import os
import json
import zipfile
import shutil

class ExtensionManager:
    def __init__(self):
        self.extension_dir = "chrome_extension"
        self.manifest = {
            "manifest_version": 3,
            "name": "Web Scraper",
            "version": "1.0",
            "description": "Scrape data from web pages",
            "permissions": ["activeTab", "scripting"],
            "action": {
                "default_popup": "popup.html",
                "default_title": "Web Scraper"
            },
            "content_scripts": [
                {
                    "matches": ["<all_urls>"],
                    "js": ["content.js"]
                }
            ],
            "host_permissions": ["<all_urls>"]
        }

    def create_extension(self, config):
        """Create the Chrome extension with given configuration"""
        try:
            # Create extension directory
            if os.path.exists(self.extension_dir):
                shutil.rmtree(self.extension_dir)
            os.makedirs(self.extension_dir)
            
            # Create manifest.json
            with open(os.path.join(self.extension_dir, "manifest.json"), "w") as f:
                json.dump(self.manifest, f, indent=2)
            
            # Create popup.html
            self.create_popup_html()
            
            # Create content.js with configuration
            self.create_content_js(config)
            
            return os.path.abspath(self.extension_dir)
            
        except Exception as e:
            raise Exception(f"Failed to create extension: {str(e)}")

    def create_popup_html(self):
        """Create the extension popup HTML"""
        popup_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { width: 300px; padding: 10px; font-family: Arial, sans-serif; }
        button { width: 100%; padding: 10px; margin: 5px 0; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #45a049; }
        #status { margin: 10px 0; padding: 10px; border-radius: 4px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .loading { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <h3>Web Scraper</h3>
    <button id="scrapeBtn">Start Scraping</button>
    <div id="status"></div>
    
    <script src="popup.js"></script>
</body>
</html>
        """
        
        with open(os.path.join(self.extension_dir, "popup.html"), "w") as f:
            f.write(popup_html)

    def create_content_js(self, config):
        """Create content script with configuration"""
        content_js = f"""
const config = {json.dumps(config, indent=2)};

function scrapeData() {{
    const results = {{
        texts: [],
        images: [],
        links: [],
        tables: [],
        custom: [],
        metadata: {{
            url: window.location.href,
            timestamp: new Date().toISOString(),
            title: document.title,
            source: 'extension'
        }}
    }};

    // Extract texts
    if (config.extract_text) {{
        config.text_selectors.forEach(selector => {{
            try {{
                document.querySelectorAll(selector).forEach(element => {{
                    const text = element.textContent.trim();
                    if (text) {{
                        results.texts.push({{
                            selector: selector,
                            text: text.substring(0, 500),
                            full_text: text
                        }});
                    }}
                }});
            }} catch (e) {{
                console.error('Error with selector:', selector, e);
            }}
        }});
    }}

    // Extract custom elements
    if (config.extract_custom && config.custom_selectors) {{
        config.custom_selectors.forEach(selector => {{
            try {{
                document.querySelectorAll(selector).forEach((element, index) => {{
                    const text = element.textContent.trim();
                    if (text) {{
                        results.custom.push({{
                            selector: selector,
                            index: index,
                            text: text.substring(0, 500),
                            full_text: text,
                            html: element.outerHTML.substring(0, 1000)
                        }});
                    }}
                }});
            }} catch (e) {{
                console.error('Error with custom selector:', selector, e);
            }}
        }});
    }}

    return results;
}}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {{
    if (request.action === "scrape") {{
        const data = scrapeData();
        sendResponse({{data: data}});
    }}
    return true;
}});
        """
        
        with open(os.path.join(self.extension_dir, "content.js"), "w") as f:
            f.write(content_js)
            
        # Create popup.js
        popup_js = """
document.getElementById('scrapeBtn').addEventListener('click', async () => {
    const status = document.getElementById('status');
    status.className = 'loading';
    status.textContent = 'Scraping...';
    
    try {
        const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
        const response = await chrome.tabs.sendMessage(tab.id, {action: "scrape"});
        
        if (response && response.data) {
            // Send data to backend
            const result = await fetch('http://127.0.0.1:5584/store', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(response.data)
            });
            
            if (result.ok) {
                status.className = 'success';
                status.textContent = `✅ Data sent! ${response.data.texts.length} texts, ${response.data.custom.length} custom elements`;
            } else {
                throw new Error('Failed to send data to server');
            }
        } else {
            throw new Error('No data received from content script');
        }
    } catch (error) {
        status.className = 'error';
        status.textContent = `❌ Error: ${error.message}`;
        console.error('Scraping error:', error);
    }
});
        """
        
        with open(os.path.join(self.extension_dir, "popup.js"), "w") as f:
            f.write(popup_js)

    def create_extension_zip(self):
        """Create a ZIP file of the extension"""
        zip_path = "web_scraper_extension.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(self.extension_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.extension_dir)
                    zipf.write(file_path, arcname)
        return zip_path