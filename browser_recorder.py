import time
import json
from PyQt5.QtCore import QObject, pyqtSignal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

class BrowserRecorder(QObject):
    action_recorded = pyqtSignal(dict)
    status_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.driver = None
        self.is_recording = False
        self.recorded_actions = []
        self.current_step = 0
        
    def start_recording(self, url):
        """Start recording with a simple URL"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Inject recording script
            self.inject_recorder_script()
            
            self.driver.get(url)
            self.is_recording = True
            self.recorded_actions = []
            self.current_step = 0
            
            self.record_action('navigate', url, f"Go to {url}")
            self.status_updated.emit("🔴 Recording started! Just use the browser normally...")
            
        except Exception as e:
            self.status_updated.emit(f"❌ Failed to start recording: {str(e)}")
            
    def inject_recorder_script(self):
        """Inject JavaScript to capture user interactions"""
        script = """
        // Create overlay to show recording status
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #dc3545;
            color: white;
            padding: 10px;
            border-radius: 5px;
            z-index: 10000;
            font-family: Arial;
            font-weight: bold;
        `;
        overlay.textContent = '🔴 RECORDING';
        document.body.appendChild(overlay);
        
        // Track clicks
        document.addEventListener('click', function(e) {
            const target = e.target;
            const selector = getSelector(target);
            const text = target.textContent?.trim().substring(0, 50) || '';
            
            window.pywebview?.postMessage({
                type: 'click',
                selector: selector,
                text: text,
                url: window.location.href
            });
        }, true);
        
        // Track form inputs
        document.addEventListener('input', function(e) {
            const target = e.target;
            if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
                const selector = getSelector(target);
                
                window.pywebview?.postMessage({
                    type: 'input',
                    selector: selector,
                    value: target.value,
                    url: window.location.href
                });
            }
        }, true);
        
        // Track navigation
        let currentUrl = window.location.href;
        setInterval(() => {
            if (window.location.href !== currentUrl) {
                window.pywebview?.postMessage({
                    type: 'navigation',
                    url: window.location.href,
                    from: currentUrl
                });
                currentUrl = window.location.href;
            }
        }, 500);
        
        // Helper function to generate CSS selector
        function getSelector(element) {
            if (element.id) return '#' + element.id;
            
            let selector = element.tagName.toLowerCase();
            if (element.className) {
                selector += '.' + element.className.trim().replace(/\\s+/g, '.');
            }
            
            // Add some uniqueness
            if (element.parentElement) {
                const siblings = Array.from(element.parentElement.children);
                const index = siblings.indexOf(element) + 1;
                if (siblings.length > 1) {
                    selector += `:nth-child(${index})`;
                }
            }
            
            return selector;
        }
        """
        self.driver.execute_script(script)
        
    def record_action(self, action_type, target, description, value=None):
        """Record an action with automatic description"""
        self.current_step += 1
        
        action = {
            'step': self.current_step,
            'type': action_type,
            'target': target,
            'value': value,
            'description': description,
            'timestamp': time.time(),
            'url': self.driver.current_url if self.driver else ''
        }
        
        self.recorded_actions.append(action)
        self.action_recorded.emit(action)
        
    def stop_recording(self):
        """Stop recording and close browser"""
        self.is_recording = False
        if self.driver:
            self.driver.quit()
            self.driver = None
        self.status_updated.emit("⏹️ Recording stopped")
        
    def get_recorded_actions(self):
        return self.recorded_actions.copy()
    
    def save_workflow(self, filename):
        """Save the recorded workflow"""
        workflow = {
            'actions': self.recorded_actions,
            'metadata': {
                'created_at': time.time(),
                'total_steps': len(self.recorded_actions),
                'description': 'Automatically recorded workflow'
            }
        }
        with open(filename, 'w') as f:
            json.dump(workflow, f, indent=2)
        return filename
    
    def add_manual_step(self, step_type, description):
        """Allow user to add manual steps if needed"""
        if self.is_recording:
            self.record_action(step_type, 'manual', description)