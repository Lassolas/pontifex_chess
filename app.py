from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

# Google Sheets API setup
SHEET_ID = "1M2TjhCmjLX6w3POBNoTLlC1QXOeZxXIPaKjTPrdECeo"  # Replace with your existing sheet ID

# Set up Google Sheets API client
def get_sheets_service():
    creds = Credentials.from_service_account_file('credentials/credentials.json', scopes=["https://www.googleapis.com/auth/spreadsheets"])
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_results', methods=['POST'])
def submit_results():
    try:
        data = request.get_json()
        patient_name = data.get('patientName', 'unknown')
        trial_data = data.get('trialData', [])
        
        # Log the data being submitted
        print(f"Submitting results for patient: {patient_name}")
        print("Trial Data:", trial_data)

        # Create a new sheet with the patient's name
        service = get_sheets_service()
        new_sheet_name = patient_name  # Use patient name as the sheet name
        
        # Check if the sheet already exists, and if not, create it
        spreadsheet = service.get(spreadsheetId=SHEET_ID).execute()
        sheet_names = [s['properties']['title'] for s in spreadsheet['sheets']]
        
        if new_sheet_name not in sheet_names:
            # Create a new sheet with the patient name
            service.batchUpdate(spreadsheetId=SHEET_ID, body={
                "requests": [{
                    "addSheet": {
                        "properties": {
                            "title": new_sheet_name
                        }
                    }
                }]
            }).execute()

        # Prepare data to be written to the new sheet
        sheet_data = [
            ['Trial', 'Trial Time', 'Attacking Piece', 'Attacking Position', 'Attacked Pieces', 'Response Time', 'Success', 'Response Position']
        ]
        for trial in trial_data:
            sheet_data.append([
                trial['trial'],
                trial['trialTime'],
                trial['attackingPiece'],
                trial['attackingPosition'],
                trial['attackedPieces'],
                trial['responseTime'],
                trial['success'],
                trial['responsePosition']
            ])
        
        # Log the data to be written to the Google Sheet
        print("Data to be written to Google Sheet:", sheet_data)

        # Append data to the newly created sheet
        range_name = f"{new_sheet_name}!A1"  # Insert data starting from the first cell of the new sheet
        result = service.values().append(
            spreadsheetId=SHEET_ID,
            range=range_name,
            valueInputOption="RAW",
            body={"values": sheet_data}
        ).execute()

        # Log the result from the Google Sheets API
        print("Google Sheets API response:", result)

        return jsonify({'status': 'success', 'message': f'Results saved to sheet {new_sheet_name}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
