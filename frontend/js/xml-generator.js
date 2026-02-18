// XML generation and download functionality
const API_BASE = '/api';

/**
 * Setup XML generator event listeners
 */
export function setupXmlGenerator(appState, elements) {
    elements.generateBtn.addEventListener('click', () => generateXml(appState, elements));
    elements.downloadBtn.addEventListener('click', () => downloadXml(appState, elements));
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
                mapping_id: appState.mappingId
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
export async function downloadXml(appState, elements) {
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
