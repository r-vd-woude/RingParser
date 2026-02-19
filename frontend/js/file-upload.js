// File upload and parsing functionality

const API_BASE = '/api';

/**
 * Setup file upload event listeners
 */
export function setupFileUpload(appState, elements) {
    elements.browseBtn.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', (e) => handleFileSelect(e, appState, elements));
    elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
    elements.uploadArea.addEventListener('dragover', (e) => handleDragOver(e, elements));
    elements.uploadArea.addEventListener('dragleave', (e) => handleDragLeave(e, elements));
    elements.uploadArea.addEventListener('drop', (e) => handleDrop(e, appState, elements));
    elements.parseBtn.addEventListener('click', () => parseFile(appState, elements));
    elements.changeFileBtn.addEventListener('click', () => resetUpload(appState, elements));
}

function resetUpload(appState, elements) {
    // Reset state
    appState.uploadedFile = null;
    appState.fileId = null;
    appState.fileType = null;
    appState.sourceColumns = [];
    appState.schemaFields = [];
    appState.mappings = {};
    appState.biometricsExpanded = false;

    // Reset file input so the same file can be re-selected
    elements.fileInput.value = '';

    // Show upload area, hide file info
    elements.uploadArea.style.display = '';
    elements.fileInfo.classList.add('hidden');

    // Reset schema section back to selection state
    elements.schemaInfo.classList.add('hidden');
    elements.schemaSelection.classList.remove('hidden');
    elements.useSchemaBtn.disabled = true;

    // Hide downstream sections
    elements.schemaSection.classList.add('hidden');
    elements.mappingSection.classList.add('hidden');
    elements.validationSection.classList.add('hidden');
    elements.generateSection.classList.add('hidden');
    elements.biometricsContainer.classList.add('hidden');

    // Clear content so it doesn't show stale data when next file is loaded
    elements.validationResults.innerHTML = '<p class="placeholder">Validation results will appear here after running validation.</p>';
    elements.xmlContent.textContent = '';
    elements.xmlPreview.classList.add('hidden');
}

function handleFileSelect(event, appState, elements) {
    const file = event.target.files[0];
    if (file) handleFile(file, appState, elements);
}

function handleDragOver(event, elements) {
    event.preventDefault();
    elements.uploadArea.classList.add('drag-over');
}

function handleDragLeave(event, elements) {
    event.preventDefault();
    elements.uploadArea.classList.remove('drag-over');
}

function handleDrop(event, appState, elements) {
    event.preventDefault();
    elements.uploadArea.classList.remove('drag-over');
    const file = event.dataTransfer.files[0];
    if (file) handleFile(file, appState, elements);
}

function handleFile(file, appState, elements) {
    const validTypes = appState.supportedExtensions;
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();

    if (!validTypes.includes(fileExtension)) {
        window.showError(`Invalid file type. Supported formats: ${validTypes.join(', ')}`);
        return;
    }

    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        window.showError('File is too large. Maximum size is 10MB.');
        return;
    }

    appState.uploadedFile = file;
    elements.fileName.textContent = file.name;
    elements.fileSize.textContent = formatFileSize(file.size);
    elements.fileInfo.classList.remove('hidden');
    elements.uploadArea.style.display = 'none';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

/**
 * Upload, parse, load schema, and auto-map — all in one flow.
 */
export async function parseFile(appState, elements) {
    if (!appState.uploadedFile) {
        window.showError('No file selected');
        return;
    }

    window.showLoading('Uploading and processing file...');

    try {
        // Step 1: Upload file
        const formData = new FormData();
        formData.append('file', appState.uploadedFile);

        const uploadResponse = await fetch(`${API_BASE}/file/upload`, {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const uploadData = await uploadResponse.json();
        appState.fileId = uploadData.file_id;
        appState.fileType = uploadData.file_type;

        // Step 2: Parse file
        const parseResponse = await fetch(`${API_BASE}/file/parse/${appState.fileId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_type: appState.fileType })
        });

        if (!parseResponse.ok) {
            const error = await parseResponse.json();
            throw new Error(error.detail || 'Parsing failed');
        }

        const parseData = await parseResponse.json();
        appState.sourceColumns = parseData.columns;

        // Step 2: Show schema selection
        elements.schemaSection.classList.remove('hidden');

    } catch (error) {
        window.showError('Error processing file: ' + error.message);
        console.error('Processing error:', error);
    } finally {
        window.hideLoading();
    }
}
