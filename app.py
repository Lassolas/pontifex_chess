from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import logging
import re

app = Flask(__name__)

# Load environment variables from the .env file
load_dotenv()

# Google Sheets API setup
SHEET_ID = "1M2TjhCmjLX6w3POBNoTLlC1QXOeZxXIPaKjTPrdECeo"  # Replace with your existing sheet ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Redact sensitive information from logs
def redact_sensitive_data(message):
    """Redact potentially sensitive information from log messages"""
    if isinstance(message, str):
        # Redact anything that looks like a key, token, or credential
        patterns = [
            r'key"?\s*:\s*"[^"]*"',
            r'private_key"?\s*:\s*"[^"]*"',
            r'token"?\s*:\s*"[^"]*"',
            r'password"?\s*:\s*"[^"]*"',
            r'secret"?\s*:\s*"[^"]*"',
            r'credential"?\s*:\s*"[^"]*"',
            r'auth"?\s*:\s*"[^"]*"'
        ]
        
        redacted_message = message
        for pattern in patterns:
            redacted_message = re.sub(pattern, r'REDACTED', redacted_message, flags=re.IGNORECASE)
        
        return redacted_message
    return message

def safe_log(level, message):
    """Log messages with sensitive data redacted"""
    redacted = redact_sensitive_data(message)
    if level == 'error':
        logging.error(redacted)
    elif level == 'warning':
        logging.warning(redacted)
    else:
        logging.info(redacted)

# Function to get Google Sheets service
def get_sheets_service():
    try:
        if "GOOGLE_SHEET_CREDENTIALS" in os.environ:
            credentials_json = os.environ["GOOGLE_SHEET_CREDENTIALS"]
            try:
                credentials_info = json.loads(credentials_json)
            except json.JSONDecodeError as e:
                safe_log('error', f"Error decoding JSON: {e}")
                raise  # Re-raise the exception to handle it later
        else:
            safe_log('error', "No credentials found!")
            raise ValueError("GOOGLE_SHEET_CREDENTIALS is not set.")

        creds = service_account.Credentials.from_service_account_info(credentials_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])

        service = build("sheets", "v4", credentials=creds)

        # Return the service object directly, not service.spreadsheets()
        return service
    except Exception as e:
        safe_log('error', f"Error loading credentials or creating service: {str(e)}")
        raise  # Re-raise the exception for further handling

# update leaderboard automatically
def update_leaderboard(service, current_user=None, current_difficulty=None, current_ies=None, current_board_time=None):
    try:
        safe_log('info', "Updating leaderboard...")

        # Get current spreadsheet
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheet_titles = [s['properties']['title'] for s in spreadsheet['sheets']]
        leaderboard_sheet_name = "Leaderboard"

        # Find existing leaderboard sheet (case-insensitive)
        existing_leaderboard = None
        for sheet in sheet_titles:
            if sheet.lower() == leaderboard_sheet_name.lower():
                existing_leaderboard = sheet
                break
        
        # Use existing sheet if found, otherwise create new one
        if existing_leaderboard:
            leaderboard_sheet_name = existing_leaderboard
        elif leaderboard_sheet_name not in sheet_titles:
            service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={
                "requests": [{
                    "addSheet": {
                        "properties": {"title": leaderboard_sheet_name}
                    }
                }]
            }).execute()

        # Organize entries by difficulty
        easy_entries = []
        medium_entries = []
        hard_entries = []

        # Add current user if provided
        if current_user and current_difficulty and current_ies is not None:
            if current_difficulty.lower() == "easy":
                easy_entries.append([current_user, current_ies, current_difficulty, current_board_time])
            elif current_difficulty.lower() == "medium":
                medium_entries.append([current_user, current_ies, current_difficulty, current_board_time])
            elif current_difficulty.lower() == "hard":
                hard_entries.append([current_user, current_ies, current_difficulty, current_board_time])

        # Collect existing entries from all sheets
        for sheet_name in sheet_titles:
            if sheet_name == leaderboard_sheet_name or sheet_name == current_user:
                continue

            try:
                # Get data from sheet
                values = service.spreadsheets().values().get(
                    spreadsheetId=SHEET_ID, 
                    range=f"{sheet_name}!A1:B20"
                ).execute().get("values", [])
                
                data_dict = {row[0]: row[1] for row in values if len(row) > 1}

                # Extract difficulty and IES
                ies = float(data_dict.get("IES Score", data_dict.get("IES", 0)))
                difficulty = data_dict.get("Difficulty", "N/A")
                board_time = float(data_dict.get("Board Display Time", 0))
                
                entry = [sheet_name, ies, difficulty, board_time]
                
                # Add to appropriate difficulty list
                if difficulty.lower() == "easy":
                    easy_entries.append(entry)
                elif difficulty.lower() == "medium":
                    medium_entries.append(entry)
                elif difficulty.lower() == "hard":
                    hard_entries.append(entry)
            except Exception as e:
                safe_log('warning', f"Skipping sheet {sheet_name} due to missing or invalid data: {e}")
                continue

        # Sort each difficulty group by IES (ascending)
        easy_entries = sorted(easy_entries, key=lambda x: float(x[1]))
        medium_entries = sorted(medium_entries, key=lambda x: float(x[1]))
        hard_entries = sorted(hard_entries, key=lambda x: float(x[1]))

        # Track current user's position in each difficulty
        current_user_easy_pos = next((i for i, entry in enumerate(easy_entries) if entry[0] == current_user), -1)
        current_user_medium_pos = next((i for i, entry in enumerate(medium_entries) if entry[0] == current_user), -1)
        current_user_hard_pos = next((i for i, entry in enumerate(hard_entries) if entry[0] == current_user), -1)

        # Prepare the leaderboard data with headers for Google Sheets
        leaderboard_data = [
            ["Easy Difficulty", "", "", "Medium Difficulty", "", "", "Hard Difficulty", "", ""],
            ["Rank", "Name", "IES (s)", "Rank", "Name", "IES (s)", "Rank", "Name", "IES (s)"]
        ]

        # Calculate the maximum number of entries across all difficulties
        max_entries = max(len(easy_entries), len(medium_entries), len(hard_entries))
        
        # Add all entries to the Google Sheet
        for i in range(max_entries):
            row = []
            
            # Easy difficulty column
            if i < len(easy_entries):
                row.extend([i+1, easy_entries[i][0], easy_entries[i][1]])
            else:
                row.extend(["", "", ""])
                
            # Medium difficulty column
            if i < len(medium_entries):
                row.extend([i+1, medium_entries[i][0], medium_entries[i][1]])
            else:
                row.extend(["", "", ""])
                
            # Hard difficulty column
            if i < len(hard_entries):
                row.extend([i+1, hard_entries[i][0], hard_entries[i][1]])
            else:
                row.extend(["", "", ""])
                
            leaderboard_data.append(row)

        # Clear the leaderboard sheet and write new data
        service.spreadsheets().values().clear(
            spreadsheetId=SHEET_ID, 
            range=f"{leaderboard_sheet_name}!A1:I1000"
        ).execute()
        
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{leaderboard_sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": leaderboard_data}
        ).execute()

        safe_log('info', "Leaderboard updated successfully.")
        
        # Return the data for frontend display
        return leaderboard_data

    except Exception as e:
        safe_log('error', f"Error updating leaderboard: {str(e)}")
        raise

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

@app.route('/get_leaderboard')
def get_leaderboard():
    try:
        safe_log('info', "Fetching leaderboard data...")
        
        # Create service
        service = get_sheets_service()
        
        # Get leaderboard data
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="Leaderboard!A1:I1000"
        ).execute()
        
        leaderboard_data = result.get('values', [])
        safe_log('info', f"Raw leaderboard data rows: {len(leaderboard_data)}")
        
        # Format the data for frontend display
        formatted_data = format_leaderboard_data(leaderboard_data)
        safe_log('info', f"Formatted leaderboard data: {formatted_data}")
        
        response = jsonify({"success": True, "leaderboard": formatted_data})
        safe_log('info', "Leaderboard response prepared")
        return response
    
    except Exception as e:
        safe_log('error', f"Error fetching leaderboard: {str(e)}")
        return jsonify({"success": False, "message": f"Error fetching leaderboard data: {str(e)}"})

@app.route('/submit_results', methods=['POST'])
def submit_results():
    try:
        data = request.json
        safe_log('debug', f"Received submission data: {data}")
        
        patient_name = data.get('patientName')
        trial_data = data.get('trialData')
        difficulty = data.get('difficulty')
        duration = data.get('duration')
        
        # Check both possible field names (for backward compatibility)
        board_display_time = data.get('boardDisplayTime')
        if board_display_time is None:
            board_display_time = data.get('hideTime')  # Use the old name as fallback
            
        safe_log('info', f"Board display time from request: {board_display_time} seconds")

        # Map difficulty to display names if needed
        display_difficulty = "Easy"  # Default
        if difficulty.lower() == "hard":
            display_difficulty = "Medium"
        elif difficulty.lower() == "very hard":
            display_difficulty = "Hard"

        # Validate required fields
        if not all([patient_name, trial_data, difficulty, board_display_time]):
            safe_log('error', f"Missing required fields - boardDisplayTime: {board_display_time}")
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # Calculate IES score
        ies = calculate_ies(trial_data)
        
        # Create service
        service = get_sheets_service()
        
        # 1. First save detailed results to a new sheet
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        
        sheet_data = [
            ['Date', current_date],
            ['Time', current_time],
            ['Patient Name', patient_name],
            ['Difficulty', display_difficulty],
            ['Duration', duration],
            ['Board Display Time', board_display_time],
            ['IES Score', ies],
            ['Trial', 'Trial Time', 'Attacking Piece', 'Attacking Position', 
             'Attacked Pieces', 'Response Time', 'Success', 'Response Position']
        ]
        
        for trial in trial_data:
            sheet_data.append([
                trial.get('trial', ''),
                trial.get('trialTime', ''),
                trial.get('attackingPiece', ''),
                trial.get('attackingPosition', ''),
                trial.get('attackedPieces', ''),
                trial.get('responseTime', ''),
                trial.get('success', ''),
                trial.get('responsePosition', '')
            ])
        
        # Create new sheet for patient results if it doesn't exist
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheet_titles = [s['properties']['title'] for s in spreadsheet['sheets']]
        
        if patient_name not in sheet_titles:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={
                    "requests": [{
                        "addSheet": {
                            "properties": {"title": patient_name}
                        }
                    }]
                }
            ).execute()
        
        # 2. Write data to sheet
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{patient_name}!A1",
            valueInputOption="RAW",
            body={"values": sheet_data}
        ).execute()

        # 3. Update leaderboard with correct difficulty
        update_leaderboard_result = update_leaderboard(
            service,
            current_user=patient_name,
            current_difficulty=display_difficulty.lower(),
            current_ies=ies,
            current_board_time=board_display_time
        )
        
        # 4. Get the updated leaderboard data to return
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range="Leaderboard!A1:I1000"
            ).execute()
            
            leaderboard_data = result.get('values', [])
            
            # Format leaderboard data for response
            formatted_leaderboard = format_leaderboard_data(leaderboard_data)
            
            # Return the leaderboard data with the results
            return jsonify({
                "success": True, 
                "ies": ies,
                "leaderboard": formatted_leaderboard  # Include the leaderboard directly in the response
            })
        except Exception as e:
            safe_log('error', f"Error getting updated leaderboard: {str(e)}")
            # Still return success for the submission, even if leaderboard fetch failed
            return jsonify({"success": True, "ies": ies})
        
    except Exception as e:
        safe_log('error', f"Error submitting results: {str(e)}")
        return jsonify({"success": False, "message": "Error submitting results"}), 500
        
def format_leaderboard_data(leaderboard_data):
    safe_log('info', f"Formatting leaderboard data with {len(leaderboard_data)} rows")
    
    if len(leaderboard_data) <= 1:  # Only header or empty
        safe_log('warning', "Leaderboard data has only headers or is empty")
        return {"easy": [], "medium": [], "hard": []}
        
    formatted_data = {
        'easy': [],
        'medium': [],
        'hard': []
    }
    
    for i, row in enumerate(leaderboard_data[1:]):  # Skip header row
        try:
            # Skip header rows
            if len(row) >= 9 and row[0] != "Rank" and row[3] != "Rank" and row[6] != "Rank":
                # Easy column
                if row[1] and row[1] != "Name":
                    formatted_data['easy'].append({
                        'rank': row[0],
                        'name': row[1],
                        'score': row[2]
                    })
                # Medium column
                if row[4] and row[4] != "Name":
                    formatted_data['medium'].append({
                        'rank': row[3],
                        'name': row[4],
                        'score': row[5]
                    })
                # Hard column
                if row[7] and row[7] != "Name":
                    formatted_data['hard'].append({
                        'rank': row[6],
                        'name': row[7],
                        'score': row[8]
                    })
        except (IndexError, ValueError) as e:
            safe_log('warning', f"Skipping invalid leaderboard row {i+1}: {row}, error: {str(e)}")
    
    safe_log('info', f"Formatted leaderboard entries - Easy: {len(formatted_data['easy'])}, Medium: {len(formatted_data['medium'])}, Hard: {len(formatted_data['hard'])}")
    return formatted_data

def calculate_ies(trial_data):
    """
    Calculate Inverse Efficiency Score (IES) from trial data.
    IES = median response time / accuracy
    
    Includes:
    - Minimum trial threshold (require at least 5 successful trials)
    - Smoothing factor to prevent explosion when accuracy approaches 0
    """
    if not trial_data:
        return 999999
    
    # Calculate accuracy (proportion of successful trials)
    total_trials = len(trial_data)
    successful_trials = sum(1 for trial in trial_data if trial.get('success') == 1)
    
    # Check minimum trial threshold
    if successful_trials < 5:
        return 999999  # Return None to indicate insufficient trials
    
    # Calculate accuracy 
    accuracy = successful_trials / total_trials if total_trials > 0 else 0  # Avoid division by zero
    
    # Calculate median response time for successful trials
    if successful_trials > 0:
        response_times = [trial.get('responseTime', 0) for trial in trial_data if trial.get('success') == 1]
        # Sort response times and get median
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        if n % 2 == 1:
            median_response_time = sorted_times[n // 2]
        else:
            median_response_time = (sorted_times[n // 2 - 1] + sorted_times[n // 2]) / 2
    else:
        # If no successful trials, use all trials
        response_times = [trial.get('responseTime', 0) for trial in trial_data]
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        if n % 2 == 1:
            median_response_time = sorted_times[n // 2]
        else:
            median_response_time = (sorted_times[n // 2 - 1] + sorted_times[n // 2]) / 2
    
    # Calculate IES with smoothing
    ies = median_response_time / accuracy if accuracy > 0 else 999999
    
    return round(ies, 2)  # Round to 2 decimal places for consistency

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)