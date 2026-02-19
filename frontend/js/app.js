// Main application logic
import { setupFileUpload } from './file-upload.js';
import { setupColumnMapper } from './column-mapper.js';
import { setupSchemaViewer, setupSchemaSelector } from './schema-viewer.js';
import { setupXmlGenerator } from './xml-generator.js';

const API_BASE = '/api';

// State management
const appState = {
    uploadedFile: null,
    fileId: null,
    fileType: null,
    selectedSchemaId: null,  // populated after Step 2
    sourceColumns: [],
    schemaFields: [],
    mappings: {},
    biometricsExpanded: false,
    validationResults: null,
    generatedXmlId: null,
    supportedExtensions: [],  // populated from /api/parsers on startup
    advancedOverrides: {}     // keyed by field name, set by the Advanced panel
};

// DOM elements
const elements = {
    uploadArea: document.getElementById('upload-area'),
    fileInput: document.getElementById('file-input'),
    browseBtn: document.getElementById('browse-btn'),
    fileInfo: document.getElementById('file-info'),
    fileName: document.getElementById('file-name'),
    fileSize: document.getElementById('file-size'),
    changeFileBtn: document.getElementById('change-file-btn'),
    parseBtn: document.getElementById('parse-btn'),

    schemaSection: document.getElementById('schema-section'),
    schemaSelection: document.getElementById('schema-selection'),
    schemaInfo: document.getElementById('schema-info'),
    schemaNameDisplay: document.getElementById('schema-name-display'),
    schemaList: document.getElementById('schema-list'),
    schemaFileInput: document.getElementById('schema-file-input'),
    schemaUploadStatus: document.getElementById('schema-upload-status'),
    useSchemaBtn: document.getElementById('use-schema-btn'),
    changeSchemaBtn: document.getElementById('change-schema-btn'),

    mappingSection: document.getElementById('mapping-section'),
    mappingControls: document.getElementById('mapping-controls'),
    mappingStatus: document.getElementById('mapping-status'),
    targetFields: document.getElementById('target-fields'),
    biometricsContainer: document.getElementById('biometrics-container'),
    biometricsFields: document.getElementById('biometrics-fields'),

    validationSection: document.getElementById('validation-section'),
    validateBtn: document.getElementById('validate-btn'),
    validationResults: document.getElementById('validation-results'),

    generateSection: document.getElementById('generate-section'),
    generateBtn: document.getElementById('generate-btn'),
    advancedToggleBtn: document.getElementById('advanced-toggle-btn'),
    advancedPanel: document.getElementById('advanced-panel'),
    xmlPreview: document.getElementById('xml-preview'),
    xmlContent: document.getElementById('xml-content'),
    downloadBtn: document.getElementById('download-btn'),

    loadingOverlay: document.getElementById('loading-overlay'),
    loadingMessage: document.getElementById('loading-message')
};

// ── Theme toggle ────────────────────────────────────────────────────────────
const themeToggleBtn = document.getElementById('theme-toggle');

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    themeToggleBtn.textContent = theme === 'dark' ? '☀' : '☾';
    localStorage.setItem('theme', theme);
}

(function initTheme() {
    const saved = localStorage.getItem('theme');
    const preferred = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    applyTheme(saved || preferred);
})();

themeToggleBtn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
});

// Initialize app
async function init() {
    await loadSupportedExtensions();
    setupEventListeners();
    checkApiHealth();
}

async function loadSupportedExtensions() {
    try {
        const response = await fetch(`${API_BASE}/parsers`);
        const data = await response.json();
        appState.supportedExtensions = data.supported_extensions;  // e.g. ['.csv', '.xlsx']
        // Keep the file input and prompt text in sync with the registry
        elements.fileInput.accept = appState.supportedExtensions.join(',');
        const exts = appState.supportedExtensions.map(e => e.toLowerCase().slice(1));
        const label = exts.length > 1
            ? exts.slice(0, -1).join(', ') + ' or ' + exts.at(-1)
            : exts[0] ?? '';
        document.getElementById('upload-prompt-text').textContent = `Drag and drop your ${label} file here`;
        document.getElementById('subtitle-text').textContent = `Map ${label} files to an XML Schema for Griel Bulkupload`;
        document.title = `RingParser`;
    } catch (error) {
        console.warn('Could not load supported extensions, falling back to defaults:', error);
        appState.supportedExtensions = ['.csv', '.xlsx'];
    }
}

// Setup event listeners
function setupEventListeners() {
    // File upload (Step 1)
    setupFileUpload(appState, elements);

    // Schema selector (Step 2)
    setupSchemaSelector(appState, elements);

    // Column mapper (Step 3)
    setupColumnMapper(appState, elements);

    // Schema viewer / validation (Step 4)
    setupSchemaViewer(appState, elements);

    // XML generator (Step 5)
    setupXmlGenerator(appState, elements);
}

// Check API health
async function checkApiHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        console.log('API Status:', data.message);
    } catch (error) {
        console.error('API connection error:', error);
        showError('Cannot connect to backend API. Make sure the server is running.');
    }
}

// UI helper functions
window.showLoading = function(message = 'Loading...') {
    elements.loadingMessage.textContent = message;
    elements.loadingOverlay.classList.remove('hidden');
};

window.hideLoading = function() {
    elements.loadingOverlay.classList.add('hidden');
};

window.showError = function(message) {
    console.error(message);
    alert('Error: ' + message);
};

window.showSuccess = function(message) {
    console.log('Success:', message);
};

window.showInfo = function(message) {
    console.log('Info:', message);
    alert(message);
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

export { appState, API_BASE, elements };
