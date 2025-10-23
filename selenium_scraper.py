# File: selenium_scraper.py
import time
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import requests
import json
import os
import platform
import tempfile
import shutil

class SeleniumScrapingThread(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    data_received = pyqtSignal(dict)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    browser_ready = pyqtSignal()

    def __init__(self, url, config):
        super().__init__()
        self.url = url
        self.config = config
        self.is_running = True
        self.is_browser_ready = False
        self.waiting_for_user = False
        self.previous_content_hash = None
        self.driver = None
        self.temp_profile_dir = None
        self.scrape_count = 0

    def _create_temp_profile(self):
        """Create a temporary Chrome profile directory"""
        try:
            self.temp_profile_dir = tempfile.mkdtemp(prefix="chrome_profile_")
            self.message.emit(f"📁 Created temporary profile: {self.temp_profile_dir}")
            return self.temp_profile_dir
        except Exception as e:
            self.message.emit(f"⚠️ Failed to create temporary profile: {str(e)}")
            return None

    def _copy_chrome_profile(self, source_profile, temp_profile):
        """Copy Chrome profile data to temporary directory"""
        try:
            if os.path.exists(source_profile):
                items_to_copy = ['Login Data', 'Cookies', 'Local State', 'Preferences']
                for item in items_to_copy:
                    source_path = os.path.join(source_profile, item)
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, temp_profile)
                self.message.emit("✅ Copied Chrome profile data")
                return True
            return False
        except Exception as e:
            self.message.emit(f"⚠️ Profile copy failed: {str(e)}")
            return False

    def _initialize_driver(self):
        """Initialize Chrome WebDriver with flexible profile options"""
        try:
            self.message.emit("📥 Setting up ChromeDriver...")
            chrome_options = Options()
            
            if self.config.get('headless', False):
                chrome_options.add_argument("--headless")
                self.message.emit("🖥️ Running in headless mode")
            else:
                chrome_options.add_argument("--start-maximized")
                self.message.emit("🖥️ Opening browser window...")

            # Essential options for better compatibility
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Use temporary profile to avoid conflicts
            temp_profile = self._create_temp_profile()
            if temp_profile:
                chrome_options.add_argument(f"--user-data-dir={temp_profile}")
                self.message.emit("🔧 Using temporary Chrome profile")
                
                # Try to copy existing profile data if available
                chrome_user_data = self._get_chrome_user_data_path()
                default_profile = os.path.join(chrome_user_data, "Default")
                self._copy_chrome_profile(default_profile, temp_profile)

            # Try multiple approaches to initialize driver
            driver_initialized = False
            initialization_errors = []

            # Approach 1: Use webdriver_manager with Service
            try:
                driver_path = ChromeDriverManager().install()
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                driver_initialized = True
                self.message.emit("✅ Driver initialized with webdriver_manager")
            except Exception as e:
                initialization_errors.append(f"Approach 1 (webdriver_manager): {str(e)}")

            # Approach 2: Try system ChromeDriver
            if not driver_initialized:
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                    driver_initialized = True
                    self.message.emit("✅ Driver initialized with system ChromeDriver")
                except Exception as e:
                    initialization_errors.append(f"Approach 2 (system): {str(e)}")

            if not driver_initialized:
                error_msg = "All driver initialization methods failed:\n" + "\n".join(initialization_errors)
                raise Exception(error_msg)

            # Set page load timeout
            self.driver.set_page_load_timeout(30)
            
            self.progress.emit(20)
            self.message.emit("🎉 ChromeDriver initialized successfully!")
            
        except Exception as e:
            error_msg = f"❌ Failed to initialize WebDriver: {str(e)}"
            self.message.emit(error_msg)
            if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
                try:
                    shutil.rmtree(self.temp_profile_dir)
                except:
                    pass
            self.error.emit(error_msg)
            self.is_running = False
            self.driver = None

    def _get_chrome_user_data_path(self):
        """Get Chrome user data path based on operating system"""
        system = platform.system()
        
        if system == "Windows":
            return os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data')
        elif system == "Darwin":  # macOS
            return os.path.expanduser('~/Library/Application Support/Google/Chrome')
        else:  # Linux
            return os.path.expanduser('~/.config/google-chrome')

    def wait_for_user_start(self):
        """Wait for user to click Start Scraping button"""
        if not self.driver or self.config.get('headless', False):
            return True
            
        self.message.emit("🎯 BROWSER READY!")
        self.message.emit("=" * 50)
        self.message.emit("Please perform the following steps:")
        self.message.emit("1. Log in to the website if needed")
        self.message.emit("2. Navigate to the exact page you want to scrape")
        self.message.emit("3. Wait for the page to fully load")
        self.message.emit("4. Click 'START SCRAPING' button when ready")
        self.message.emit("=" * 50)
        
        # Emit signal that browser is ready and waiting for user
        self.is_browser_ready = True
        self.waiting_for_user = True
        self.browser_ready.emit()
        
        # Wait for user to click start (controlled by main thread)
        while self.waiting_for_user and self.is_running:
            time.sleep(0.5)
            
        return self.is_running

    def start_scraping_now(self):
        """Called when user clicks the Start Scraping button"""
        self.waiting_for_user = False
        self.message.emit("🚀 Starting scraping now...")

    def scroll_to_bottom(self):
        """Handle infinite scroll pages"""
        if not self.driver:
            return
            
        self.message.emit("📜 Scrolling to load dynamic content...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = self.config.get('max_scroll_attempts', 5)
        scroll_delay = self.config.get('scroll_delay', 2)
        
        while self.is_running and scroll_attempts < max_scroll_attempts:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_delay)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1
            
        self.message.emit(f"✅ Finished scrolling after {scroll_attempts} attempts")

    def extract_specific_elements(self):
        """Extract ONLY from user-specified tags/selectors"""
        if not self.driver:
            return {}
        
        current_url = self.driver.current_url
        current_title = self.driver.title
        
        results = {
            'texts': [],
            'custom_elements': [],
            'metadata': {
                'url': current_url,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'title': current_title,
                'source': 'selenium',
                'scrape_count': self.scrape_count
            }
        }

        try:
            # Extract from custom selectors if specified
            custom_selectors = self.config.get('custom_selectors', [])
            if custom_selectors:
                self.message.emit(f"🎯 Extracting from custom selectors: {', '.join(custom_selectors)}")
                for selector in custom_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            self.message.emit(f"✅ Found {len(elements)} elements for: {selector}")
                            for i, element in enumerate(elements):
                                try:
                                    text = element.text.strip()
                                    if text:
                                        results['custom_elements'].append({
                                            'selector': selector,
                                            'index': i,
                                            'text': text[:500],
                                            'full_text': text,
                                            'html': element.get_attribute('outerHTML')[:1000]
                                        })
                                except Exception:
                                    continue
                    except Exception as e:
                        self.message.emit(f"⚠️ Error with selector {selector}: {str(e)}")

            # Extract from custom tag if specified
            custom_tag = self.config.get('custom_tag', '').strip()
            if self.config.get('extract_custom_tag', False) and custom_tag:
                self.message.emit(f"🏷️ Extracting from: {custom_tag}")
                try:
                    if custom_tag.startswith('.'):
                        # CSS class
                        class_name = custom_tag[1:]
                        elements = self.driver.find_elements(By.CSS_SELECTOR, f'[class*="{class_name}"]')
                    elif custom_tag.startswith('#'):
                        # CSS ID
                        id_name = custom_tag[1:]
                        elements = self.driver.find_elements(By.CSS_SELECTOR, f'[id*="{id_name}"]')
                    else:
                        # HTML tag
                        elements = self.driver.find_elements(By.TAG_NAME, custom_tag)
                    
                    self.message.emit(f"✅ Found {len(elements)} elements for: {custom_tag}")
                    
                    for i, element in enumerate(elements):
                        try:
                            text = element.text.strip()
                            if text:
                                results['custom_elements'].append({
                                    'selector': custom_tag,
                                    'index': i,
                                    'text': text[:500],
                                    'full_text': text,
                                    'html': element.get_attribute('outerHTML')[:1000]
                                })
                        except Exception:
                            continue
                except Exception as e:
                    self.message.emit(f"⚠️ Error with {custom_tag}: {str(e)}")

            # If no specific selectors, extract basic text
            if not custom_selectors and not (self.config.get('extract_custom_tag', False) and custom_tag):
                self.message.emit("📝 Extracting basic text elements")
                basic_selectors = ['p', 'h1', 'h2', 'h3', 'div']
                for selector in basic_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            text = element.text.strip()
                            if text and len(text) > 3:
                                results['texts'].append({
                                    'selector': selector,
                                    'text': text[:500],
                                    'full_text': text
                                })
                    except Exception as e:
                        continue

            self.scrape_count += 1
            total_elements = len(results['texts']) + len(results['custom_elements'])
            self.message.emit(f"📊 Scrape #{self.scrape_count}: {total_elements} elements found")

        except Exception as e:
            self.message.emit(f"⚠️ Error during extraction: {str(e)}")

        return results

    def send_to_backend(self, data):
        """Send scraped data to the Flask backend"""
        try:
            response = requests.post('http://127.0.0.1:5584/store', json=data, timeout=10)
            if response.status_code == 200:
                self.message.emit("✅ Data sent to backend successfully")
            else:
                self.message.emit(f"⚠️ Failed to send data to backend: {response.status_code}")
        except Exception as e:
            self.message.emit(f"⚠️ Error sending data to backend: {str(e)}")

    def run(self):
        try:
            # Initialize driver at the start of run
            self._initialize_driver()
            
            if not self.driver:
                self.error.emit("❌ No WebDriver available, scraping aborted")
                return

            self.progress.emit(30)

            # If not in headless mode, wait for user to manually start scraping
            if not self.config.get('headless', False):
                if not self.wait_for_user_start():
                    self.message.emit("🛑 User cancelled scraping")
                    self.finished.emit()
                    return
            else:
                # In headless mode, navigate to the URL automatically
                if self.url:
                    self.message.emit(f"🌐 Navigating to: {self.url}")
                    self.driver.get(self.url)
                    time.sleep(5)

            self.progress.emit(50)

            # Check if continuous scraping is enabled
            is_dynamic = self.config.get('is_dynamic', False)
            
            if is_dynamic:
                # CONTINUOUS SCRAPING MODE
                self.message.emit("🔄 Starting CONTINUOUS scraping mode...")
                self.message.emit("📊 Browser will remain open and keep scraping until you click STOP")
                
                interval = self.config.get('dynamic_interval', 5)
                max_scrapes = 1000  # Large number for continuous operation
                
                while self.is_running and self.scrape_count < max_scrapes:
                    # Scroll if enabled
                    if self.config.get('handle_dynamic', True):
                        self.scroll_to_bottom()
                    
                    # Extract data
                    results = self.extract_specific_elements()
                    
                    # Send data if we found anything
                    if results.get('texts') or results.get('custom_elements'):
                        self.send_to_backend(results)
                        self.data_received.emit(results)
                    
                    # Update progress
                    progress = 50 + min(self.scrape_count * 2, 40)
                    self.progress.emit(progress)
                    
                    # Wait for next scrape
                    if self.is_running:
                        self.message.emit(f"⏳ Next scrape in {interval} seconds... (Scrapes: {self.scrape_count})")
                        for i in range(interval):
                            if not self.is_running:
                                break
                            time.sleep(1)
                
                if self.scrape_count >= max_scrapes:
                    self.message.emit("🏁 Reached maximum scrape limit")
                    
            else:
                # SINGLE SCRAPING MODE
                self.message.emit("📊 Performing single scrape...")
                
                # Scroll if enabled
                if self.config.get('handle_dynamic', True):
                    self.scroll_to_bottom()
                
                # Extract data
                results = self.extract_specific_elements()
                
                # Send data
                if results.get('texts') or results.get('custom_elements'):
                    self.send_to_backend(results)
                    self.data_received.emit(results)
                
                self.progress.emit(90)

            self.progress.emit(100)
            
            if is_dynamic:
                self.message.emit("🔄 Continuous scraping stopped by user")
            else:
                self.message.emit("✅ Single scraping completed successfully!")
                
            self.finished.emit()

        except Exception as e:
            error_msg = f"❌ Selenium scraping failed: {str(e)}"
            self.message.emit(error_msg)
            self.error.emit(error_msg)
        finally:
            # Only close browser if not in dynamic mode OR if explicitly stopped
            if not self.config.get('is_dynamic', False) or not self.is_running:
                self.stop_scraping()

    def stop_scraping(self):
        """Stop scraping and clean up WebDriver"""
        self.is_running = False
        self.waiting_for_user = False
        
        if self.driver:
            try:
                self.driver.quit()
                self.message.emit("🛑 WebDriver closed")
            except Exception as e:
                self.message.emit(f"⚠️ Error closing WebDriver: {str(e)}")
            finally:
                self.driver = None
        
        # Clean up temporary profile
        if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
            try:
                shutil.rmtree(self.temp_profile_dir)
                self.message.emit("🧹 Temporary profile cleaned up")
            except Exception as e:
                self.message.emit(f"⚠️ Error cleaning temp profile: {str(e)}")