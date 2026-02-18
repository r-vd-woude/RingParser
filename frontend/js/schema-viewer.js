// Schema viewing and validation functionality
import { autoMapFields } from './column-mapper.js';

const API_BASE = '/api';

/**
 * Setup schema viewer event listeners
 */
export function setupSchemaViewer(appState, elements) {
    elements.validateBtn.addEventListener('click', () => validateMapping(appState, elements));
}

/**
 * Load XSD schema, then auto-map. Called automatically after file parse.
 * Throws on failure so the caller (parseFile) can handle errors centrally.
 */
export async function loadSchema(appState, elements) {
    const response = await fetch(`${API_BASE}/schema/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
        throw new Error(`Failed to load schema: ${response.statusText}`);
    }

    const schema = await response.json();
    appState.schemaFields = schema.fields;

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
