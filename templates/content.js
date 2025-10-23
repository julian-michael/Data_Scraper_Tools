// File: templates/content.js
(function() {
    'use strict';
    
    console.log('[Web Scraper] Content script loaded for:', window.location.href);
    
    let isScraping = false;
    
    // Default configuration
    let config = {
        selectors: {
            text: {{TEXT_SELECTORS}},
            images: {{IMAGE_SELECTORS}},
            links: {{LINK_SELECTORS}},
            tables: {{TABLE_SELECTORS}},
            custom: {{CUSTOM_SELECTORS}}
        },
        options: {
            extractText: {{EXTRACT_TEXT}},
            extractImages: {{EXTRACT_IMAGES}},
            extractLinks: {{EXTRACT_LINKS}},
            extractTables: {{EXTRACT_TABLES}},
            extractCustom: {{EXTRACT_CUSTOM}}
        }
    };
    
    // Load configuration from storage
    chrome.storage.local.get(['scraperConfig'], function(result) {
        if (result.scraperConfig) {
            config = {...config, ...result.scraperConfig};
            console.log('Loaded configuration from storage:', config);
        }
    });
    
    function scrapeData() {
        if (isScraping) {
            console.log('Scraping already in progress...');
            return null;
        }
        
        isScraping = true;
        console.log('Starting data scraping with config:', config);
        
        const results = {
            texts: [],
            images: [],
            links: [],
            tables: [],
            custom: [],
            metadata: {
                url: window.location.href,
                title: document.title,
                timestamp: new Date().toISOString(),
                source: 'extension',
                config: config
            }
        };
        
        try {
            // Extract texts
            if (config.options.extractText) {
                config.selectors.text.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach((element, index) => {
                            const text = element.textContent?.trim();
                            if (text && text.length > 0 && text.length < 1000) {
                                results.texts.push({
                                    selector: selector,
                                    text: text,
                                    elementIndex: index,
                                    tagName: element.tagName,
                                    className: element.className,
                                    id: element.id
                                });
                            }
                        });
                    } catch (e) {
                        console.error('Error with text selector ' + selector + ':', e);
                    }
                });
            }
            
            // Extract images
            if (config.options.extractImages) {
                config.selectors.images.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach((element, index) => {
                            const src = element.src || element.getAttribute('data-src');
                            const alt = element.alt || element.getAttribute('alt') || 'No alt text';
                            if (src) {
                                results.images.push({
                                    selector: selector,
                                    src: src,
                                    alt: alt,
                                    elementIndex: index,
                                    tagName: element.tagName,
                                    className: element.className,
                                    id: element.id
                                });
                            }
                        });
                    } catch (e) {
                        console.error('Error with image selector ' + selector + ':', e);
                    }
                });
            }
            
            // Extract links
            if (config.options.extractLinks) {
                config.selectors.links.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach((element, index) => {
                            const href = element.href;
                            const text = element.textContent?.trim();
                            if (href && href !== '#' && !href.startsWith('javascript:')) {
                                results.links.push({
                                    selector: selector,
                                    href: href,
                                    text: text || href,
                                    elementIndex: index,
                                    tagName: element.tagName,
                                    className: element.className,
                                    id: element.id
                                });
                            }
                        });
                    } catch (e) {
                        console.error('Error with link selector ' + selector + ':', e);
                    }
                });
            }
            
            // Extract tables
            if (config.options.extractTables) {
                config.selectors.tables.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach((table, tableIndex) => {
                            try {
                                const rows = [];
                                const headers = [];
                                
                                // Get headers
                                const thElements = table.querySelectorAll('th');
                                thElements.forEach(th => {
                                    headers.push(th.textContent?.trim() || '');
                                });
                                
                                // Get rows
                                const trElements = table.querySelectorAll('tr');
                                trElements.forEach(tr => {
                                    const row = [];
                                    const cells = tr.querySelectorAll('td, th');
                                    cells.forEach(cell => {
                                        row.push(cell.textContent?.trim() || '');
                                    });
                                    if (row.length > 0) {
                                        rows.push(row);
                                    }
                                });
                                
                                if (rows.length > 0) {
                                    results.tables.push({
                                        selector: selector,
                                        tableIndex: tableIndex,
                                        headers: headers,
                                        rows: rows
                                    });
                                }
                            } catch (e) {
                                console.error('Error processing table:', e);
                            }
                        });
                    } catch (e) {
                        console.error('Error with table selector ' + selector + ':', e);
                    }
                });
            }
            
            // Extract custom elements
            if (config.options.extractCustom) {
                config.selectors.custom.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach((element, index) => {
                            const text = element.textContent?.trim();
                            if (text) {
                                results.custom.push({
                                    selector: selector,
                                    text: text,
                                    elementIndex: index,
                                    tagName: element.tagName,
                                    className: element.className,
                                    id: element.id,
                                    html: element.outerHTML,
                                    attributes: Array.from(element.attributes).reduce((acc, attr) => {
                                        acc[attr.name] = attr.value;
                                        return acc;
                                    }, {})
                                });
                            }
                        });
                    } catch (e) {
                        console.error('Error with custom selector ' + selector + ':', e);
                    }
                });
            }
            
            console.log('Scraping completed. Found:', {
                texts: results.texts.length,
                images: results.images.length,
                links: results.links.length,
                tables: results.tables.length,
                custom: results.custom.length
            });
            
        } catch (error) {
            console.error('Error during scraping:', error);
            results.error = error.message;
        } finally {
            isScraping = false;
        }
        
        return results;
    }
    
    // Send data to server
    function sendToServer(data) {
        return fetch('http://127.0.0.1:5584/store', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(result => {
            console.log('Data sent to server successfully:', result);
            return result;
        })
        .catch(error => {
            console.error('Error sending data to server:', error);
            throw error;
        });
    }
    
    // Listen for messages from popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        console.log('Received message in content script:', request);
        
        if (request.action === 'scrape') {
            console.log('Starting scrape from content script...');
            
            // Execute scraping and send to server
            const data = scrapeData();
            
            if (data) {
                sendToServer(data)
                    .then(result => {
                        sendResponse({success: true, data: data, serverResponse: result});
                    })
                    .catch(error => {
                        sendResponse({success: false, error: error.message});
                    });
            } else {
                sendResponse({success: false, error: 'Scraping already in progress'});
            }
            
            return true; // Keep message channel open for async response
        }
        
        if (request.action === 'updateConfig') {
            console.log('Updating configuration:', request.config);
            config = {...config, ...request.config};
            // Save to storage
            chrome.storage.local.set({scraperConfig: config});
            sendResponse({success: true, config: config});
            return true;
        }
        
        if (request.action === 'getConfig') {
            sendResponse({success: true, config: config});
            return true;
        }
        
        return false;
    });
    
    console.log('Web Scraper content script initialized successfully');
    
})();