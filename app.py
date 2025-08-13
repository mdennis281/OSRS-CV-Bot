from flask import Flask, jsonify, render_template
import psutil
import time

app = Flask(__name__)

@app.route('/metrics')
def get_metrics():
    cpu_usage = psutil.cpu_percent(interval=1)
    gpu_usage = 43  # Placeholder for GPU usage
    ram_used = psutil.virtual_memory().used
    ram_free = psutil.virtual_memory().free
    return jsonify({
        "cpu": cpu_usage,
        "gpu": gpu_usage,
        "ram": {
            "used": ram_used,
            "free": ram_free
        }
    })

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5012)
