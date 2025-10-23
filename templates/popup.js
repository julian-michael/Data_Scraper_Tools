let isScraping = false;
let isDynamicMode = false;
let scrapeInterval = null;
let currentConfig = {};
let dynamicIntervalMs = 3000; // default 3 seconds

// -------------------------------
// Tab functionality
// -------------------------------
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

        button.classList.add('active');
        const tabId = button.getAttribute('data-tab') + '-tab';
        document.getElementById(tabId).classList.add('active');
    });
});

// -------------------------------
// Status update utility
// -------------------------------
function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = 'status ' + type;
}

// -------------------------------
// Display results
// -------------------------------
function showResults(data) {
    const resultsEl = document.getElementById('results');
    const contentEl = document.getElementById('resultsContent');

    let html = '<div style="margin-top: 5px;">';
    html += '<div>📝 Texts: ' + (data.texts?.length || 0) + '</div>';
    html += '<div>🖼️ Images: ' + (data.images?.length || 0) + '</div>';
    html += '<div>🔗 Links: ' + (data.links?.length || 0) + '</div>';
    html += '<div>📊 Tables: ' + (data.tables?.length || 0) + '</div>';
    html += '<div>🎯 Custom: ' + (data.custom?.length || 0) + '</div>';
    html += '</div>';

    contentEl.innerHTML = html;
    resultsEl.style.display = 'block';
}

// -------------------------------
// Button toggle
// -------------------------------
function toggleButtons(scraping) {
    document.getElementById('scrapeBtn').style.display = scraping ? 'none' : 'block';
    document.getElementById('stopBtn').style.display = scraping ? 'block' : 'none';
}

// -------------------------------
// Load configuration
// -------------------------------
function loadConfig() {
    chrome.storage.local.get(['scraperConfig', 'pageType', 'intervalMs'], function(result) {
        if (result.scraperConfig) {
            currentConfig = result.scraperConfig;
            updateFormWithConfig(currentConfig);
        } else {
            loadDefaultConfig();
        }

        // Page type
        document.getElementById('pageType').value = result.pageType || 'static';
        isDynamicMode = result.pageType === 'dynamic';

        // Interval
        document.getElementById('intervalMs').value = result.intervalMs || dynamicIntervalMs;
        dynamicIntervalMs = parseInt(result.intervalMs || dynamicIntervalMs);
    });
}

function loadDefaultConfig() {
    currentConfig = {
        selectors: {
            text: ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span'],
            images: ['img'],
            links: ['a'],
            tables: ['table'],
            custom: []
        },
        options: {
            extractText: true,
            extractImages: true,
            extractLinks: true,
            extractTables: true,
            extractCustom: true
        }
    };
    updateFormWithConfig(currentConfig);
}

function updateFormWithConfig(config) {
    document.getElementById('textSelectors').value = config.selectors.text.join(', ');
    document.getElementById('imageSelectors').value = config.selectors.images.join(', ');
    document.getElementById('linkSelectors').value = config.selectors.links.join(', ');
    document.getElementById('tableSelectors').value = config.selectors.tables.join(', ');
    document.getElementById('customSelectors').value = config.selectors.custom.join(', ');

    document.getElementById('extractText').checked = config.options.extractText;
    document.getElementById('extractImages').checked = config.options.extractImages;
    document.getElementById('extractLinks').checked = config.options.extractLinks;
    document.getElementById('extractTables').checked = config.options.extractTables;
    document.getElementById('extractCustom').checked = config.options.extractCustom;
}

function getConfigFromForm() {
    return {
        selectors: {
            text: document.getElementById('textSelectors').value.split(',').map(s => s.trim()).filter(s => s),
            images: document.getElementById('imageSelectors').value.split(',').map(s => s.trim()).filter(s => s),
            links: document.getElementById('linkSelectors').value.split(',').map(s => s.trim()).filter(s => s),
            tables: document.getElementById('tableSelectors').value.split(',').map(s => s.trim()).filter(s => s),
            custom: document.getElementById('customSelectors').value.split(',').map(s => s.trim()).filter(s => s)
        },
        options: {
            extractText: document.getElementById('extractText').checked,
            extractImages: document.getElementById('extractImages').checked,
            extractLinks: document.getElementById('extractLinks').checked,
            extractTables: document.getElementById('extractTables').checked,
            extractCustom: document.getElementById('extractCustom').checked
        }
    };
}

// -------------------------------
// Core scraping logic
// -------------------------------
async function performScrape() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        const response = await chrome.tabs.sendMessage(tab.id, { action: 'scrape' });

        if (response && response.success) {
            updateStatus('✅ Data scraped successfully!', 'success');
            showResults(response.data);

            // Send data to backend
            fetch('http://127.0.0.1:5584/store', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(response.data)
            }).catch(err => console.warn('Backend send error:', err));
        } else {
            updateStatus('❌ Failed to extract data', 'error');
        }
    } catch (error) {
        console.error('Scrape error:', error);
        if (error.message.includes('Could not establish connection')) {
            updateStatus('❌ Please refresh the page and try again', 'error');
        } else {
            updateStatus('❌ ' + error.message, 'error');
        }
    }
}

// -------------------------------
// Event Listeners
// -------------------------------
document.getElementById('scrapeBtn').addEventListener('click', async () => {
    if (isScraping) return;

    isScraping = true;
    toggleButtons(true);
    updateStatus('Scraping started...', 'loading');
    document.getElementById('results').style.display = 'none';

    if (isDynamicMode) {
        // Dynamic continuous scraping
        updateStatus('Dynamic scraping active (every ' + dynamicIntervalMs + 'ms)...', 'loading');
        scrapeInterval = setInterval(performScrape, dynamicIntervalMs);
    } else {
        // Static single scrape
        await performScrape();
        isScraping = false;
        toggleButtons(false);
    }
});

document.getElementById('stopBtn').addEventListener('click', () => {
    if (scrapeInterval) {
        clearInterval(scrapeInterval);
        scrapeInterval = null;
    }
    isScraping = false;
    toggleButtons(false);
    updateStatus('Scraping stopped', 'info');
});

document.getElementById('saveConfig').addEventListener('click', async () => {
    const newConfig = getConfigFromForm();
    const pageType = document.getElementById('pageType').value;
    const intervalValue = parseInt(document.getElementById('intervalMs').value) || 3000;

    isDynamicMode = pageType === 'dynamic';
    dynamicIntervalMs = intervalValue;

    chrome.storage.local.set({
        scraperConfig: newConfig,
        pageType: pageType,
        intervalMs: intervalValue
    });

    updateStatus('✅ Configuration saved!', 'success');
    document.querySelector('[data-tab="scrape"]').click();
});

document.getElementById('resetConfig').addEventListener('click', () => {
    loadDefaultConfig();
    updateStatus('Configuration reset to defaults', 'info');
});

// -------------------------------
// Initialize
// -------------------------------
loadConfig();
updateStatus('Ready to scrape...', 'info');
