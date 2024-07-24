from flask import Flask, request, jsonify
from CostOptTool.ui.azure_cost_optimizer import main as optimizer_main
import os
import threading

app = Flask(__name__)

@app.route('/api/run', methods=['POST'])
def run_optimizer():
    mode = request.json.get('mode')
    all_subscriptions = request.json.get('all_subscriptions', False)
    use_adls = request.json.get('use_adls', False)

    def run_optimizer_in_thread():
        optimizer_main(mode, all_subscriptions, use_adls)

    thread = threading.Thread(target=run_optimizer_in_thread)
    thread.start()

    return jsonify({'status': 'Optimizer started'}), 200

@app.route('/api/status', methods=['GET'])
def get_status():
    # Implement status retrieval logic if needed
    return jsonify({'status': 'Running'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
