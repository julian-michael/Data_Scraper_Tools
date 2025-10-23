import json
import os
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem,
    QTextEdit, QComboBox, QLabel, QSplitter, QDialog, QFormLayout, QDialogButtonBox,
    QFileDialog, QMessageBox, QTabWidget, QCheckBox
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class DataCleaningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Cleaning Options")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.remove_empty_cb = QCheckBox("Remove empty records")
        self.remove_empty_cb.setChecked(True)
        layout.addRow(self.remove_empty_cb)
        
        self.remove_duplicates_cb = QCheckBox("Remove duplicate texts")
        self.remove_duplicates_cb.setChecked(True)
        layout.addRow(self.remove_duplicates_cb)
        
        self.trim_whitespace_cb = QCheckBox("Trim whitespace from text")
        self.trim_whitespace_cb.setChecked(True)
        layout.addRow(self.trim_whitespace_cb)
        
        self.remove_short_texts_cb = QCheckBox("Remove very short texts (<10 chars)")
        self.remove_short_texts_cb.setChecked(False)
        layout.addRow(self.remove_short_texts_cb)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_cleaning_options(self):
        return {
            'remove_empty': self.remove_empty_cb.isChecked(),
            'remove_duplicates': self.remove_duplicates_cb.isChecked(),
            'trim_whitespace': self.trim_whitespace_cb.isChecked(),
            'remove_short_texts': self.remove_short_texts_cb.isChecked()
        }

class DataManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.collected_data = []
        self.data_file = "scraped_data.json"
        self.setup_data_tab()
    
    def setup_data_tab(self):
        """Setup the Data Manager tab interface"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create splitter for better layout
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Data controls and list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Data controls
        control_frame = QGroupBox("Data Management Controls")
        control_layout = QGridLayout(control_frame)
        
        # Row 1
        self.clear_data_btn = QPushButton("🗑️ Clear All Data")
        self.clear_data_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; padding: 8px; border-radius: 4px; }")
        self.clear_data_btn.clicked.connect(self.clear_data)
        control_layout.addWidget(self.clear_data_btn, 0, 0)
        
        self.refresh_data_btn = QPushButton("🔄 Refresh")
        self.refresh_data_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; padding: 8px; border-radius: 4px; }")
        self.refresh_data_btn.clicked.connect(self.refresh_data_view)
        control_layout.addWidget(self.refresh_data_btn, 0, 1)
        
        # Row 2
        self.export_json_btn = QPushButton("💾 Export JSON")
        self.export_json_btn.setStyleSheet("QPushButton { background-color: #6f42c1; color: white; padding: 8px; border-radius: 4px; }")
        self.export_json_btn.clicked.connect(lambda: self.export_data('json'))
        control_layout.addWidget(self.export_json_btn, 1, 0)
        
        self.export_csv_btn = QPushButton("📊 Export CSV")
        self.export_csv_btn.setStyleSheet("QPushButton { background-color: #20c997; color: white; padding: 8px; border-radius: 4px; }")
        self.export_csv_btn.clicked.connect(lambda: self.export_data('csv'))
        control_layout.addWidget(self.export_csv_btn, 1, 1)
        
        left_layout.addWidget(control_frame)

        # Data records list
        records_frame = QGroupBox("Data Records")
        records_layout = QVBoxLayout(records_frame)
        
        self.records_list = QListWidget()
        self.records_list.itemSelectionChanged.connect(self.on_record_selected)
        records_layout.addWidget(self.records_list)
        
        left_layout.addWidget(records_frame)

        # Data Analysis Controls
        analysis_frame = QGroupBox("Data Analysis & Cleaning")
        analysis_layout = QGridLayout(analysis_frame)
        
        # Analysis type
        analysis_layout.addWidget(QLabel("Analysis:"), 0, 0)
        self.analysis_type = QComboBox()
        self.analysis_type.addItems(["Basic Statistics", "Text Analysis", "Numeric Analysis", "Data Cleaning"])
        analysis_layout.addWidget(self.analysis_type, 0, 1)
        
        # Chart type
        analysis_layout.addWidget(QLabel("Chart:"), 1, 0)
        self.chart_type = QComboBox()
        self.chart_type.addItems(["Bar Chart", "Line Chart", "Pie Chart", "Histogram"])
        analysis_layout.addWidget(self.chart_type, 1, 1)
        
        # Action buttons
        self.analyze_btn = QPushButton("📈 Analyze Data")
        self.analyze_btn.setStyleSheet("QPushButton { background-color: #fd7e14; color: white; padding: 8px; border-radius: 4px; }")
        self.analyze_btn.clicked.connect(self.analyze_data)
        analysis_layout.addWidget(self.analyze_btn, 2, 0)
        
        self.clean_btn = QPushButton("🧹 Clean Data")
        self.clean_btn.setStyleSheet("QPushButton { background-color: #e83e8c; color: white; padding: 8px; border-radius: 4px; }")
        self.clean_btn.clicked.connect(self.clean_data)
        analysis_layout.addWidget(self.clean_btn, 2, 1)
        
        left_layout.addWidget(analysis_frame)
        
        # Right panel - Data display and analysis
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Tab widget for different views
        self.data_tabs = QTabWidget()
        
        # Table View Tab
        self.table_tab = QWidget()
        table_layout = QVBoxLayout(self.table_tab)
        
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.data_table)
        
        # Analysis View Tab
        self.analysis_tab = QWidget()
        analysis_tab_layout = QVBoxLayout(self.analysis_tab)
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setStyleSheet("font-family: 'Courier New'; font-size: 10pt; background-color: #f8f9fa;")
        analysis_tab_layout.addWidget(self.analysis_text)
        
        # Chart View Tab
        self.chart_tab = QWidget()
        chart_layout = QVBoxLayout(self.chart_tab)
        
        self.chart_canvas = FigureCanvas(plt.Figure(figsize=(10, 6)))
        chart_layout.addWidget(self.chart_canvas)
        
        # Add tabs
        self.data_tabs.addTab(self.table_tab, "📋 Table View")
        self.data_tabs.addTab(self.analysis_tab, "📊 Analysis")
        self.data_tabs.addTab(self.chart_tab, "📈 Charts")
        
        right_layout.addWidget(self.data_tabs)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        
        self.tab = tab
    
    def get_tab(self):
        """Return the data manager tab"""
        return self.tab

    def update_records_list(self):
        """Update the records list widget"""
        self.records_list.clear()
        
        for i, record in enumerate(self.collected_data):
            metadata = record.get('metadata', {})
            source = metadata.get('source', 'Unknown')
            url = metadata.get('url', 'No URL')
            timestamp = metadata.get('timestamp', 'No time')
            
            item_text = f"{i+1}. {source} | {timestamp}\n{url[:50]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, i)
            self.records_list.addItem(item)

    def on_record_selected(self):
        """When a record is selected from the list"""
        selected_items = self.records_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        record_index = item.data(Qt.UserRole)
        record = self.collected_data[record_index]
        
        self.display_record_in_table(record)
        self.display_record_analysis(record)

    def display_record_in_table(self, record):
        """Display record data in table format"""
        table_data = []
        
        # Add texts
        for text in record.get('texts', []):
            table_data.append({
                'Type': 'Text',
                'Selector': text.get('selector', ''),
                'Content': text.get('text', ''),
                'Full Content': text.get('full_text', '')[:200] + '...' if len(text.get('full_text', '')) > 200 else text.get('full_text', '')
            })
        
        # Add custom elements
        for custom in record.get('custom_elements', []):
            table_data.append({
                'Type': 'Custom',
                'Selector': custom.get('selector', ''),
                'Content': custom.get('text', ''),
                'Full Content': custom.get('full_text', '')[:200] + '...' if len(custom.get('full_text', '')) > 200 else custom.get('full_text', '')
            })
        
        # Add images
        for img in record.get('images', []):
            table_data.append({
                'Type': 'Image',
                'Selector': img.get('selector', ''),
                'Content': img.get('alt', ''),
                'Full Content': img.get('src', '')
            })
        
        # Add links
        for link in record.get('links', []):
            table_data.append({
                'Type': 'Link',
                'Selector': link.get('selector', ''),
                'Content': link.get('text', ''),
                'Full Content': link.get('href', '')
            })
        
        # Setup table
        self.data_table.setRowCount(len(table_data))
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(['Type', 'Selector', 'Content', 'Full Content'])
        
        # Populate table
        for row, item in enumerate(table_data):
            self.data_table.setItem(row, 0, QTableWidgetItem(item['Type']))
            self.data_table.setItem(row, 1, QTableWidgetItem(item['Selector']))
            self.data_table.setItem(row, 2, QTableWidgetItem(item['Content']))
            self.data_table.setItem(row, 3, QTableWidgetItem(item['Full Content']))

    def display_record_analysis(self, record):
        """Display basic analysis of the record"""
        analysis_text = "=== DATA ANALYSIS ===\n\n"
        
        # Basic statistics
        analysis_text += "📊 BASIC STATISTICS:\n"
        analysis_text += f"• Total Texts: {len(record.get('texts', []))}\n"
        analysis_text += f"• Total Images: {len(record.get('images', []))}\n"
        analysis_text += f"• Total Links: {len(record.get('links', []))}\n"
        analysis_text += f"• Total Custom Elements: {len(record.get('custom_elements', []))}\n"
        analysis_text += f"• Total Tables: {len(record.get('tables', []))}\n\n"
        
        # Text analysis
        all_texts = [text.get('text', '') for text in record.get('texts', [])]
        all_texts.extend([custom.get('text', '') for custom in record.get('custom_elements', [])])
        
        if all_texts:
            text_lengths = [len(text) for text in all_texts if text.strip()]
            if text_lengths:
                analysis_text += "📝 TEXT ANALYSIS:\n"
                analysis_text += f"• Average Text Length: {np.mean(text_lengths):.2f} chars\n"
                analysis_text += f"• Max Text Length: {max(text_lengths)} chars\n"
                analysis_text += f"• Min Text Length: {min(text_lengths)} chars\n"
                analysis_text += f"• Total Characters: {sum(text_lengths)}\n\n"
        
        # Selector analysis
        selectors = {}
        for text in record.get('texts', []):
            selector = text.get('selector', 'unknown')
            selectors[selector] = selectors.get(selector, 0) + 1
        
        if selectors:
            analysis_text += "🎯 SELECTOR DISTRIBUTION:\n"
            for selector, count in selectors.items():
                analysis_text += f"• {selector}: {count} items\n"
        
        self.analysis_text.setPlainText(analysis_text)

    def analyze_data(self):
        """Perform advanced data analysis"""
        if not self.collected_data:
            QMessageBox.warning(self.main_window, "Warning", "No data to analyze")
            return
        
        analysis_type = self.analysis_type.currentText()
        chart_type = self.chart_type.currentText()
        
        try:
            if analysis_type == "Basic Statistics":
                self.show_basic_statistics()
            elif analysis_type == "Text Analysis":
                self.show_text_analysis()
            elif analysis_type == "Numeric Analysis":
                self.show_numeric_analysis()
            elif analysis_type == "Data Cleaning":
                self.show_data_cleaning_report()
            
            # Generate chart
            self.generate_chart(chart_type)
            
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Analysis failed: {str(e)}")

    def show_basic_statistics(self):
        """Show comprehensive statistics"""
        stats_text = "=== COMPREHENSIVE STATISTICS ===\n\n"
        
        total_records = len(self.collected_data)
        stats_text += f"📈 TOTAL RECORDS: {total_records}\n\n"
        
        # Aggregate all data
        all_texts = []
        all_custom = []
        all_images = []
        all_links = []
        
        for record in self.collected_data:
            all_texts.extend(record.get('texts', []))
            all_custom.extend(record.get('custom_elements', []))
            all_images.extend(record.get('images', []))
            all_links.extend(record.get('links', []))
        
        stats_text += "📊 DATA COUNTS:\n"
        stats_text += f"• Texts: {len(all_texts)}\n"
        stats_text += f"• Custom Elements: {len(all_custom)}\n"
        stats_text += f"• Images: {len(all_images)}\n"
        stats_text += f"• Links: {len(all_links)}\n\n"
        
        # Text statistics
        text_contents = [item.get('text', '') for item in all_texts + all_custom if item.get('text', '').strip()]
        if text_contents:
            text_lengths = [len(text) for text in text_contents]
            stats_text += "📝 TEXT STATISTICS:\n"
            stats_text += f"• Mean Length: {np.mean(text_lengths):.2f} chars\n"
            stats_text += f"• Median Length: {np.median(text_lengths):.2f} chars\n"
            stats_text += f"• Std Dev: {np.std(text_lengths):.2f} chars\n"
            stats_text += f"• Total Characters: {sum(text_lengths)}\n\n"
        
        # Source distribution
        sources = {}
        for record in self.collected_data:
            source = record.get('metadata', {}).get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        stats_text += "🔧 SOURCE DISTRIBUTION:\n"
        for source, count in sources.items():
            stats_text += f"• {source}: {count} records\n"
        
        self.analysis_text.setPlainText(stats_text)

    def show_text_analysis(self):
        """Perform text analysis"""
        all_texts = []
        for record in self.collected_data:
            all_texts.extend([text.get('text', '') for text in record.get('texts', [])])
            all_texts.extend([custom.get('text', '') for custom in record.get('custom_elements', [])])
        
        # Filter non-empty texts
        all_texts = [text for text in all_texts if text.strip()]
        
        analysis_text = "=== TEXT ANALYSIS ===\n\n"
        analysis_text += f"Total text items: {len(all_texts)}\n\n"
        
        if all_texts:
            # Word count analysis
            word_counts = [len(text.split()) for text in all_texts]
            analysis_text += "📊 WORD COUNT ANALYSIS:\n"
            analysis_text += f"• Average words: {np.mean(word_counts):.2f}\n"
            analysis_text += f"• Max words: {max(word_counts)}\n"
            analysis_text += f"• Min words: {min(word_counts)}\n\n"
            
            # Character count analysis
            char_counts = [len(text) for text in all_texts]
            analysis_text += "🔤 CHARACTER COUNT ANALYSIS:\n"
            analysis_text += f"• Average chars: {np.mean(char_counts):.2f}\n"
            analysis_text += f"• Max chars: {max(char_counts)}\n"
            analysis_text += f"• Min chars: {min(char_counts)}\n\n"
            
            # Show sample texts by length
            analysis_text += "📝 TEXT LENGTH DISTRIBUTION:\n"
            short_texts = len([t for t in all_texts if len(t) < 50])
            medium_texts = len([t for t in all_texts if 50 <= len(t) < 200])
            long_texts = len([t for t in all_texts if len(t) >= 200])
            
            analysis_text += f"• Short (<50 chars): {short_texts}\n"
            analysis_text += f"• Medium (50-200 chars): {medium_texts}\n"
            analysis_text += f"• Long (≥200 chars): {long_texts}\n"
        
        self.analysis_text.setPlainText(analysis_text)

    def show_numeric_analysis(self):
        """Extract and analyze numeric data"""
        analysis_text = "=== NUMERIC ANALYSIS ===\n\n"
        
        # Extract numbers from text
        all_numbers = []
        for record in self.collected_data:
            for text in record.get('texts', []):
                content = text.get('text', '')
                # Simple number extraction
                numbers = re.findall(r'\d+\.?\d*', content)
                all_numbers.extend([float(num) for num in numbers if self.is_convertible(num)])
    
        if all_numbers:
            analysis_text += f"🔢 Found {len(all_numbers)} numeric values\n\n"
            analysis_text += "📊 DESCRIPTIVE STATISTICS:\n"
            analysis_text += f"• Count: {len(all_numbers)}\n"
            analysis_text += f"• Mean: {np.mean(all_numbers):.2f}\n"
            analysis_text += f"• Median: {np.median(all_numbers):.2f}\n"
            analysis_text += f"• Standard Deviation: {np.std(all_numbers):.2f}\n"
            analysis_text += f"• Min: {min(all_numbers)}\n"
            analysis_text += f"• Max: {max(all_numbers)}\n"
            analysis_text += f"• Sum: {sum(all_numbers):.2f}\n\n"
            
            # Quartiles
            q25, q75 = np.percentile(all_numbers, [25, 75])
            analysis_text += f"• 25th Percentile: {q25:.2f}\n"
            analysis_text += f"• 75th Percentile: {q75:.2f}\n"
        else:
            analysis_text += "No numeric data found in the collected texts.\n"
        
        self.analysis_text.setPlainText(analysis_text)

    def is_convertible(self, text):
        """Check if text can be converted to float"""
        try:
            float(text)
            return True
        except ValueError:
            return False

    def show_data_cleaning_report(self):
        """Show data quality report"""
        report = "=== DATA CLEANING REPORT ===\n\n"
        
        total_records = len(self.collected_data)
        report += f"Total records analyzed: {total_records}\n\n"
        
        # Data quality metrics
        empty_records = 0
        records_with_text = 0
        total_text_items = 0
        empty_text_items = 0
        
        for record in self.collected_data:
            texts = record.get('texts', [])
            custom_elements = record.get('custom_elements', [])
            
            if not texts and not custom_elements:
                empty_records += 1
            else:
                records_with_text += 1
            
            total_text_items += len(texts) + len(custom_elements)
            empty_text_items += len([t for t in texts if not t.get('text', '').strip()])
            empty_text_items += len([c for c in custom_elements if not c.get('text', '').strip()])
        
        report += "📊 DATA QUALITY METRICS:\n"
        report += f"• Empty records: {empty_records} ({empty_records/total_records*100:.1f}%)\n"
        report += f"• Records with content: {records_with_text} ({records_with_text/total_records*100:.1f}%)\n"
        report += f"• Total text items: {total_text_items}\n"
        report += f"• Empty text items: {empty_text_items} ({empty_text_items/total_text_items*100:.1f}%)\n\n"
        
        report += "💡 RECOMMENDATIONS:\n"
        if empty_records > 0:
            report += "• Consider removing empty records\n"
        if empty_text_items > 0:
            report += "• Clean up empty text items\n"
        if records_with_text == 0:
            report += "• No usable data found - check scraping configuration\n"
        
        self.analysis_text.setPlainText(report)

    def generate_chart(self, chart_type):
        """Generate charts based on data"""
        self.chart_canvas.figure.clear()
        ax = self.chart_canvas.figure.add_subplot(111)
        
        # Prepare data for charting
        if chart_type == "Bar Chart":
            self.create_bar_chart(ax)
        elif chart_type == "Line Chart":
            self.create_line_chart(ax)
        elif chart_type == "Pie Chart":
            self.create_pie_chart(ax)
        elif chart_type == "Histogram":
            self.create_histogram(ax)
        
        self.chart_canvas.draw()

    def create_bar_chart(self, ax):
        """Create bar chart of data types"""
        types_count = {
            'Texts': sum(len(record.get('texts', [])) for record in self.collected_data),
            'Custom': sum(len(record.get('custom_elements', [])) for record in self.collected_data),
            'Images': sum(len(record.get('images', [])) for record in self.collected_data),
            'Links': sum(len(record.get('links', [])) for record in self.collected_data)
        }
        
        bars = ax.bar(types_count.keys(), types_count.values(), color=['#3498db', '#2ecc71', '#e74c3c', '#f39c12'])
        ax.set_title('Data Types Distribution')
        ax.set_ylabel('Count')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')

    def create_line_chart(self, ax):
        """Create line chart of records over time"""
        if len(self.collected_data) < 2:
            ax.text(0.5, 0.5, 'Need at least 2 records for timeline', 
                    ha='center', va='center', transform=ax.transAxes)
            return
        
        # Extract timestamps and counts
        timestamps = []
        text_counts = []
        
        for i, record in enumerate(self.collected_data):
            timestamps.append(i + 1)
            text_counts.append(len(record.get('texts', [])))
    
        ax.plot(timestamps, text_counts, marker='o', linewidth=2)
        ax.set_title('Text Items per Record')
        ax.set_xlabel('Record Number')
        ax.set_ylabel('Text Count')
        ax.grid(True, alpha=0.3)

    def create_pie_chart(self, ax):
        """Create pie chart of source distribution"""
        sources = {}
        for record in self.collected_data:
            source = record.get('metadata', {}).get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        if not sources:
            ax.text(0.5, 0.5, 'No data available', 
                    ha='center', va='center', transform=ax.transAxes)
            return
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(sources)))
        wedges, texts, autotexts = ax.pie(sources.values(), labels=sources.keys(), autopct='%1.1f%%',
                                         colors=colors, startangle=90)
        ax.set_title('Data Source Distribution')

    def create_histogram(self, ax):
        """Create histogram of text lengths"""
        all_texts = []
        for record in self.collected_data:
            all_texts.extend([text.get('text', '') for text in record.get('texts', [])])
            all_texts.extend([custom.get('text', '') for custom in record.get('custom_elements', [])])
        
        text_lengths = [len(text) for text in all_texts if text.strip()]
        
        if not text_lengths:
            ax.text(0.5, 0.5, 'No text data available', 
                    ha='center', va='center', transform=ax.transAxes)
            return
        
        ax.hist(text_lengths, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax.set_title('Text Length Distribution')
        ax.set_xlabel('Text Length (characters)')
        ax.set_ylabel('Frequency')

    def clean_data(self):
        """Open data cleaning dialog"""
        if not self.collected_data:
            QMessageBox.warning(self.main_window, "Warning", "No data to clean")
            return
        
        dialog = DataCleaningDialog(self.main_window)
        if dialog.exec_() == QDialog.Accepted:
            cleaning_options = dialog.get_cleaning_options()
            self.apply_data_cleaning(cleaning_options)

    def apply_data_cleaning(self, options):
        """Apply data cleaning based on options"""
        original_count = len(self.collected_data)
        
        # Remove empty records
        if options.get('remove_empty', False):
            self.collected_data = [record for record in self.collected_data 
                                 if record.get('texts') or record.get('custom_elements')]
        
        # Remove duplicate texts
        if options.get('remove_duplicates', False):
            seen_texts = set()
            for record in self.collected_data:
                unique_texts = []
                for text in record.get('texts', []):
                    text_content = text.get('text', '').strip()
                    if text_content and text_content not in seen_texts:
                        seen_texts.add(text_content)
                        unique_texts.append(text)
                record['texts'] = unique_texts
        
        # Trim whitespace
        if options.get('trim_whitespace', False):
            for record in self.collected_data:
                for text in record.get('texts', []):
                    if 'text' in text:
                        text['text'] = text['text'].strip()
                for custom in record.get('custom_elements', []):
                    if 'text' in custom:
                        custom['text'] = custom['text'].strip()
        
        new_count = len(self.collected_data)
        removed_count = original_count - new_count
        
        self.main_window.update_extension_status(f"🧹 Data cleaning completed: {removed_count} records removed")
        self.refresh_data_view()
        
        if removed_count > 0:
            QMessageBox.information(self.main_window, "Success", 
                                   f"Data cleaning completed!\nRemoved {removed_count} records/items.")

    def export_data(self, format_type='json'):
        """Export data in specified format"""
        if not self.collected_data:
            QMessageBox.warning(self.main_window, "Warning", "No data to export")
            return
        
        if format_type == 'json':
            self.export_to_json()
        else:
            self.export_to_csv()

    def export_to_json(self):
        """Export data to JSON file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window, "Export JSON", "scraped_data.json", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.collected_data, f, indent=2, ensure_ascii=False)
                
                self.main_window.update_extension_status(f"💾 Data exported to JSON: {file_path}")
                QMessageBox.information(self.main_window, "Success", f"Data exported successfully to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"Failed to export JSON:\n{str(e)}")

    def export_to_csv(self):
        """Export data to CSV file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window, "Export CSV", "scraped_data.csv", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                # Prepare data for CSV
                csv_data = []
                
                for record_idx, record in enumerate(self.collected_data):
                    metadata = record.get('metadata', {})
                    
                    # Add texts
                    for text in record.get('texts', []):
                        csv_data.append({
                            'record_id': record_idx + 1,
                            'type': 'text',
                            'source': metadata.get('source', ''),
                            'url': metadata.get('url', ''),
                            'timestamp': metadata.get('timestamp', ''),
                            'selector': text.get('selector', ''),
                            'content': text.get('text', ''),
                            'full_content': text.get('full_text', '')
                        })
                    
                    # Add custom elements
                    for custom in record.get('custom_elements', []):
                        csv_data.append({
                            'record_id': record_idx + 1,
                            'type': 'custom',
                            'source': metadata.get('source', ''),
                            'url': metadata.get('url', ''),
                            'timestamp': metadata.get('timestamp', ''),
                            'selector': custom.get('selector', ''),
                            'content': custom.get('text', ''),
                            'full_content': custom.get('full_text', '')
                        })
                
                if csv_data:
                    df = pd.DataFrame(csv_data)
                    df.to_csv(file_path, index=False, encoding='utf-8')
                    
                    self.main_window.update_extension_status(f"📊 Data exported as CSV: {len(csv_data)} rows")
                    QMessageBox.information(self.main_window, "Success", 
                                          f"CSV export completed!\n{len(csv_data)} rows exported to:\n{file_path}")
                else:
                    QMessageBox.warning(self.main_window, "Warning", "No data available for CSV export")
                    
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"Failed to export CSV:\n{str(e)}")

    def refresh_data_view(self):
        """Refresh all data views"""
        self.update_records_list()
        
        # Refresh table if a record is selected
        selected_items = self.records_list.selectedItems()
        if selected_items:
            self.on_record_selected()
        
        self.main_window.update_extension_status("🔃 Data view refreshed")

    def clear_data(self):
        """Clear all collected data"""
        if not self.collected_data:
            return
        
        reply = QMessageBox.question(self.main_window, "Confirm Clear", 
                                   "Are you sure you want to clear all collected data?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.collected_data.clear()
            self.save_data_to_file()
            self.refresh_data_view()
            self.main_window.update_extension_status("🗑️ All data cleared")

    def save_data_to_file(self):
        """Save current data to file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.collected_data, f, indent=2, ensure_ascii=False)
            self.main_window.update_extension_status(f"💾 Data saved to {self.data_file}")
        except Exception as e:
            self.main_window.update_extension_status(f"❌ Error saving data: {str(e)}")

    def load_saved_data(self):
        """Load previously saved data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    self.collected_data = saved_data
                self.main_window.update_extension_status(f"📂 Loaded {len(self.collected_data)} saved records")
                self.refresh_data_view()
        except Exception as e:
            self.main_window.update_extension_status(f"⚠️ Error loading saved data: {str(e)}")

    def add_data(self, data):
        """Add new data to the collection"""
        self.collected_data.append(data)
        self.save_data_to_file()
        self.refresh_data_view()