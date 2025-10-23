import os
import json
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, 
    QTextEdit, QLabel, QListWidget, QListWidgetItem, QLineEdit,
    QSpinBox, QFileDialog, QMessageBox, QProgressBar, QSplitter,
    QTabWidget, QInputDialog, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from browser_recorder import BrowserRecorder

class RobotProcessUI(QWidget):
    data_received = pyqtSignal(dict)
    
    def __init__(self, robot_manager):
        super().__init__()
        self.robot_manager = robot_manager
        self.executor = None
        self.browser_recorder = BrowserRecorder()
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🤖 Smart Robot Process")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "🎯 EASY MODE: Just enter a URL and start recording. Use the browser normally - we'll automatically record your steps!\n"
            "No complex setup needed. Click, type, navigate - we remember everything."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin: 10px; padding: 10px; background-color: #e8f5e8; border-radius: 5px; color: #2d5016;")
        layout.addWidget(desc)
        
        # Simple Start Section
        start_group = QGroupBox("🚀 Start Recording")
        start_layout = QVBoxLayout(start_group)
        
        # URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Website URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setText("https://www.example.com")
        url_layout.addWidget(self.url_input)
        
        self.start_record_btn = QPushButton("🔴 Start Smart Recording")
        self.start_record_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 12px; font-size: 12pt; }")
        url_layout.addWidget(self.start_record_btn)
        
        start_layout.addLayout(url_layout)
        
        # Quick actions
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Quick Actions:"))
        
        self.add_wait_btn = QPushButton("⏰ Add Wait")
        self.add_scroll_btn = QPushButton("📜 Add Scroll")
        self.add_extract_btn = QPushButton("📄 Extract Data Here")
        
        quick_layout.addWidget(self.add_wait_btn)
        quick_layout.addWidget(self.add_scroll_btn)
        quick_layout.addWidget(self.add_extract_btn)
        quick_layout.addStretch()
        
        start_layout.addLayout(quick_layout)
        layout.addWidget(start_group)
        
        # Recording Controls
        control_group = QGroupBox("🎮 Recording Controls")
        control_layout = QHBoxLayout(control_group)
        
        self.stop_record_btn = QPushButton("⏹️ Stop Recording")
        self.stop_record_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; font-weight: bold; padding: 10px; }")
        self.stop_record_btn.setEnabled(False)
        
        self.save_btn = QPushButton("💾 Save Steps")
        self.save_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 10px; }")
        
        self.load_btn = QPushButton("📂 Load Steps")
        self.load_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; padding: 10px; }")
        
        control_layout.addWidget(self.stop_record_btn)
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.load_btn)
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
        # Splitter for actions and status
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left - Recorded Steps
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        steps_label = QLabel("📋 Your Recorded Steps (Auto-saved):")
        steps_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        left_layout.addWidget(steps_label)
        
        self.actions_list = QListWidget()
        self.actions_list.setAlternatingRowColors(True)
        left_layout.addWidget(self.actions_list)
        
        splitter.addWidget(left_widget)
        
        # Right - Status and Execution
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Execution Section
        exec_group = QGroupBox("🚀 Run Your Automation")
        exec_layout = QVBoxLayout(exec_group)
        
        exec_desc = QLabel("Click below to run all your recorded steps automatically:")
        exec_desc.setWordWrap(True)
        exec_layout.addWidget(exec_desc)
        
        self.execute_btn = QPushButton("🤖 Run Automation")
        self.execute_btn.setStyleSheet("QPushButton { background-color: #ff6b00; color: white; font-weight: bold; padding: 15px; font-size: 12pt; }")
        exec_layout.addWidget(self.execute_btn)
        
        self.stop_execute_btn = QPushButton("🛑 Stop")
        self.stop_execute_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 10px; }")
        self.stop_execute_btn.setEnabled(False)
        exec_layout.addWidget(self.stop_execute_btn)
        
        # Progress
        self.rp_progress = QProgressBar()
        self.rp_progress.setStyleSheet("QProgressBar { height: 20px; border-radius: 10px; } QProgressBar::chunk { background-color: #ff6b00; }")
        exec_layout.addWidget(self.rp_progress)
        
        right_layout.addWidget(exec_group)
        
        # Status
        status_group = QGroupBox("📊 What's Happening")
        status_layout = QVBoxLayout(status_group)
        
        self.rp_status = QTextEdit()
        self.rp_status.setMaximumHeight(200)
        self.rp_status.setReadOnly(True)
        self.rp_status.setStyleSheet("font-family: 'Courier New'; font-size: 10pt; background-color: #f8f9fa;")
        status_layout.addWidget(self.rp_status)
        
        right_layout.addWidget(status_group)
        splitter.addWidget(right_widget)
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
        
    def connect_signals(self):
        # Browser recorder signals
        self.browser_recorder.action_recorded.connect(self.on_action_recorded)
        self.browser_recorder.status_updated.connect(self.update_status)
        
        # Button connections
        self.start_record_btn.clicked.connect(self.start_smart_recording)
        self.stop_record_btn.clicked.connect(self.stop_smart_recording)
        self.save_btn.clicked.connect(self.save_workflow)
        self.load_btn.clicked.connect(self.load_workflow)
        self.execute_btn.clicked.connect(self.execute_workflow)
        self.stop_execute_btn.clicked.connect(self.stop_execution)
        
        # Quick actions
        self.add_wait_btn.clicked.connect(self.add_quick_wait)
        self.add_scroll_btn.clicked.connect(self.add_quick_scroll)
        self.add_extract_btn.clicked.connect(self.add_quick_extract)
        
    def start_smart_recording(self):
        """Start the smart recording with just a URL"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Oops", "Please enter a website URL to start recording")
            return
            
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        try:
            self.browser_recorder.start_recording(url)
            self.start_record_btn.setEnabled(False)
            self.stop_record_btn.setEnabled(True)
            self.update_status("🎬 Recording started! A browser window opened - just use it normally!")
            self.update_status("💡 TIP: Click buttons, type in fields, navigate to other pages - we'll record everything!")
            
        except Exception as e:
            self.update_status(f"❌ Failed to start recording: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not start recording:\n{str(e)}")
            
    def stop_smart_recording(self):
        """Stop the smart recording"""
        self.browser_recorder.stop_recording()
        self.start_record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        self.update_status("✅ Recording stopped! Your steps are saved below.")
        
    def on_action_recorded(self, action):
        """When a new action is recorded automatically"""
        # Add to robot manager
        if action['type'] == 'navigate':
            self.robot_manager.record_navigation(action['target'], action['description'])
        elif action['type'] == 'click':
            self.robot_manager.record_click(action['target'], action['description'])
        elif action['type'] == 'input':
            self.robot_manager.record_input(action['target'], action['value'], action['description'])
            
        self.update_actions_list()
        
    def add_quick_wait(self):
        """Add a wait step manually"""
        seconds, ok = QInputDialog.getInt(self, "Add Wait", "Wait for how many seconds?", 3, 1, 30, 1)
        if ok:
            self.robot_manager.record_wait(seconds, f"Wait for {seconds} seconds")
            self.update_actions_list()
            self.update_status(f"⏰ Added wait: {seconds} seconds")
            
    def add_quick_scroll(self):
        """Add a scroll step"""
        self.robot_manager.record_scroll('down', "Scroll down the page")
        self.update_actions_list()
        self.update_status("📜 Added scroll action")
        
    def add_quick_extract(self):
        """Add data extraction step"""
        selector, ok = QInputDialog.getText(self, "Extract Data", "What should we extract? (CSS selector):", text=".content, p, h1")
        if ok and selector:
            self.robot_manager.record_text_extraction(selector, f"Extract data from {selector}")
            self.update_actions_list()
            self.update_status(f"📄 Added data extraction: {selector}")
            
    def save_workflow(self):
        """Save the recorded workflow"""
        if not self.robot_manager.get_recorded_actions():
            QMessageBox.warning(self, "No Steps", "No steps recorded yet! Start recording first.")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Your Automation", "my_automation.json", "JSON Files (*.json)"
        )
        if filename:
            self.robot_manager.save_workflow(filename)
            self.update_status(f"💾 Automation saved: {filename}")
            QMessageBox.information(self, "Saved!", f"Your automation steps have been saved!\n\nYou can load them anytime to run again.")
            
    def load_workflow(self):
        """Load a saved workflow"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Automation", "", "JSON Files (*.json)"
        )
        if filename:
            self.robot_manager.load_workflow(filename)
            self.update_actions_list()
            self.update_status(f"📂 Loaded automation: {filename}")
            
    def execute_workflow(self):
        """Execute the recorded workflow"""
        if not self.robot_manager.get_recorded_actions():
            QMessageBox.warning(self, "No Steps", "No steps to execute! Record some steps first.")
            return
            
        self.executor = self.robot_manager.execute_workflow()
        if self.executor:
            self.executor.progress.connect(self.rp_progress.setValue)
            self.executor.message.connect(self.update_status)
            self.executor.data_received.connect(self.data_received.emit)
            self.executor.execution_finished.connect(self.execution_finished)
            self.executor.step_started.connect(self.step_started)
            
            self.execute_btn.setEnabled(False)
            self.stop_execute_btn.setEnabled(True)
            self.rp_progress.setValue(0)
            
            self.executor.start()
            
    def stop_execution(self):
        if self.executor and self.executor.isRunning():
            self.executor.stop_execution()
            self.execution_finished()
            
    def execution_finished(self):
        self.execute_btn.setEnabled(True)
        self.stop_execute_btn.setEnabled(False)
        
    def step_started(self, step_number, description):
        self.update_status(f"🔧 Executing step {step_number}: {description}")
        
    def update_actions_list(self):
        self.actions_list.clear()
        actions = self.robot_manager.get_recorded_actions()
        for action in actions:
            item_text = f"Step {action['step']}: {action['description']}"
            item = QListWidgetItem(item_text)
            
            # Color code by action type
            color_map = {
                'navigate': '#e3f2fd',
                'click': '#fff3e0', 
                'input': '#e8f5e8',
                'extract_text': '#f3e5f5',
                'wait': '#f5f5f5',
                'scroll': '#fff8e1'
            }
            
            bg_color = color_map.get(action['type'], '#ffffff')
            item.setBackground(Qt.transparent)
            item.setStyleSheet(f"background-color: {bg_color}; padding: 5px; border-bottom: 1px solid #ddd;")
                
            self.actions_list.addItem(item)
            
    def update_status(self, message):
        timestamp = time.strftime('%H:%M:%S')
        self.rp_status.append(f"[{timestamp}] {message}")
        self.rp_status.verticalScrollBar().setValue(
            self.rp_status.verticalScrollBar().maximum()
        )