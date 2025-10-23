# File: extension_scraper.py
import time
from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class ExtensionScrapingThread(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    data_received = pyqtSignal(dict)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, extension_path):
        super().__init__()
        self.extension_path = extension_path
        self.is_running = True
        self.driver = None

    def run(self):
        try:
            self.message.emit("🚀 Starting Chrome browser with extension...")
            
            # Configure Chrome with extension
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"--load-extension={self.extension_path}")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Install ChromeDriver
            self.message.emit("📥 Installing ChromeDriver...")
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path)
            
            self.message.emit("🔧 Starting Chrome browser...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.progress.emit(100)
            self.message.emit("✅ Chrome browser launched successfully!")
            self.message.emit("📋 Manual Installation Instructions:")
            self.message.emit("1. Open Chrome and go to: chrome://extensions/")
            self.message.emit("2. Enable 'Developer mode' (toggle in top-right)")
            self.message.emit("3. Click 'Load unpacked' button")
            self.message.emit("4. Select this folder: " + self.extension_path)
            self.message.emit("5. The extension will appear in your toolbar")
            self.message.emit("6. Navigate to any website and click the extension icon")
            self.message.emit("7. Click 'Start Scraping' to extract data")
            
            # Open extensions page for easy installation
            self.driver.get("chrome://extensions/")
            self.message.emit("🌐 Opened Chrome extensions page for easy installation")
            
            # Keep the thread running
            while self.is_running:
                time.sleep(1)
                
        except Exception as e:
            self.error.emit(f"❌ Failed to start browser: {str(e)}")

    def stop(self):
        """Stop the extension scraping"""
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.finished.emit()