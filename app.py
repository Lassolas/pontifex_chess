from flask import Flask, render_template, request, jsonify
import os
import csv
from datetime import datetime

app = Flask(__name__)

# Configure results directory
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_results', methods=['POST'])
def submit_results():
    try:
        data = request.get_json()
        patient_name = data.get('patientName', 'unknown')
        trial_data = data.get('trialData', [])
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{patient_name}_{timestamp}.csv"
        filepath = os.path.join(RESULTS_DIR, filename)
        
        # Write data to CSV
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['trial', 'trialTime', 'attackingPiece', 'attackingPosition', 
                         'attackedPieces', 'responseTime', 'success', 'responsePosition']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for trial in trial_data:
                writer.writerow(trial)
        
        return jsonify({'status': 'success', 'message': f'Results saved to {filename}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Use port 5001 to avoid conflict with AirPlay on macOS
    port = int(os.environ.get('PORT', 5000))
    # Run the app on 0.0.0.0 to accept external connections
    app.run(host='0.0.0.0', port=port, debug=False) 