from flask import Flask, request, jsonify
from PyQt5.QtCore import QThread, pyqtSignal
import json

class FlaskServerThread(QThread):
    data_received = pyqtSignal(dict)
    message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.app = Flask(__name__)
        self.is_running = True
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({"status": "healthy"}), 200
            
        @self.app.route('/store', methods=['POST'])
        def store_data():
            try:
                data = request.get_json()
                if data:
                    self.data_received.emit(data)
                    self.message.emit("✅ Data received by Flask server")
                    return jsonify({"status": "success"}), 200
                else:
                    return jsonify({"error": "No data received"}), 400
            except Exception as e:
                self.message.emit(f"❌ Flask server error: {str(e)}")
                return jsonify({"error": str(e)}), 500

    def run(self):
        try:
            self.message.emit("🚀 Starting Flask server on http://127.0.0.1:5584")
            self.app.run(host='127.0.0.1', port=5584, debug=False, threaded=True)
        except Exception as e:
            self.message.emit(f"❌ Flask server failed: {str(e)}")

    def stop_server(self):
        self.is_running = False