import sys
import os
import time
import json
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QWidget, QLabel, QLineEdit, QCheckBox,
    QTextEdit, QGroupBox, QGridLayout, QProgressBar, QTabWidget, QSpinBox
)
from PyQt5.QtCore import Qt
from flask_server import FlaskServerThread
from extension_manager import ExtensionManager
from selenium_scraper import SeleniumScrapingThread
from data_manager import DataManager
from robot_process import RobotProcessManager
from robot_process_ui import RobotProcessUI

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Web Scraper - Two Methods")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize components
        self.extension_manager = ExtensionManager()
        self.flask_server = FlaskServerThread()
        self.extension_thread = None
        self.selenium_thread = None
        self.robot_manager = RobotProcessManager()

        
        # Initialize Data Manager
        self.data_manager = DataManager(self)
        
        # Setup GUI
        self.setup_gui()
        
        # Start Flask server
        self.flask_server.data_received.connect(self.handle_received_data)
        self.flask_server.message.connect(self.update_extension_status)
        self.flask_server.start()
        
        # Wait for Flask server to start
        self.wait_for_flask_server()
        
        # Load default configuration
        self.load_default_config()

    def setup_gui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Extension Method Tab
        self.setup_extension_tab()
        
        # Selenium Method Tab
        self.setup_selenium_tab()
        
        # Robot Process Tab
        self.setup_robot_process_tab()
        
        # Data Manager Tab
        self.tabs.addTab(self.data_manager.get_tab(), "📊 Data Manager")
    
    def setup_robot_process_tab(self):
        """Setup the Robot Process automation tab"""
        self.robot_process_ui = RobotProcessUI(self.robot_manager)
        self.robot_process_ui.data_received.connect(self.handle_received_data)
        self.tabs.addTab(self.robot_process_ui, "🤖 Robot Process")
        
    def setup_extension_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Title
        title_label = QLabel("🕷️ Extension-Based Scraping")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "This method creates a Chrome extension that you can use to scrape any website manually.\n"
            "Create the extension, install it in Chrome manually, then use the extension popup to scrape data."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin: 10px; color: #34495e;")
        layout.addWidget(desc_label)

        # Extension Configuration
        config_frame = QGroupBox("Extension Configuration")
        config_layout = QGridLayout(config_frame)
        
        row = 0
        
        # Text Selectors
        config_layout.addWidget(QLabel("Text Selectors:"), row, 0)
        self.text_selectors_input = QLineEdit()
        self.text_selectors_input.setText("p, h1, h2, h3, h4, h5, h6, div, span")
        self.text_selectors_input.setToolTip("CSS selectors for text elements (comma separated)")
        config_layout.addWidget(self.text_selectors_input, row, 1)
        row += 1
        
        # Custom Selectors
        config_layout.addWidget(QLabel("Custom Selectors:"), row, 0)
        self.custom_selectors_input = QLineEdit()
        self.custom_selectors_input.setPlaceholderText(".product, .price, [data-role], ...")
        self.custom_selectors_input.setToolTip("Additional CSS selectors for specific elements")
        config_layout.addWidget(self.custom_selectors_input, row, 1)
        row += 1
        
        # Options
        self.extract_text_cb = QCheckBox("Extract Text")
        self.extract_text_cb.setChecked(True)
        config_layout.addWidget(self.extract_text_cb, row, 0)
        
        self.extract_images_cb = QCheckBox("Extract Images")
        self.extract_images_cb.setChecked(True)
        config_layout.addWidget(self.extract_images_cb, row, 1)
        row += 1
        
        self.extract_links_cb = QCheckBox("Extract Links")
        self.extract_links_cb.setChecked(True)
        config_layout.addWidget(self.extract_links_cb, row, 0)
        
        self.extract_tables_cb = QCheckBox("Extract Tables")
        self.extract_tables_cb.setChecked(True)
        config_layout.addWidget(self.extract_tables_cb, row, 1)
        
        layout.addWidget(config_frame)

        # Extension Controls
        control_frame = QGroupBox("Extension Controls")
        control_layout = QVBoxLayout(control_frame)
        
        # Create Extension Button
        self.create_ext_btn = QPushButton("🛠️ Create Chrome Extension")
        self.create_ext_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; padding: 12px; border-radius: 6px; }")
        self.create_ext_btn.clicked.connect(self.create_extension)
        control_layout.addWidget(self.create_ext_btn)
        
        # Open Folder Button
        self.open_folder_btn = QPushButton("📁 Open Extension Folder")
        self.open_folder_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; padding: 12px; border-radius: 6px; }")
        self.open_folder_btn.clicked.connect(self.open_extension_folder)
        self.open_folder_btn.setEnabled(False)
        control_layout.addWidget(self.open_folder_btn)
        
        # Instructions
        instructions_label = QLabel(
            "📋 Installation Steps:\n"
            "1. Click 'Create Chrome Extension' above\n"
            "2. Click 'Open Extension Folder'\n"
            "3. Open Chrome and go to: chrome://extensions/\n"
            "4. Enable 'Developer mode' (toggle in top-right)\n"
            "5. Click 'Load unpacked' button\n"
            "6. Select the extension folder that opened\n"
            "7. The extension will appear in Chrome toolbar\n"
            "8. Navigate to any website and click the extension icon\n"
            "9. Click 'Start Scraping' in the popup\n"
            "10. Data will appear in 'Data Manager' tab"
        )
        instructions_label.setWordWrap(True)
        instructions_label.setStyleSheet("background-color: #f8f9fa; padding: 15px; border-radius: 6px; color: #495057; border: 1px solid #dee2e6; font-size: 10pt;")
        control_layout.addWidget(instructions_label)
        
        layout.addWidget(control_frame)
        
        # Status
        status_frame = QGroupBox("Extension Status")
        status_layout = QVBoxLayout(status_frame)
        
        self.extension_status = QTextEdit()
        self.extension_status.setMaximumHeight(200)
        self.extension_status.setReadOnly(True)
        self.extension_status.setStyleSheet("font-family: 'Courier New'; font-size: 10pt; background-color: #f8f9fa;")
        status_layout.addWidget(self.extension_status)
        
        layout.addWidget(status_frame)
        
        self.tabs.addTab(tab, "🕷️ Extension Method")

    def setup_selenium_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Title
        title_label = QLabel("🤖 Selenium-Based Scraping")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "This method uses Selenium to automatically scrape data from a specified URL.\n"
            "Enter the target URL, configure options, and click Start to begin automated scraping."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin: 10px; color: #34495e;")
        layout.addWidget(desc_label)

        # URL Input
        url_frame = QGroupBox("Target Website")
        url_layout = QHBoxLayout(url_frame)
        
        url_layout.addWidget(QLabel("URL:"))
        self.selenium_url_input = QLineEdit()
        self.selenium_url_input.setPlaceholderText("https://example.com")
        self.selenium_url_input.setText("https://www.example.com")
        url_layout.addWidget(self.selenium_url_input)
        
        layout.addWidget(url_frame)

        # Selenium Options
        options_frame = QGroupBox("Selenium Options")
        options_layout = QGridLayout(options_frame)
        
        row = 0
        
        # Custom HTML Tag
        options_layout.addWidget(QLabel("Custom HTML Tag:"), row, 0)
        self.custom_tag_input = QLineEdit()
        self.custom_tag_input.setPlaceholderText("e.g., article, section, .price, #id")
        self.custom_tag_input.setToolTip("Enter HTML tag or CSS selector to scrape")
        options_layout.addWidget(self.custom_tag_input, row, 1)
        
        self.extract_custom_tag_cb = QCheckBox("Extract Custom Tag")
        self.extract_custom_tag_cb.setChecked(False)
        options_layout.addWidget(self.extract_custom_tag_cb, row, 2)
        row += 1
        
        self.selenium_headless_cb = QCheckBox("Headless Mode (run in background)")
        self.selenium_headless_cb.setChecked(False)
        options_layout.addWidget(self.selenium_headless_cb, row, 0)
        
        self.selenium_dynamic_cb = QCheckBox("Continuous Scraping (Dynamic Pages)")
        self.selenium_dynamic_cb.setChecked(False)
        options_layout.addWidget(self.selenium_dynamic_cb, row, 1)
        row += 1
        
        options_layout.addWidget(QLabel("Scroll Delay (seconds):"), row, 0)
        self.selenium_scroll_delay = QSpinBox()
        self.selenium_scroll_delay.setRange(1, 10)
        self.selenium_scroll_delay.setValue(2)
        options_layout.addWidget(self.selenium_scroll_delay, row, 1)
        
        options_layout.addWidget(QLabel("Max Scroll Attempts:"), row, 2)
        self.selenium_max_scroll = QSpinBox()
        self.selenium_max_scroll.setRange(1, 20)
        self.selenium_max_scroll.setValue(5)
        options_layout.addWidget(self.selenium_max_scroll, row, 3)
        row += 1
        
        # Dynamic interval widget
        options_layout.addWidget(QLabel("Dynamic Scraping Interval (seconds):"), row, 0)
        self.dynamic_interval = QSpinBox()
        self.dynamic_interval.setRange(1, 60)
        self.dynamic_interval.setValue(5)
        self.dynamic_interval.setToolTip("Interval between scrapes for dynamic pages")
        options_layout.addWidget(self.dynamic_interval, row, 1)
        
        layout.addWidget(options_frame)

        # Instructions
        instructions_frame = QGroupBox("Usage Instructions")
        instructions_layout = QVBoxLayout(instructions_frame)
        
        instructions_text = QLabel(
            "🔐 For websites requiring login:\n"
            "1. UNCHECK 'Headless Mode'\n"
            "2. Click 'Start Browser'\n"
            "3. Browser will open with your sessions\n"
            "4. Log in manually if needed\n" 
            "5. Navigate to the page you want to scrape\n"
            "6. Click 'Start Scraping' when ready\n\n"
            "🔄 Continuous Mode:\n"
            "• Check 'Continuous Scraping' to keep browser open\n"
            "• Data will be scraped repeatedly until you click Stop\n"
            "• Perfect for real-time data monitoring\n\n"
            "🎯 For specific elements:\n"
            "• Custom HTML Tag: 'div.price' or '.buttonText-hw_3o_pb'\n"
            "• Custom Selectors: '.price, .button, [data-role]'"
        )
        instructions_text.setWordWrap(True)
        instructions_text.setStyleSheet("background-color: #f0f8ff; padding: 15px; border-radius: 6px; color: #0066cc; border: 1px solid #b3d9ff; font-size: 10pt;")
        instructions_layout.addWidget(instructions_text)
        
        layout.addWidget(instructions_frame)

        # Controls - Split into two rows
        control_frame = QGroupBox("Selenium Controls")
        control_layout = QVBoxLayout(control_frame)
        
        # Row 1: Browser controls
        browser_row = QHBoxLayout()
        
        self.start_browser_btn = QPushButton("🚀 Start Browser")
        self.start_browser_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; padding: 12px; border-radius: 6px; }")
        self.start_browser_btn.clicked.connect(self.start_selenium_browser)
        browser_row.addWidget(self.start_browser_btn)
        
        self.stop_selenium_btn = QPushButton("🛑 Stop Selenium")
        self.stop_selenium_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 12px; border-radius: 6px; }")
        self.stop_selenium_btn.clicked.connect(self.stop_selenium_scraping)
        self.stop_selenium_btn.setEnabled(False)
        browser_row.addWidget(self.stop_selenium_btn)
        
        control_layout.addLayout(browser_row)
        
        # Row 2: Scraping control (appears when browser is ready)
        self.scraping_row = QHBoxLayout()
        
        self.start_scraping_btn = QPushButton("📥 Start Scraping Now")
        self.start_scraping_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 12px; border-radius: 6px; }")
        self.start_scraping_btn.clicked.connect(self.start_scraping_now)
        self.start_scraping_btn.setEnabled(False)
        self.start_scraping_btn.setVisible(False)
        self.scraping_row.addWidget(self.start_scraping_btn)
        
        self.scraping_row.addStretch()
        control_layout.addLayout(self.scraping_row)
        
        layout.addWidget(control_frame)

        # Progress
        self.selenium_progress = QProgressBar()
        self.selenium_progress.setStyleSheet("QProgressBar { height: 20px; border-radius: 10px; } QProgressBar::chunk { background-color: #007bff; border-radius: 10px; }")
        layout.addWidget(self.selenium_progress)

        # Status
        status_frame = QGroupBox("Selenium Status")
        status_layout = QVBoxLayout(status_frame)
        
        self.selenium_status = QTextEdit()
        self.selenium_status.setReadOnly(True)
        self.selenium_status.setStyleSheet("font-family: 'Courier New'; font-size: 10pt; background-color: #f8f9fa;")
        status_layout.addWidget(self.selenium_status)
        
        layout.addWidget(status_frame)
        
        self.tabs.addTab(tab, "🤖 Selenium Method")

    def wait_for_flask_server(self):
        """Wait for Flask server to be ready"""
        max_attempts = 10
        for i in range(max_attempts):
            try:
                response = requests.get('http://127.0.0.1:5000/health', timeout=1)
                if response.status_code == 200:
                    self.update_extension_status("✅ Flask server is running")
                    return True
            except:
                pass
            time.sleep(0.5)
        self.update_extension_status("⚠️ Flask server not responding, but continuing...")
        return False

    def load_default_config(self):
        self.update_extension_status("🚀 Web Scraper Application Started")
        self.update_extension_status("📡 Flask server starting on http://127.0.0.1:5584")
        self.update_extension_status("✅ Ready to create extensions")

    def create_extension(self):
        try:
            self.update_extension_status("🛠️ Creating Chrome extension...")
            config = self.get_extension_config()
            extension_path = self.extension_manager.create_extension(config)
            
            zip_path = self.extension_manager.create_extension_zip()
            
            self.update_extension_status(f"✅ Extension created successfully!")
            self.update_extension_status(f"📁 Extension location: {extension_path}")
            self.update_extension_status(f"📦 ZIP file created: {zip_path}")
            
            self.open_folder_btn.setEnabled(True)
            
            QMessageBox.information(self, "Extension Created", 
                f"Chrome extension created successfully!\n\n"
                f"Extension folder: {extension_path}\n\n"
                "To install the extension:\n"
                "1. Open Chrome and go to: chrome://extensions/\n"
                "2. Enable 'Developer mode' (toggle in top-right)\n"
                "3. Click 'Load unpacked' button\n"
                "4. Select the extension folder\n"
                "5. The extension will appear in your toolbar")
            
        except Exception as e:
            self.update_extension_status(f"❌ Failed to create extension: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create extension:\n{str(e)}")

    def open_extension_folder(self):
        try:
            extension_path = self.extension_manager.extension_dir
            if os.path.exists(extension_path):
                if sys.platform == "win32":
                    os.startfile(extension_path)
                elif sys.platform == "darwin":
                    os.system(f'open "{extension_path}"')
                else:
                    os.system(f'xdg-open "{extension_path}"')
                self.update_extension_status("📁 Opened extension folder in file explorer")
            else:
                QMessageBox.warning(self, "Warning", "Extension folder not found. Please create the extension first.")
        except Exception as e:
            self.update_extension_status(f"❌ Failed to open folder: {str(e)}")

    def start_selenium_browser(self):
        """Start the browser and wait for user to manually start scraping"""
        url = self.selenium_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            config = self.get_selenium_config()
            
            self.selenium_thread = SeleniumScrapingThread(url, config)
            self.selenium_thread.progress.connect(self.selenium_progress.setValue)
            self.selenium_thread.message.connect(self.update_selenium_status)
            self.selenium_thread.data_received.connect(self.handle_received_data)
            self.selenium_thread.finished.connect(self.selenium_finished)
            self.selenium_thread.error.connect(self.selenium_error)
            self.selenium_thread.browser_ready.connect(self.browser_ready)
            
            self.start_browser_btn.setEnabled(False)
            self.stop_selenium_btn.setEnabled(True)
            self.selenium_progress.setValue(0)
            self.selenium_status.clear()
            
            self.selenium_thread.start()
            
        except Exception as e:
            self.update_selenium_status(f"❌ Failed to start Selenium: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start Selenium scraping:\n{str(e)}")

    def start_scraping_now(self):
        """Called when user clicks Start Scraping button"""
        if self.selenium_thread:
            self.start_scraping_btn.setEnabled(False)
            self.selenium_thread.start_scraping_now()

    def browser_ready(self):
        """Called when browser is ready and waiting for user to start scraping"""
        self.start_scraping_btn.setEnabled(True)
        self.start_scraping_btn.setVisible(True)
        self.update_selenium_status("✅ Browser is ready! Click 'Start Scraping Now' when you're ready to scrape the current page.")

    def selenium_finished(self):
        """Called when selenium scraping is complete"""
        self.start_browser_btn.setEnabled(True)
        self.stop_selenium_btn.setEnabled(False)
        self.start_scraping_btn.setEnabled(False)
        self.start_scraping_btn.setVisible(False)
        self.update_selenium_status("✅ Selenium scraping completed!")

    def selenium_error(self, error_message):
        """Handle Selenium errors"""
        self.update_selenium_status(f"❌ Selenium error: {error_message}")
        self.start_browser_btn.setEnabled(True)
        self.stop_selenium_btn.setEnabled(False)
        self.start_scraping_btn.setEnabled(False)
        self.start_scraping_btn.setVisible(False)

    def stop_selenium_scraping(self):
        """Stop selenium scraping"""
        if self.selenium_thread and self.selenium_thread.isRunning():
            self.selenium_thread.stop_scraping()
            self.selenium_thread.terminate()
            self.selenium_thread.wait()
            self.update_selenium_status("🛑 Selenium scraping stopped")
            self.start_browser_btn.setEnabled(True)
            self.stop_selenium_btn.setEnabled(False)
            self.start_scraping_btn.setEnabled(False)
            self.start_scraping_btn.setVisible(False)

    def get_extension_config(self):
        custom_selectors = [s.strip() for s in self.custom_selectors_input.text().split(',') if s.strip()]
        text_selectors = [s.strip() for s in self.text_selectors_input.text().split(',') if s.strip()]
        
        return {
            'text_selectors': text_selectors,
            'image_selectors': ['img'],
            'link_selectors': ['a'],
            'table_selectors': ['table'],
            'custom_selectors': custom_selectors,
            'extract_text': self.extract_text_cb.isChecked(),
            'extract_images': self.extract_images_cb.isChecked(),
            'extract_links': self.extract_links_cb.isChecked(),
            'extract_tables': self.extract_tables_cb.isChecked(),
            'extract_custom': True
        }

    def get_selenium_config(self):
        config = self.get_extension_config()
        config.update({
            'headless': self.selenium_headless_cb.isChecked(),
            'is_dynamic': self.selenium_dynamic_cb.isChecked(),
            'scroll_delay': self.selenium_scroll_delay.value(),
            'max_scroll_attempts': self.selenium_max_scroll.value(),
            'dynamic_interval': self.dynamic_interval.value(),
            'custom_tag': self.custom_tag_input.text().strip(),
            'extract_custom_tag': self.extract_custom_tag_cb.isChecked(),
            'profile_strategy': 'temp'
        })
        return config

    def handle_received_data(self, data):
        """Handle new data received from scraping"""
        self.data_manager.add_data(data)
        
        source = data.get('metadata', {}).get('source', 'unknown')
        if source == 'extension':
            self.update_extension_status(f"✅ Data received: {len(data.get('texts', []))} texts")
        else:
            self.update_selenium_status(f"✅ Data received: {len(data.get('texts', []))} texts")

    def update_extension_status(self, message):
        timestamp = time.strftime('%H:%M:%S')
        self.extension_status.append(f"[{timestamp}] {message}")
        self.extension_status.verticalScrollBar().setValue(
            self.extension_status.verticalScrollBar().maximum()
        )

    def update_selenium_status(self, message):
        timestamp = time.strftime('%H:%M:%S')
        self.selenium_status.append(f"[{timestamp}] {message}")
        self.selenium_status.verticalScrollBar().setValue(
            self.selenium_status.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        """Save data when application closes"""
        if hasattr(self, 'data_manager'):
            self.data_manager.save_data_to_file()
        
        if self.flask_server.is_running:
            self.flask_server.terminate()
            self.flask_server.wait()
        
        if self.selenium_thread and self.selenium_thread.isRunning():
            self.selenium_thread.stop_scraping()
            self.selenium_thread.terminate()
            self.selenium_thread.wait()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())