/**
 * Origin Certification Generator - Application JavaScript
 * Handles file uploads, form submissions, and UI interactions
 */

// ========== CONFIGURATION ==========
const CONFIG = {
    maxFileSize: 16 * 1024 * 1024, // 16MB
    allowedTypes: ['application/pdf'],
    animationDuration: 300
};

// ========== DOM ELEMENTS ==========
const elements = {
    // Will be populated on DOMContentLoaded
};

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', () => {
    initializeElements();
    initializeTabs();
    initializeFileUploads();
    initializeForms();
});

function initializeElements() {
    elements.tabs = document.querySelectorAll('.tab');
    elements.tabContents = document.querySelectorAll('.tab-content');
    elements.alertContainer = document.getElementById('alert-container');
    elements.loading = document.getElementById('loading');
}

// ========== TAB FUNCTIONALITY ==========
function initializeTabs() {
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
}

function switchTab(tabId) {
    // Update tab buttons
    elements.tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });

    // Update tab content with animation
    elements.tabContents.forEach(content => {
        if (content.id === `tab-${tabId}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
}

// ========== FILE UPLOAD FUNCTIONALITY ==========
function initializeFileUploads() {
    // Get all upload zones
    const uploadZones = document.querySelectorAll('.upload-zone');

    uploadZones.forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        const fileInfoId = zone.dataset.fileInfo;

        // Click to upload
        zone.addEventListener('click', () => input.click());

        // File selection change
        input.addEventListener('change', () => handleFileSelect(input, fileInfoId, zone));

        // Drag and drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventType => {
            zone.addEventListener(eventType, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventType => {
            zone.addEventListener(eventType, () => zone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventType => {
            zone.addEventListener(eventType, () => zone.classList.remove('dragover'), false);
        });

        zone.addEventListener('drop', (e) => {
            const file = e.dataTransfer.files[0];
            if (file && CONFIG.allowedTypes.includes(file.type)) {
                const dt = new DataTransfer();
                dt.items.add(file);
                input.files = dt.files;
                handleFileSelect(input, fileInfoId, zone);
            } else {
                showAlert('Please upload a PDF file only', 'error');
            }
        });
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleFileSelect(input, fileInfoId, zone) {
    if (input.files.length > 0) {
        const file = input.files[0];

        // Validate file size
        if (file.size > CONFIG.maxFileSize) {
            showAlert('File size exceeds 16MB limit', 'error');
            input.value = '';
            return;
        }

        // Update file info display
        const fileInfo = document.getElementById(fileInfoId);
        if (fileInfo) {
            const fileName = fileInfo.querySelector('.file-info-name');
            if (fileName) {
                fileName.textContent = file.name;
            }
            fileInfo.classList.add('show');
        }

        // Update zone appearance
        zone.classList.add('has-file');

        // Enable submit buttons
        updateSubmitButtons();
    }
}

function updateSubmitButtons() {
    // Check combined upload tab
    const invoiceFile = document.getElementById('invoiceFile');
    const billFileCombined = document.getElementById('billFileCombined');
    const extractBothBtn = document.getElementById('extractBothBtn');

    if (extractBothBtn && invoiceFile && billFileCombined) {
        extractBothBtn.disabled = !(invoiceFile.files.length > 0 || billFileCombined.files.length > 0);
    }

    // Check single bill upload tab
    const billFile = document.getElementById('billFile');
    const extractBtn = document.getElementById('extractBtn');

    if (extractBtn && billFile) {
        extractBtn.disabled = !billFile.files.length;
    }
}

// ========== FORM FUNCTIONALITY ==========
function initializeForms() {
    // Combined extraction form
    const extractBothBtn = document.getElementById('extractBothBtn');
    if (extractBothBtn) {
        extractBothBtn.addEventListener('click', () => extractFromBoth());
    }

    // Single bill extraction
    const extractBtn = document.getElementById('extractBtn');
    if (extractBtn) {
        extractBtn.addEventListener('click', () => extractAndGenerate());
    }

    // Manual form
    const manualForm = document.getElementById('manualForm');
    if (manualForm) {
        manualForm.addEventListener('submit', (e) => {
            e.preventDefault();
            generateManual();
        });
    }
}

// ========== API CALLS ==========
async function extractFromBoth() {
    const invoiceFile = document.getElementById('invoiceFile');
    const billFile = document.getElementById('billFileCombined');

    if (!invoiceFile?.files.length && !billFile?.files.length) {
        showAlert('Please upload at least one file (Invoice or Bill of Lading)', 'error');
        return;
    }

    const formData = new FormData();

    if (invoiceFile?.files.length) {
        formData.append('invoice_file', invoiceFile.files[0]);
    }
    if (billFile?.files.length) {
        formData.append('bill_file', billFile.files[0]);
    }

    await submitForm('/generate-combined', formData);
}

async function extractAndGenerate() {
    const fileInput = document.getElementById('billFile');
    if (!fileInput?.files.length) {
        showAlert('Please select a Bill of Lading PDF', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('bill_file', fileInput.files[0]);

    await submitForm('/generate', formData);
}

async function generateManual() {
    const form = document.getElementById('manualForm');
    const formData = new FormData(form);

    await submitForm('/generate-manual', formData);
}

async function submitForm(endpoint, formData) {
    showLoading(true);

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const blob = await response.blob();
            downloadFile(blob, 'certificate_of_origin.zip');
            showAlert('Certificate generated successfully! Contains both Word and PDF files.', 'success');
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to generate certificate', 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
}

// ========== UI UTILITIES ==========
function showAlert(message, type = 'info') {
    const container = elements.alertContainer;
    if (!container) return;

    const icons = {
        success: '<i class="fas fa-check-circle"></i>',
        error: '<i class="fas fa-exclamation-circle"></i>',
        info: '<i class="fas fa-info-circle"></i>'
    };

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <span class="alert-icon">${icons[type]}</span>
        <span>${message}</span>
    `;

    container.innerHTML = '';
    container.appendChild(alert);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

function showLoading(show) {
    if (elements.loading) {
        elements.loading.classList.toggle('show', show);
    }

    // Disable all buttons during loading
    document.querySelectorAll('.btn-primary').forEach(btn => {
        btn.disabled = show;
    });
}

// ========== FORM VALIDATION ==========
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.style.borderColor = '#f87171';
            isValid = false;
        } else {
            field.style.borderColor = '';
        }
    });

    return isValid;
}

// Add real-time validation
document.addEventListener('input', (e) => {
    if (e.target.matches('.form-input, .form-textarea')) {
        if (e.target.hasAttribute('required') && e.target.value.trim()) {
            e.target.style.borderColor = '';
        }
    }
});
