// Column mapping functionality
const API_BASE = '/api';

/**
 * Setup column mapper event listeners
 */
export function setupColumnMapper() {
    // Auto-map is triggered programmatically after schema loads
}

/**
 * Auto-map fields using backend suggestions.
 * Called by loadSchema() — loading state is managed by the caller.
 * Throws on failure so the caller can handle errors centrally.
 */
export async function autoMapFields(appState, elements) {
    const sourceColumnNames = appState.sourceColumns.map(col => col.name);

    const response = await fetch(`${API_BASE}/mapping/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_columns: sourceColumnNames, threshold: 0.5 })
    });

    if (!response.ok) {
        throw new Error('Failed to get mapping suggestions');
    }

    const data = await response.json();
    console.log('Mapping suggestions:', data);

    // Store mappings keyed by target_path
    appState.mappings = {};
    data.suggestions.forEach(suggestion => {
        appState.mappings[suggestion.target_path] = {
            source_column: suggestion.source_column,
            target_name: suggestion.target_name,
            confidence: suggestion.confidence
        };
    });

    updateMappingDisplay(appState, elements);
    await saveMappingConfiguration(appState);

    // Show downstream sections
    elements.mappingSection.classList.remove('hidden');
    elements.validationSection.classList.remove('hidden');
    elements.generateSection.classList.remove('hidden');
}

const HARDCODED_FIELDS = new Set(['Modus', 'EURINGCodeIdentifier']);

/**
 * Update mapping display — XSD fields as primary, source column dropdowns underneath.
 * Biometrics fields are in a collapsible section.
 */
export function updateMappingDisplay(appState, elements) {
    elements.targetFields.innerHTML = '';

    const leafFields = getLeafFields(appState.schemaFields || []);
    const sourceColumnNames = appState.sourceColumns
        ? appState.sourceColumns.map(col => col.name)
        : [];

    const regularFields = leafFields.filter(f =>
        !HARDCODED_FIELDS.has(f.name) && !f.path.includes('Biometrics')
    );
    const bioFields = leafFields.filter(f => f.path.includes('Biometrics'));

    // Build column name → sample_values lookup
    const sourceColumnMap = {};
    (appState.sourceColumns || []).forEach(col => {
        sourceColumnMap[col.name] = col.sample_values || [];
    });

    // Regular fields
    regularFields.forEach(field => {
        elements.targetFields.appendChild(
            createFieldRow(field, sourceColumnNames, sourceColumnMap, appState, elements)
        );
    });

    // Biometrics — separate scrollable section below the main list
    if (bioFields.length > 0) {
        // Recreate toggle button in the controls bar
        const existing = elements.mappingControls.querySelector('.biometrics-toggle');
        if (existing) existing.remove();

        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'btn biometrics-toggle' + (appState.biometricsExpanded ? ' active' : '');
        toggleBtn.textContent = 'Add biometric data';
        elements.targetFields.parentNode.insertBefore(toggleBtn, elements.targetFields.nextSibling);

        // Populate the dedicated biometrics field list
        elements.biometricsFields.innerHTML = '';
        bioFields.forEach(field => {
            elements.biometricsFields.appendChild(
                createFieldRow(field, sourceColumnNames, sourceColumnMap, appState, elements)
            );
        });

        elements.biometricsContainer.classList.toggle('hidden', !appState.biometricsExpanded);

        toggleBtn.addEventListener('click', () => {
            appState.biometricsExpanded = !appState.biometricsExpanded;
            elements.biometricsContainer.classList.toggle('hidden', !appState.biometricsExpanded);
            toggleBtn.classList.toggle('active', appState.biometricsExpanded);
            updateMappingStatus(appState, elements);
        });
    }

    updateMappingStatus(appState, elements);
}

function createFieldRow(field, sourceColumnNames, sourceColumnMap, appState, elements) {
    const item = document.createElement('div');
    item.className = 'column-item' + (field.required ? ' required' : '');

    // Field name
    const nameEl = document.createElement('div');
    nameEl.className = 'column-name';
    nameEl.textContent = field.name;
    if (field.required) {
        const star = document.createElement('span');
        star.className = 'required-star';
        star.textContent = '*';
        nameEl.appendChild(star);
    }
    item.appendChild(nameEl);

    // Select + sample button row
    const selectRow = document.createElement('div');
    selectRow.className = 'select-row';

    const select = document.createElement('select');
    select.className = 'mapping-select';
    select.dataset.targetPath = field.path;

    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = '-- Not mapped --';
    select.appendChild(defaultOption);

    sourceColumnNames.forEach(colName => {
        const option = document.createElement('option');
        option.value = colName;
        option.textContent = colName;
        select.appendChild(option);
    });

    const existing = appState.mappings[field.path];
    if (existing) {
        select.value = existing.source_column;
        applyConfidenceStyle(select, existing.confidence);
    }

    // Sample data button
    const sampleBtn = document.createElement('button');
    sampleBtn.className = 'btn sample-btn';
    sampleBtn.type = 'button';
    sampleBtn.textContent = '✓ View sample';
    sampleBtn.disabled = !select.value;

    // Sample data panel
    const samplePanel = document.createElement('div');
    samplePanel.className = 'sample-panel hidden';

    sampleBtn.addEventListener('click', () => {
        const isNowHidden = samplePanel.classList.toggle('hidden');
        if (!isNowHidden) {
            const samples = sourceColumnMap[select.value] || [];
            samplePanel.innerHTML = samples.length
                ? samples.map(v => `<span class="sample-value">${v}</span>`).join('')
                : '<em class="no-samples">No sample data available</em>';
        }
    });

    select.addEventListener('change', (e) => {
        const sourceColumn = e.target.value;
        sampleBtn.disabled = !sourceColumn;
        samplePanel.classList.add('hidden');

        if (sourceColumn) {
            appState.mappings[field.path] = {
                source_column: sourceColumn,
                target_name: field.name,
                confidence: 1.0
            };
            applyConfidenceStyle(e.target, 1.0);
        } else {
            delete appState.mappings[field.path];
            e.target.style.borderLeft = '';
        }
        updateMappingStatus(appState, elements);
        saveMappingConfiguration(appState);
    });

    selectRow.appendChild(select);
    selectRow.appendChild(sampleBtn);
    item.appendChild(selectRow);
    item.appendChild(samplePanel);
    return item;
}

function applyConfidenceStyle(select, confidence) {
    if (confidence >= 0.8) {
        select.style.borderLeft = '3px solid var(--success-color)';
    } else if (confidence >= 0.6) {
        select.style.borderLeft = '3px solid var(--warning-color)';
    } else {
        select.style.borderLeft = '3px solid var(--error-color)';
    }
}

/**
 * Get only leaf (non-complex) fields, flattened from the schema tree.
 */
function getLeafFields(fields, result = []) {
    fields.forEach(field => {
        const isComplex = (field.children && field.children.length > 0) || field.is_choice;
        if (!isComplex) {
            result.push({ name: field.name, path: field.path, required: field.required });
        }
        if (field.children && field.children.length > 0) {
            getLeafFields(field.children, result);
        }
        if (field.is_choice && field.choice_options) {
            field.choice_options.forEach(option => {
                if (option.name === 'ProjectIDRingerNumber') return;
                if (option.fields) getLeafFields(option.fields, result);
            });
        }
    });
    return result;
}

/**
 * Update mapping status display.
 */
export function updateMappingStatus(appState, elements) {
    const allLeaf = getLeafFields(appState.schemaFields || []);
    const visibleLeaf = allLeaf.filter(f =>
        !HARDCODED_FIELDS.has(f.name) &&
        (appState.biometricsExpanded || !f.path.includes('Biometrics'))
    );

    const requiredFields = visibleLeaf.filter(f => f.required);
    const mappedPaths = new Set(Object.keys(appState.mappings));
    const mappedRequired = requiredFields.filter(f => mappedPaths.has(f.path)).length;
    const mappedTotal = visibleLeaf.filter(f => mappedPaths.has(f.path)).length;

    elements.mappingStatus.innerHTML =
        `Mapped: ${mappedRequired} / ${requiredFields.length} of required XSD fields<br>` +
        `Mapped: ${mappedTotal} / ${visibleLeaf.length} of total XSD fields`;

    if (mappedRequired === requiredFields.length && requiredFields.length > 0) {
        elements.mappingStatus.classList.add('text-success');
        elements.mappingStatus.classList.remove('text-warning');
    } else if (mappedRequired > 0) {
        elements.mappingStatus.classList.add('text-warning');
        elements.mappingStatus.classList.remove('text-success');
    } else {
        elements.mappingStatus.classList.remove('text-success', 'text-warning');
    }
}

/**
 * Save mapping configuration to backend.
 */
export async function saveMappingConfiguration(appState) {
    if (!appState.fileId || !appState.fileType) {
        console.warn('Cannot save mapping: missing file ID or type');
        return;
    }

    if (Object.keys(appState.mappings).length === 0) {
        console.warn('Cannot save mapping: no mappings defined');
        return;
    }

    try {
        const mappings = Object.entries(appState.mappings).map(([targetPath, mapping]) => ({
            source_column: mapping.source_column,
            target_path: targetPath,
            target_name: mapping.target_name,
            confidence: mapping.confidence
        }));

        const response = await fetch(`${API_BASE}/mapping/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_id: appState.fileId,
                file_type: appState.fileType,
                mappings: mappings
            })
        });

        if (!response.ok) {
            throw new Error('Failed to save mapping');
        }

        const data = await response.json();
        appState.mappingId = data.mapping_id;
        console.log('Mapping saved with ID:', data.mapping_id);

    } catch (error) {
        console.error('Error saving mapping:', error);
    }
}
