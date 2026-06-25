import json
import os
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key-change-this")
app.config["UPLOAD_FOLDER"] = "/tmp" if os.getenv("VERCEL") else os.getenv("UPLOAD_FOLDER", "uploads")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_FILE_SIZE_MB", "16")) * 1024 * 1024

if not os.getenv("VERCEL"):
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_model = None
genai_client = None
legacy_genai = None

# Try to initialize the new google-genai SDK first
try:
    from google import genai
    if hasattr(genai, "Client"):
        if GEMINI_API_KEY:
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
            
            class GeminiGenAIWrapper:
                def __init__(self, client, model_name):
                    self.client = client
                    self.model_name = model_name

                def generate_content(self, inputs):
                    return self.client.models.generate_content(
                        model=self.model_name,
                        contents=inputs
                    )
            
            gemini_model = GeminiGenAIWrapper(genai_client, "gemini-2.5-flash")
except Exception:
    pass

# Fallback to the legacy google-generativeai SDK if the new SDK is not available
if gemini_model is None:
    try:
        import google.generativeai as legacy_genai_mod
        if GEMINI_API_KEY:
            legacy_genai_mod.configure(api_key=GEMINI_API_KEY)
            model_obj = legacy_genai_mod.GenerativeModel("models/gemini-2.5-flash")
            
            class GeminiLegacyWrapper:
                def __init__(self, model):
                    self.model = model

                def generate_content(self, inputs):
                    return self.model.generate_content(inputs)
            
            gemini_model = GeminiLegacyWrapper(model_obj)
            legacy_genai = legacy_genai_mod
    except Exception:
        pass

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "bmp", "tiff"}
MIME_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
}


def extract_json_from_text(response_text: str):
    response_text = response_text.strip()
    response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
    response_text = re.sub(r"\s*```$", "", response_text)

    start_index = min(
        [index for index in [response_text.find("{"), response_text.find("[")] if index != -1],
        default=-1,
    )
    end_index = max(response_text.rfind("}"), response_text.rfind("]"))
    if start_index != -1 and end_index != -1 and end_index > start_index:
        response_text = response_text[start_index : end_index + 1]

    return json.loads(response_text)


def extract_token_usage(response):
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None

    prompt_tokens = getattr(usage, "prompt_token_count", None)
    completion_tokens = getattr(usage, "candidates_token_count", None)
    total_tokens = getattr(usage, "total_token_count", None)
    cached_tokens = getattr(usage, "cached_content_token_count", None)
    response_tokens = getattr(usage, "tool_use_prompt_token_count", None)

    if prompt_tokens is None and hasattr(usage, "promptTokens"):
        prompt_tokens = getattr(usage, "promptTokens")
    if completion_tokens is None and hasattr(usage, "candidatesTokens"):
        completion_tokens = getattr(usage, "candidatesTokens")
    if total_tokens is None and hasattr(usage, "totalTokens"):
        total_tokens = getattr(usage, "totalTokens")
    if cached_tokens is None and hasattr(usage, "cachedContentTokens"):
        cached_tokens = getattr(usage, "cachedContentTokens")
    if response_tokens is None and hasattr(usage, "toolUsePromptTokens"):
        response_tokens = getattr(usage, "toolUsePromptTokens")

    if (
        prompt_tokens is None
        and completion_tokens is None
        and total_tokens is None
        and cached_tokens is None
        and response_tokens is None
    ):
        return None

    return {
        "request_count": 1,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
        "tool_use_tokens": response_tokens,
    }


def extract_data_with_gemini(filepath: str):
    if gemini_model is None:
        raise RuntimeError("Gemini API key not configured")

    extension = filepath.rsplit(".", 1)[-1].lower()
    mime_type = MIME_TYPES.get(extension, "application/octet-stream")

    prompt = """
You are an expert Purchase Order to ERP Sales Order transformation engine.

IMPORTANT BUSINESS CONTEXT:

The uploaded document is always a Purchase Order (PO) received by our company.

Our company acts as the supplier/vendor.

Therefore:

* The customer issuing the PO becomes the ERP Customer.
* The Purchase Order Number becomes Party PO No.
* The Purchase Order Date becomes PO Date.
* Delivery schedules, item specifications, taxes, terms and conditions must be converted into ERP Sales Order structure.
* Do NOT rely on matching labels.
* Understand the business meaning of fields and map semantically.

---

## PHASE 1 : DOCUMENT EXTRACTION

Analyze the entire document and extract ALL available information.

Apply the following rules:

1. Discover document structure dynamically.
2. Extract all metadata, identifiers, dates, references.
3. Extract all company information.
4. Extract all addresses.
5. Extract all tax information.
6. Extract all financial information.
7. Extract all item rows.
8. Extract all size breakups.
9. Extract all schedules.
10. Extract all terms and conditions.
11. Extract all remarks.
12. Extract all footer information.
13. Extract all signatures, declarations and notes.

Normalize all keys using snake_case.

Keep data types accurate.

Convert all discovered tables into arrays.

Preserve parent-child relationships.

If a value is unreadable or empty use null.

---

## PHASE 2 : ERP MAPPING

Transform the extracted information into the following ERP structure.

Return BOTH:

1. erp_data
2. additional_extracted_information

Do NOT lose any information.

---

## ERP STRUCTURE

{
"erp_data": {
"transaction_header": {},
"item_details": [],
"document_wise_commercials": [],
"document_terms": [],
"item_wise_commercials": [],
"item_wise_terms": [],
"delivery_schedule": [],
"missing_erp_fields": []
},

"additional_extracted_information": {}
}

---

## ERP MAPPING RULES

A. TRANSACTION HEADER

Map semantically.

Examples:

Purchase Order Number
PO Number
PO Ref
Buyer PO
Customer PO

→ party_po_no

Order Date
PO Date
Document Date

→ po_date

Customer Name
Buyer Name
Purchaser
Brand Owner

→ customer

Supplier Name

→ supplier_name

Ship To

→ shipping_address

Bill To

→ billing_address

GSTIN
GST Number

→ gst_no

---

## B. ITEM DETAILS

Every item must become a row.

If item contains size breakdown:

Example:

XS = 100
S = 50
M = 75

Create separate ERP rows:

{
"size_breakup":"XS",
"order_quantity":100
}

{
"size_breakup":"S",
"order_quantity":50
}

{
"size_breakup":"M",
"order_quantity":75
}

Never store multiple sizes in one field.

---

## C. DOCUMENT WISE COMMERCIALS

Extract:

CGST
SGST
IGST
CESS
DISCOUNT
SURCHARGE

as separate rows.

---

## D. DOCUMENT TERMS

Preserve FULL TEXT.

Never summarize.

Example:

"If the supplies are delayed from the delivery schedule, it shall attract a 1% reduction on PO value for each days delay."

Store exactly as written.

{
        "term_name": "payment_terms",
        "term_remark": "60 DAYS CREDIT"
      },

---

## E. ITEM WISE COMMERCIALS

Store taxes and commercial calculations item-wise.

---

## F. ITEM WISE TERMS

Store specifications item-wise.

Examples:

Material
Width
Length
Fold
Color
Fabric
Construction
Artwork
Printing
Packing

Each becomes a separate term row.

---

## G. DELIVERY SCHEDULE

Store all schedule rows.

Preserve:

Required From Date
Required To Date
Dispatch Date
Quantity
Document References

---

## MISSING ERP FIELDS

For every ERP field not found in document:

Add field name into:

missing_erp_fields

Example:

[
"division",
"location",
"series",
"sales_person"
]

---

## ADDITIONAL EXTRACTED INFORMATION

VERY IMPORTANT:

Any information extracted from the document that does NOT fit ERP structure must NEVER be discarded.

Store it inside:

additional_extracted_information

Examples:

brand
global_customer
season
buyer_contact
supplier_cin
phone
email
amount_in_words
legal_notes
special_instructions
country_of_origin
care_instructions
barcode
style_number
sku
remarks
footer_notes
signatory_information

Store complete original values.

---

## OUTPUT RULES

Return ONLY ONE VALID JSON.

No markdown.

No explanations.

No code blocks.

No comments.

No text outside JSON.

Preserve full original content.

Never summarize.

Never truncate.

Never lose information.

""".strip()

    if genai_client is not None:
        from google.genai import types
        try:
            uploaded_document = genai_client.files.upload(
                file=filepath,
                config=types.UploadFileConfig(mime_type=mime_type)
            )
        except Exception:
            uploaded_document = genai_client.files.upload(file=filepath)
    elif legacy_genai is not None:
        uploaded_document = legacy_genai.upload_file(filepath, mime_type=mime_type)
    else:
        raise RuntimeError("Gemini SDK not configured")

    response = gemini_model.generate_content([prompt, uploaded_document])
    return extract_json_from_text(response.text), extract_token_usage(response)


def convert_to_erp_flat_arrays(json_data):
    if not isinstance(json_data, dict):
        return {}
    erp_data = json_data.get("erp_data", {})
    if not isinstance(erp_data, dict):
        erp_data = {}
        
    header = erp_data.get("transaction_header", {})
    header_list = [header] if isinstance(header, dict) else (header or [])
    
    return {
        "header": header_list,
        "items": erp_data.get("item_details") or [],
        "item_terms": erp_data.get("item_wise_terms") or [],
        "commercials": erp_data.get("document_wise_commercials") or [],
        "document_terms": erp_data.get("document_terms") or []
    }


def convert_to_erp_grouped(json_data):
    if not isinstance(json_data, dict):
        return {}
    erp_data = json_data.get("erp_data", {})
    if not isinstance(erp_data, dict):
        erp_data = {}
        
    item_details = erp_data.get("item_details") or []
    item_wise_terms = erp_data.get("item_wise_terms") or []
    
    if not isinstance(item_details, list):
        item_details = []
    if not isinstance(item_wise_terms, list):
        item_wise_terms = []
        
    grouped_items = []
    for item in item_details:
        if not isinstance(item, dict):
            grouped_items.append(item)
            continue
        item_copy = dict(item)
        item_copy["terms"] = []
        
        parent_ref = item_copy.get("parent_po_no_ref")
        for term in item_wise_terms:
            if isinstance(term, dict) and term.get("parent_po_no_ref") == parent_ref:
                item_copy["terms"].append(term)
                
        grouped_items.append(item_copy)
        
    return {
        "header": erp_data.get("transaction_header") or {},
        "items": grouped_items,
        "commercials": erp_data.get("document_wise_commercials") or [],
        "document_terms": erp_data.get("document_terms") or []
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file_route():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not configured"}), 500

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if "." not in file.filename:
        return jsonify({"error": "Invalid file type"}), 400

    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    try:
        file.save(filepath)
        extracted_data, token_usage = extract_data_with_gemini(filepath)
        erp_flat = convert_to_erp_flat_arrays(extracted_data)
        erp_grouped = convert_to_erp_grouped(extracted_data)
        return jsonify({
            "success": True,
            "filename": filename,
            "extracted_data": extracted_data,
            "erp_flat_arrays": erp_flat,
            "erp_grouped": erp_grouped,
            "token_usage": token_usage,
        })
    except json.JSONDecodeError as error:
        return jsonify({"error": f"Failed to parse JSON: {error}"}), 500
    except Exception as error:
        return jsonify({"error": str(error)}), 500
    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "gemini_configured": GEMINI_API_KEY is not None,
        "json_only": True,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
