// Schema viewing and validation functionality
import { autoMapFields } from './column-mapper.js';

const API_BASE = '/api';

/**
 * Setup schema selector event listeners (Step 2).
 */
export function setupSchemaSelector(appState, elements) {
    // Load schema list when the section becomes visible via MutationObserver
    const observer = new MutationObserver(() => {
        if (!elements.schemaSection.classList.contains('hidden')) {
            loadSchemaList(appState, elements);
        }
    });
    observer.observe(elements.schemaSection, { attributeFilter: ['class'] });

    // Upload custom schema
    elements.schemaFileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        elements.schemaUploadStatus.textContent = 'Uploading...';
        try {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch(`${API_BASE}/schema/upload`, { method: 'POST', body: formData });
            if (!response.ok) throw new Error((await response.json()).detail);
            const data = await response.json();
            elements.schemaUploadStatus.textContent = `Uploaded: ${data.name}`;
            await loadSchemaList(appState, elements);
            selectSchema(data.id, appState, elements);
        } catch (err) {
            elements.schemaUploadStatus.textContent = `Upload failed: ${err.message}`;
        }
    });

    // Use selected schema button
    elements.useSchemaBtn.addEventListener('click', async () => {
        if (!appState.selectedSchemaId) return;
        window.showLoading('Loading schema...');
        try {
            await loadSchema(appState, elements);
        } catch (err) {
            window.showError('Failed to load schema: ' + err.message);
        } finally {
            window.hideLoading();
        }
    });
}

async function loadSchemaList(appState, elements) {
    try {
        const response = await fetch(`${API_BASE}/schema/list`);
        const data = await response.json();
        elements.schemaList.innerHTML = '';
        data.schemas.forEach(schema => {
            const card = document.createElement('div');
            card.className = 'schema-card';
            card.dataset.schemaId = schema.id;
            card.innerHTML = `
                <span class="schema-card__name">${schema.name}</span>
                <span class="schema-card__size">${(schema.size / 1024).toFixed(1)} KB</span>
            `;
            card.addEventListener('click', () => selectSchema(schema.id, appState, elements));
            elements.schemaList.appendChild(card);
        });
        // Auto-select if only one schema available
        if (data.schemas.length === 1) {
            selectSchema(data.schemas[0].id, appState, elements);
        }
    } catch (err) {
        elements.schemaList.innerHTML = '<p class="placeholder">Could not load schemas.</p>';
    }
}

function selectSchema(schemaId, appState, elements) {
    appState.selectedSchemaId = schemaId;
    elements.schemaList.querySelectorAll('.schema-card').forEach(card => {
        card.classList.toggle('schema-card--selected', card.dataset.schemaId === schemaId);
    });
    elements.useSchemaBtn.disabled = false;
}

/**
 * Setup schema viewer event listeners
 */
export function setupSchemaViewer(appState, elements) {
    elements.validateBtn.addEventListener('click', () => validateMapping(appState, elements));
}

/**
 * Load XSD schema, then auto-map. Called after schema is selected in Step 2.
 * Throws on failure so the caller can handle errors centrally.
 */
export async function loadSchema(appState, elements) {
    const response = await fetch(`${API_BASE}/schema/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schema_id: appState.selectedSchemaId })
    });

    if (!response.ok) {
        throw new Error(`Failed to load schema: ${response.statusText}`);
    }

    const schema = await response.json();
    appState.schemaFields = schema.fields;

    elements.schemaSection.classList.add('hidden');
    await autoMapFields(appState, elements);
}

/**
 * Validate mapping
 */
export async function validateMapping(appState, elements) {
    if (!appState.fileId || !appState.mappingId) {
        window.showError('Please upload a file and create a mapping first');
        return;
    }

    window.showLoading('Validating data...');

    try {
        const response = await fetch(`${API_BASE}/mapping/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_id: appState.fileId,
                file_type: appState.fileType,
                mapping_id: appState.mappingId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Validation failed');
        }

        const result = await response.json();
        displayValidationResults(result, elements);

        if (result.is_valid && result.required_fields_missing.length === 0) {
            elements.generateBtn.disabled = false;
        } else if (result.total_errors === 0) {
            elements.generateBtn.disabled = false;
        } else {
            elements.generateBtn.disabled = true;
            window.showError(`Validation found ${result.total_errors} errors. Please fix them before generating XML.`);
        }

    } catch (error) {
        window.showError('Validation error: ' + error.message);
        console.error('Validation error:', error);
    } finally {
        window.hideLoading();
    }
}

function displayValidationResults(result, elements) {
    elements.validationResults.innerHTML = '';

    const statusDiv = document.createElement('div');
    statusDiv.className = result.is_valid && result.total_errors === 0 ? 'validation-success' : 'validation-error';

    if (result.is_valid && result.total_errors === 0) {
        statusDiv.innerHTML = `
            <strong>✓ Validation Passed</strong><br>
            ${result.validated_fields} fields validated successfully
        `;
    } else {
        statusDiv.innerHTML = `
            <strong>✗ Validation Issues Found</strong><br>
            ${result.total_errors} errors, ${result.total_warnings} warnings in ${result.validated_fields} fields
        `;
    }

    elements.validationResults.appendChild(statusDiv);

    if (result.messages && result.messages.length > 0) {
        const messagesContainer = document.createElement('div');
        messagesContainer.style.marginTop = '16px';

        result.messages.forEach(msg => {
            const msgDiv = document.createElement('div');
            msgDiv.className = msg.severity === 'error' ? 'validation-error' : 'validation-warning';
            msgDiv.style.marginBottom = '8px';
            msgDiv.innerHTML = `
                <strong>${msg.field_name}</strong>: ${msg.message}<br>
                <small>${msg.actual_value ? 'Value: ' + msg.actual_value : ''} ${msg.expected_value ? '(Expected: ' + msg.expected_value + ')' : ''}</small>
            `;
            messagesContainer.appendChild(msgDiv);
        });

        elements.validationResults.appendChild(messagesContainer);
    }

    if (result.required_fields_missing && result.required_fields_missing.length > 0) {
        const missingDiv = document.createElement('div');
        missingDiv.className = 'validation-warning';
        missingDiv.style.marginTop = '16px';
        missingDiv.innerHTML = `
            <strong>Required Fields Not Mapped (${result.required_fields_missing.length})</strong><br>
            <small>These fields are required by the XSD schema but not currently mapped:</small>
            <ul style="margin-top: 8px; padding-left: 20px;">
                ${result.required_fields_missing.slice(0, 10).map(f => `<li>${f}</li>`).join('')}
                ${result.required_fields_missing.length > 10 ? `<li><em>...and ${result.required_fields_missing.length - 10} more</em></li>` : ''}
            </ul>
        `;
        elements.validationResults.appendChild(missingDiv);
    }
}
