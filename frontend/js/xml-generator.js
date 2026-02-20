// XML generation and download functionality
const API_BASE = '/api';

// Fields that are hardcoded in the XML generator — exposed in the Advanced panel
const ADVANCED_FIELDS = [
    { name: 'Modus', default: 'Insert' },
    { name: 'EURINGCodeIdentifier', default: '4' },
];

/**
 * Setup XML generator event listeners
 */
export function setupXmlGenerator(appState, elements) {
    elements.generateBtn.addEventListener('click', () => generateXml(appState, elements));
    elements.downloadBtn.addEventListener('click', () => downloadXml(appState));
    elements.advancedToggleBtn.addEventListener('click', () => {
        const isNowHidden = elements.advancedPanel.classList.toggle('hidden');
        elements.advancedToggleBtn.classList.toggle('active', !isNowHidden);
        if (!isNowHidden) {
            buildAdvancedPanel(appState, elements);
        }
    });
}

/**
 * Flatten schema fields to leaf nodes only (mirrors column-mapper.js logic).
 */
function getLeafFields(fields, result = []) {
    fields.forEach(field => {
        const isComplex = (field.children && field.children.length > 0) || field.is_choice;
        if (!isComplex) {
            result.push({ name: field.name, path: field.path });
        }
        if (field.children && field.children.length > 0) {
            getLeafFields(field.children, result);
        }
        if (field.is_choice && field.choice_options) {
            field.choice_options.forEach(option => {
                if (option.fields) getLeafFields(option.fields, result);
            });
        }
    });
    return result;
}

/**
 * Build (or rebuild) the contents of the Advanced panel.
 */
function buildAdvancedPanel(appState, elements) {
    const panel = elements.advancedPanel;
    panel.innerHTML = '';

    const sourceColumns = (appState.sourceColumns || []).map(c => c.name);
    const leafFields = getLeafFields(appState.schemaFields || []);
    const advancedFieldNames = new Set(ADVANCED_FIELDS.map(f => f.name));

    ADVANCED_FIELDS.forEach(({ name, default: defaultVal }) => {
        // Restore any previously set override, or fall back to static default
        const current = appState.advancedOverrides[name] || { type: 'static', value: defaultVal };

        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'advanced-field';

        const nameEl = document.createElement('div');
        nameEl.className = 'advanced-field-name';
        nameEl.textContent = name;
        fieldDiv.appendChild(nameEl);

        const controls = document.createElement('div');
        controls.className = 'advanced-field-controls';

        // --- Static value option ---
        const staticLabel = document.createElement('label');
        staticLabel.className = 'advanced-option-label';

        const staticRadio = document.createElement('input');
        staticRadio.type = 'radio';
        staticRadio.name = `adv-${name}`;
        staticRadio.value = 'static';
        staticRadio.checked = current.type === 'static';

        const staticInput = document.createElement('input');
        staticInput.type = 'text';
        staticInput.className = 'advanced-static-input';
        staticInput.value = current.type === 'static' ? current.value : defaultVal;
        staticInput.disabled = current.type !== 'static';

        staticLabel.append(staticRadio, ' Static value: ', staticInput);
        controls.appendChild(staticLabel);

        // --- From column option ---
        const columnLabel = document.createElement('label');
        columnLabel.className = 'advanced-option-label';

        const columnRadio = document.createElement('input');
        columnRadio.type = 'radio';
        columnRadio.name = `adv-${name}`;
        columnRadio.value = 'column';
        columnRadio.checked = current.type === 'column';

        const columnSelect = document.createElement('select');
        columnSelect.className = 'mapping-select advanced-column-select';
        columnSelect.disabled = current.type !== 'column';

        const emptyOpt = document.createElement('option');
        emptyOpt.value = '';
        emptyOpt.textContent = '-- Select column --';
        columnSelect.appendChild(emptyOpt);
        sourceColumns.forEach(col => {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            if (current.type === 'column' && current.value === col) opt.selected = true;
            columnSelect.appendChild(opt);
        });

        columnLabel.append(columnRadio, ' From column: ', columnSelect);
        controls.appendChild(columnLabel);

        // --- Wire up interactivity ---
        const save = () => {
            const isStatic = staticRadio.checked;
            staticInput.disabled = !isStatic;
            columnSelect.disabled = isStatic;
            appState.advancedOverrides[name] = {
                type: isStatic ? 'static' : 'column',
                value: isStatic ? staticInput.value : columnSelect.value,
            };
        };

        staticRadio.addEventListener('change', save);
        columnRadio.addEventListener('change', save);
        staticInput.addEventListener('input', save);
        columnSelect.addEventListener('change', save);

        // Persist current state immediately so the first generate reflects it
        appState.advancedOverrides[name] = current;

        fieldDiv.appendChild(controls);
        panel.appendChild(fieldDiv);
    });

    // --- Column overrides section ---
    const separator = document.createElement('hr');
    separator.className = 'advanced-separator';
    panel.appendChild(separator);

    const overrideList = document.createElement('div');
    overrideList.className = 'advanced-override-list';

    // Restore any previously added column overrides
    Object.entries(appState.advancedOverrides).forEach(([key, override]) => {
        if (!advancedFieldNames.has(key)) {
            addColumnOverrideRow(overrideList, appState, leafFields, key, override.value);
        }
    });

    panel.appendChild(overrideList);

    const addBtn = document.createElement('button');
    addBtn.className = 'btn btn-secondary';
    addBtn.type = 'button';
    addBtn.textContent = '+ Add override';
    addBtn.addEventListener('click', () => {
        addColumnOverrideRow(overrideList, appState, leafFields, '', '');
    });
    panel.appendChild(addBtn);
}

/**
 * Add a single column-override row to the override list.
 * leafFields: array of { name, path } from the XSD schema.
 * initialColumn: the target_path key stored in appState.advancedOverrides.
 */
function addColumnOverrideRow(container, appState, leafFields, initialColumn, initialValue) {
    const row = document.createElement('div');
    row.className = 'advanced-override-row';

    const colSelect = document.createElement('select');
    colSelect.className = 'mapping-select advanced-column-select';

    const emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.textContent = '-- Select XSD field --';
    colSelect.appendChild(emptyOpt);
    leafFields.forEach(field => {
        const opt = document.createElement('option');
        opt.value = field.path;
        opt.textContent = field.name;
        if (field.path === initialColumn) opt.selected = true;
        colSelect.appendChild(opt);
    });

    const valueInput = document.createElement('input');
    valueInput.type = 'text';
    valueInput.className = 'advanced-static-input';
    valueInput.placeholder = 'Static value';
    valueInput.value = initialValue;

    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-secondary advanced-remove-btn';
    removeBtn.type = 'button';
    removeBtn.textContent = '✕';

    let currentColumn = initialColumn;

    const save = () => {
        const col = colSelect.value;
        const val = valueInput.value;
        if (currentColumn && currentColumn !== col) {
            delete appState.advancedOverrides[currentColumn];
        }
        currentColumn = col;
        if (col) {
            appState.advancedOverrides[col] = { type: 'static', value: val };
        }
    };

    colSelect.addEventListener('change', save);
    valueInput.addEventListener('input', save);
    removeBtn.addEventListener('click', () => {
        if (currentColumn) {
            delete appState.advancedOverrides[currentColumn];
        }
        container.removeChild(row);
    });

    row.appendChild(colSelect);
    row.appendChild(valueInput);
    row.appendChild(removeBtn);
    container.appendChild(row);

    if (initialColumn) {
        appState.advancedOverrides[initialColumn] = { type: 'static', value: initialValue };
    }
}

/**
 * Serialise appState.advancedOverrides into the API payload format.
 */
function buildOverridesPayload(advancedOverrides) {
    return Object.entries(advancedOverrides).map(([field_name, override]) => ({
        field_name,
        static_value: override.type === 'static' ? override.value : null,
        source_column: override.type === 'column' ? override.value : null,
    }));
}

/**
 * Generate XML from mapped data
 */
export async function generateXml(appState, elements) {
    if (!appState.fileId || !appState.mappingId) {
        window.showError('Please upload a file and create a mapping first');
        return;
    }

    window.showLoading('Generating XML output...');

    try {
        const response = await fetch(`${API_BASE}/xml/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: appState.fileId,
                file_type: appState.fileType,
                mapping_id: appState.mappingId,
                advanced_overrides: buildOverridesPayload(appState.advancedOverrides)
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'XML generation failed');
        }

        const result = await response.json();
        console.log('XML generated:', result);

        // Store XML ID for download
        appState.generatedXmlId = result.xml_id;

        // Display XML preview
        elements.xmlPreview.classList.remove('hidden');
        elements.xmlContent.textContent = result.preview;
        elements.downloadBtn.disabled = false;

        // Show statistics
        const statsMessage = `
            XML generated successfully!
            - File: ${result.filename}
            - Total rows: ${result.total_rows}
            - File size: ${formatFileSize(result.file_size)}
        `.trim();

        window.showSuccess(statsMessage);
        alert(result.message + '\n\n' + statsMessage);

    } catch (error) {
        window.showError('XML generation error: ' + error.message);
        console.error('XML generation error:', error);
    } finally {
        window.hideLoading();
    }
}

/**
 * Download generated XML file
 */
export async function downloadXml(appState) {
    if (!appState.generatedXmlId) {
        window.showError('No XML file generated yet');
        return;
    }

    try {
        // Trigger download via browser
        const downloadUrl = `${API_BASE}/xml/download/${appState.generatedXmlId}`;

        // Create a temporary link and click it to trigger download
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `bird_ringing_data_${appState.generatedXmlId}.xml`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        window.showSuccess('XML file download started');
    } catch (error) {
        window.showError('Download error: ' + error.message);
        console.error('Download error:', error);
    }
}

/**
 * Format file size to human-readable format
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}
