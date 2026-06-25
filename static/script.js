// Global variable to hold the extracted JSON formats
let currentExtractedData = null;

// File input handler
document.getElementById('fileInput').addEventListener('change', handleFileSelect);

// Tab selection handler
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        if (!currentExtractedData) return;
        
        // Remove active class from all tabs
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        
        // Add active class to clicked tab
        btn.classList.add('active');
        
        // Update JSON content
        const target = btn.getAttribute('data-target');
        let selectedJson = null;
        if (target === 'raw') {
            selectedJson = currentExtractedData.raw;
        } else if (target === 'flat') {
            selectedJson = currentExtractedData.flat;
        } else if (target === 'grouped') {
            selectedJson = currentExtractedData.grouped;
        }
        
        const resultJson = document.getElementById('resultJson');
        if (resultJson && selectedJson) {
            resultJson.textContent = JSON.stringify(selectedJson, null, 2);
        }
    });
});

const copyJsonBtn = document.getElementById('copyJsonBtn');
if (copyJsonBtn) {
    copyJsonBtn.addEventListener('click', async () => {
        const resultJson = document.getElementById('resultJson');
        const text = resultJson ? resultJson.textContent : '';
        if (!text) {
            return;
        }

        try {
            await navigator.clipboard.writeText(text);
            copyJsonBtn.textContent = 'Copied';
            setTimeout(() => {
                copyJsonBtn.textContent = 'Copy JSON';
            }, 1200);
        } catch (error) {
            showError('Could not copy JSON: ' + error.message);
        }
    });
}

// Drag and drop handlers
const uploadBox = document.getElementById('uploadBox');
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.style.borderColor = 'var(--primary)';
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.style.borderColor = 'var(--border)';
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.style.borderColor = 'var(--border)';
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    // Validate file type
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
        showError('Invalid file type. Please upload PDF or image file.');
        return;
    }

    // Validate file size (16MB max)
    if (file.size > 16 * 1024 * 1024) {
        showError('File size exceeds 16MB limit.');
        return;
    }

    uploadFile(file);
}

async function uploadFile(file) {
    // Hide upload box, show progress
    document.getElementById('uploadBox').style.display = 'none';
    document.getElementById('uploadProgress').style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);

    try {
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 5;
            if (progress <= 90) {
                document.getElementById('progressFill').style.width = progress + '%';
            }
        }, 200);

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);
        document.getElementById('progressFill').style.width = '100%';

        const data = await response.json();

        if (response.ok && data.success) {
            showSuccess(data.filename, data, data.token_usage);
        } else {
            showError(data.error || 'Upload failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

function showSuccess(filename, data, tokenUsage) {
    document.getElementById('uploadProgress').style.display = 'none';
    document.getElementById('uploadResult').style.display = 'block';
    document.getElementById('resultFilename').textContent = filename;
    
    currentExtractedData = {
        raw: data.extracted_data,
        flat: data.erp_flat_arrays,
        grouped: data.erp_grouped
    };
    
    // Reset active tab class to raw on show
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const rawTab = document.querySelector('.tab-btn[data-target="raw"]');
    if (rawTab) {
        rawTab.classList.add('active');
    }
    
    document.getElementById('resultJson').textContent = JSON.stringify(data.extracted_data, null, 2);

    const tokenUsageBadge = document.getElementById('tokenUsageBadge');
    if (tokenUsageBadge) {
        if (tokenUsage) {
            const rows = [
                ['Requests', tokenUsage.request_count],
                ['Input', tokenUsage.input_tokens],
                ['Output', tokenUsage.output_tokens],
                ['Total', tokenUsage.total_tokens],
                ['Cached', tokenUsage.cached_tokens],
                ['Tool', tokenUsage.tool_use_tokens],
            ].filter(([, value]) => value !== null && value !== undefined);

            if (rows.length > 0) {
                tokenUsageBadge.innerHTML = `
                    <div class="token-usage-title">Gemini Usage</div>
                    <div class="token-usage-grid">
                        ${rows.map(([label, value]) => `<div class="token-usage-item"><span>${label}</span><strong>${value}</strong></div>`).join('')}
                    </div>
                `;
            } else {
                tokenUsageBadge.textContent = '';
                tokenUsageBadge.style.display = 'none';
                return;
            }

            tokenUsageBadge.style.display = 'inline-flex';
        } else {
            tokenUsageBadge.style.display = 'none';
            tokenUsageBadge.textContent = '';
        }
    }
}

function showError(message) {
    document.getElementById('uploadBox').style.display = 'none';
    document.getElementById('uploadProgress').style.display = 'none';
    document.getElementById('errorMessage').style.display = 'block';
    document.getElementById('errorText').textContent = message;
}

function resetUpload() {
    currentExtractedData = null;
    document.getElementById('uploadBox').style.display = 'block';
    document.getElementById('uploadProgress').style.display = 'none';
    document.getElementById('uploadResult').style.display = 'none';
    document.getElementById('errorMessage').style.display = 'none';
    document.getElementById('fileInput').value = '';
    document.getElementById('progressFill').style.width = '0%';
    const tokenUsageBadge = document.getElementById('tokenUsageBadge');
    if (tokenUsageBadge) {
        tokenUsageBadge.style.display = 'none';
        tokenUsageBadge.textContent = '';
        tokenUsageBadge.innerHTML = '';
    }
    const resultJson = document.getElementById('resultJson');
    if (resultJson) {
        resultJson.textContent = '';
    }
    // Reset tab active state to raw
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const rawTab = document.querySelector('.tab-btn[data-target="raw"]');
    if (rawTab) {
        rawTab.classList.add('active');
    }
}
