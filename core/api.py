from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import time
import io
import threading
from core.control import ScriptControl
from core.logger import get_logger

class BotAPI:
    def __init__(self, client=None):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for all routes
        self.control = ScriptControl()
        self.client = client  # Reference to RuneLiteClient instance
        self.log = get_logger("API")
        self.start_time = time.time()
        self.thread = None
        
        # Define routes
        self.register_routes()
        
    def register_routes(self):
        # Status endpoints
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            return jsonify({
                'running': not self.control.terminate,
                'paused': self.control.pause,
                'runtime': time.time() - self.start_time
            })
        
        # Control endpoints
        @self.app.route('/api/control/terminate', methods=['GET'])
        def get_terminate():
            return jsonify({'terminate': self.control.terminate})
            
        @self.app.route('/api/control/terminate', methods=['POST'])
        def set_terminate():
            value = request.json.get('terminate', False)
            self.control.terminate = bool(value)
            return jsonify({'terminate': self.control.terminate})
        
        @self.app.route('/api/control/pause', methods=['GET'])
        def get_pause():
            return jsonify({'pause': self.control.pause})
            
        @self.app.route('/api/control/pause', methods=['POST'])
        def set_pause():
            value = request.json.get('pause', False)
            self.control.pause = bool(value)
            return jsonify({'pause': self.control.pause})
        
        # Screenshot endpoint
        @self.app.route('/api/screenshot', methods=['GET'])
        def get_screenshot():
            if not self.client:
                return jsonify({'error': 'Client not available'}), 503
                
            try:
                screenshot = self.client.get_screenshot()
                img_io = io.BytesIO()
                screenshot.save(img_io, 'PNG')
                img_io.seek(0)
                return send_file(img_io, mimetype='image/png')
            except Exception as e:
                self.log.error(f"Screenshot error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        # Runtime endpoint
        @self.app.route('/api/runtime', methods=['GET'])
        def get_runtime():
            runtime_seconds = time.time() - self.start_time
            hours, remainder = divmod(runtime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return jsonify({
                'runtime_seconds': runtime_seconds,
                'formatted': f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}",
                'started_at': self.start_time
            })
    
    def start(self, port=5432):
        """Start the API server in a background thread"""
        if self.thread and self.thread.is_alive():
            self.log.warning("API server is already running")
            return
            
        def run_server():
            self.log.info(f"Starting API server on port {port}")
            self.app.run(host='0.0.0.0', port=port, threaded=True)
            
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop the API server (if running)"""
        # Note: Flask doesn't provide a clean way to stop from another thread
        self.log.info("API shutdown requested - server will stop when process terminates")


# Function to create and configure a BotAPI instance
def create_bot_api(client=None):
    return BotAPI(client)
