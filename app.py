from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv


app = Flask(__name__)

# Load environment variables from the .env file
load_dotenv()

# Google Sheets API setup
SHEET_ID = "1M2TjhCmjLX6w3POBNoTLlC1QXOeZxXIPaKjTPrdECeo"  # Replace with your existing sheet ID

# Function to get Google Sheets service
def get_sheets_service():
    try:
        # Load credentials from the environment variable
        google_credentials = os.getenv('GOOGLE_SHEET_CREDENTIALS')

        # Print the credentials for debugging
        print("Google Credentials:", google_credentials)  # Log the credentials

        if google_credentials:
            print("Google Credentials loaded successfully.")
            try:
                credentials_info = json.loads(google_credentials)
                print("Credentials are valid.")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                raise  # Re-raise the exception to handle it later
        else:
            print("No credentials found!")
            raise ValueError("GOOGLE_SHEET_CREDENTIALS is not set.")

        creds = service_account.Credentials.from_service_account_info(credentials_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])

        # Log successful credential loading
        print("Credentials loaded successfully.")

        service = build("sheets", "v4", credentials=creds)

        # Log successful service creation
        print("Google Sheets service created successfully.")

        return service.spreadsheets()
    except Exception as e:
        print(f"Error loading credentials or creating service: {str(e)}")
        raise  # Re-raise the exception for further handling

@app.route('/')
def index():
    return render_template('index.html')

#health check
@app.route('/health')
def health():
    return "OK", 200

#add a ping return
@app.route("/ping")
def ping():
    return "pong", 200

@app.route('/submit_results', methods=['POST'])
def submit_results():
    try:
        data = request.get_json()
        patient_name = data.get('patientName', 'unknown')
        trial_data = data.get('trialData', [])
        
        # Extract configuration settings
        difficulty = data.get('difficulty', 'N/A')
        test_duration = data.get('testDuration', 'N/A')
        board_display_time = data.get('boardDisplayTime', 'N/A')

        # Log the data being submitted
        print(f"Submitting results for patient: {patient_name}")
        print("Trial Data:", trial_data)
        print(f"Configuration - Difficulty: {difficulty}, Test Duration: {test_duration}, Board Display Time: {board_display_time}")

        # Create a new sheet with the patient's name
        service = get_sheets_service()
        new_sheet_name = patient_name  # Use patient name as the sheet name

        # Check if the sheet already exists, and if not, create it
        spreadsheet = service.get(spreadsheetId=SHEET_ID).execute()

        # Log the spreadsheet metadata to confirm access
        print("Spreadsheet metadata retrieved successfully:", spreadsheet)

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
            print(f"New sheet created: {new_sheet_name}")

        # Prepare data to be written to the new sheet
        sheet_data = [
            ['Difficulty', difficulty],  # Header for Difficulty
            ['Test Duration', test_duration],  # Header for Test Duration
            ['Board Display Time', board_display_time],  # Header for Board Display Time
            ['Trial', 'Trial Time', 'Attacking Piece', 'Attacking Position', 'Attacked Pieces', 'Response Time', 'Success', 'Response Position']  # Main headers
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
        range_name = f"{new_sheet_name}!A1"
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
        print(f"Error occurred: {str(e)}")  # Log the error message
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
