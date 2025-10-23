import time
import json
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import pickle
import os

class ActionRecorder:
    def __init__(self):
        self.actions = []
        self.is_recording = False
        self.current_step = 0
        
    def start_recording(self):
        self.actions = []
        self.is_recording = True
        self.current_step = 0
        logging.info("Action recording started")
        
    def stop_recording(self):
        self.is_recording = False
        logging.info(f"Action recording stopped. {len(self.actions)} actions recorded")
        
    def record_action(self, action_type, selector, value=None, description=""):
        if not self.is_recording:
            return
            
        action = {
            'step': self.current_step + 1,
            'type': action_type,
            'selector': selector,
            'value': value,
            'description': description,
            'timestamp': time.time()
        }
        self.actions.append(action)
        self.current_step += 1
        logging.info(f"Recorded action: {action_type} on {selector}")
        
    def get_actions(self):
        return self.actions.copy()
    
    def save_workflow(self, filename):
        workflow = {
            'actions': self.actions,
            'metadata': {
                'created_at': time.time(),
                'total_steps': len(self.actions),
                'version': '1.0'
            }
        }
        with open(filename, 'w') as f:
            json.dump(workflow, f, indent=2)
        logging.info(f"Workflow saved to {filename}")
        
    def load_workflow(self, filename):
        with open(filename, 'r') as f:
            workflow = json.load(f)
        self.actions = workflow['actions']
        self.current_step = len(self.actions)
        logging.info(f"Workflow loaded from {filename}")
        return workflow

class RobotProcessExecutor(QThread):
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    data_received = pyqtSignal(dict)
    execution_finished = pyqtSignal()
    step_started = pyqtSignal(int, str)
    
    def __init__(self, workflow_file=None, actions=None):
        super().__init__()
        self.workflow_file = workflow_file
        self.actions = actions or []
        self.driver = None
        self.is_running = False
        self.current_step = 0
        self.extracted_data = []
        
    def set_workflow(self, workflow_file):
        self.workflow_file = workflow_file
        
    def set_actions(self, actions):
        self.actions = actions
        
    def stop_execution(self):
        self.is_running = False
        if self.driver:
            self.driver.quit()
            
    def run(self):
        self.is_running = True
        
        if not self.actions and self.workflow_file:
            try:
                with open(self.workflow_file, 'r') as f:
                    workflow = json.load(f)
                    self.actions = workflow['actions']
            except Exception as e:
                self.message.emit(f"❌ Failed to load workflow: {str(e)}")
                return
                
        if not self.actions:
            self.message.emit("❌ No actions to execute")
            return
            
        try:
            self.message.emit("🤖 Starting Robot Process execution...")
            
            # Initialize browser
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            total_steps = len(self.actions)
            
            for step_idx, action in enumerate(self.actions):
                if not self.is_running:
                    break
                    
                self.current_step = step_idx + 1
                progress = int((step_idx / total_steps) * 100)
                self.progress.emit(progress)
                
                self.step_started.emit(action['step'], action['description'])
                self.message.emit(f"🔧 Step {action['step']}: {action['description']}")
                
                success = self.execute_action(action)
                if not success:
                    self.message.emit(f"❌ Failed at step {action['step']}")
                    break
                    
                time.sleep(1)  # Brief pause between actions
                
            if self.is_running:
                self.progress.emit(100)
                self.message.emit("✅ Robot Process execution completed!")
                
                # Emit collected data
                if self.extracted_data:
                    final_data = {
                        'texts': self.extracted_data,
                        'metadata': {
                            'source': 'robot_process',
                            'timestamp': time.time(),
                            'steps_executed': self.current_step,
                            'total_data_points': len(self.extracted_data)
                        }
                    }
                    self.data_received.emit(final_data)
                    
        except Exception as e:
            self.message.emit(f"❌ Robot Process error: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
            self.execution_finished.emit()
            
    def execute_action(self, action):
        try:
            action_type = action['type']
            selector = action['selector']
            value = action.get('value')
            
            if action_type == 'navigate':
                self.driver.get(selector)  # selector contains URL here
                
            elif action_type == 'click':
                element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                element.click()
                
            elif action_type == 'input':
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                element.clear()
                element.send_keys(value)
                
            elif action_type == 'wait':
                time.sleep(int(value))
                
            elif action_type == 'extract_text':
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text:
                        self.extracted_data.append({
                            'text': text,
                            'selector': selector,
                            'step': action['step'],
                            'timestamp': time.time()
                        })
                self.message.emit(f"📊 Extracted {len(elements)} text elements")
                
            elif action_type == 'extract_attribute':
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                attribute = value  # value contains attribute name here
                for element in elements:
                    attr_value = element.get_attribute(attribute)
                    if attr_value:
                        self.extracted_data.append({
                            'text': attr_value,
                            'selector': f"{selector}[{attribute}]",
                            'step': action['step'],
                            'timestamp': time.time()
                        })
                self.message.emit(f"📊 Extracted {len(elements)} attribute values")
                
            elif action_type == 'scroll':
                if value == 'down':
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                elif value == 'up':
                    self.driver.execute_script("window.scrollTo(0, 0);")
                else:
                    self.driver.execute_script(f"window.scrollTo(0, {value});")
                    
            return True
            
        except Exception as e:
            self.message.emit(f"❌ Error executing {action_type}: {str(e)}")
            return False

class RobotProcessManager(QObject):
    def __init__(self):
        super().__init__()
        self.recorder = ActionRecorder()
        self.executor = None
        self.current_workflow_file = None
        
    def start_recording(self):
        self.recorder.start_recording()
        
    def stop_recording(self):
        self.recorder.stop_recording()
        
    def record_navigation(self, url, description="Navigate to page"):
        self.recorder.record_action('navigate', url, None, description)
        
    def record_click(self, selector, description="Click element"):
        self.recorder.record_action('click', selector, None, description)
        
    def record_input(self, selector, value, description="Input text"):
        self.recorder.record_action('input', selector, value, description)
        
    def record_text_extraction(self, selector, description="Extract text"):
        self.recorder.record_action('extract_text', selector, None, description)
        
    def record_attribute_extraction(self, selector, attribute, description="Extract attribute"):
        self.recorder.record_action('extract_attribute', selector, attribute, description)
        
    def record_wait(self, seconds, description="Wait"):
        self.recorder.record_action('wait', 'wait', seconds, description)
        
    def record_scroll(self, direction='down', description="Scroll page"):
        self.recorder.record_action('scroll', 'scroll', direction, description)
        
    def save_workflow(self, filename):
        self.recorder.save_workflow(filename)
        self.current_workflow_file = filename
        
    def load_workflow(self, filename):
        self.recorder.load_workflow(filename)
        self.current_workflow_file = filename
        
    def execute_workflow(self):
        if not self.recorder.actions and not self.current_workflow_file:
            return False
            
        self.executor = RobotProcessExecutor(
            workflow_file=self.current_workflow_file,
            actions=self.recorder.actions
        )
        return self.executor
    
    def get_recorded_actions(self):
        return self.recorder.get_actions()
    
    def clear_actions(self):
        self.recorder.actions = []
        self.recorder.current_step = 0