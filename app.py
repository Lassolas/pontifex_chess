from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import logging
import re
import math

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
            r'credential"?\scorr*:\s*"[^"]*"',
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
def update_leaderboard(service, current_user=None, current_difficulty=None, current_ies=None, current_board_time=None, current_drift=None, current_stability=None):
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
        if current_user and current_difficulty and current_ies is not None and current_drift is not None and current_stability is not None:
            if current_difficulty.lower() == "easy":
                easy_entries.append([current_user, current_ies, current_drift, current_stability, current_difficulty, current_board_time])
            elif current_difficulty.lower() == "medium":
                medium_entries.append([current_user, current_ies, current_drift, current_stability, current_difficulty, current_board_time])
            elif current_difficulty.lower() == "hard":
                hard_entries.append([current_user, current_ies, current_drift, current_stability, current_difficulty, current_board_time])

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

                # Extract difficulty, IES, drift, and stability
                ies = data_dict.get("Overall IES Score", data_dict.get("IES Score", data_dict.get("IES", "999999")))
                try:
                    ies = float(ies)
                except (ValueError, TypeError):
                    ies = 999999
                
                difficulty = data_dict.get("Difficulty", "N/A")
                board_time = float(data_dict.get("Board Display Time", 0))
                
                # Extract drift and stability
                drift = data_dict.get("Focus Drift", "0")
                stability = data_dict.get("Focus Stability", "0")
                
                try:
                    drift = float(drift)
                    stability = float(stability)
                except (ValueError, TypeError):
                    drift = 0
                    stability = 0
                
                entry = [sheet_name, ies, drift, stability, difficulty, board_time]
                
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
            ["Easy Difficulty", "", "", "", "", "Medium Difficulty", "", "", "", "", "Hard Difficulty", "", "", ""],
            ["Rank", "Name", "IES (s)", "Drift", "Stability", 
             "Rank", "Name", "IES (s)", "Drift", "Stability", 
             "Rank", "Name", "IES (s)", "Drift", "Stability"]
        ]

        # Calculate the maximum number of entries across all difficulties
        max_entries = max(len(easy_entries), len(medium_entries), len(hard_entries))
        
        # Add all entries to the Google Sheet
        for i in range(max_entries):
            # Add easy entries
            if i < len(easy_entries):
                entry = easy_entries[i]
                leaderboard_data.append([
                    i + 1,  # Rank
                    entry[0],  # Name
                    entry[1],  # IES
                    entry[2],  # Drift
                    entry[3],  # Stability
                    "", "", "", "", "",  # Medium placeholders
                    "", "", "", "", ""   # Hard placeholders
                ])
            # Add medium entries
            elif i < len(easy_entries) + len(medium_entries):
                entry = medium_entries[i - len(easy_entries)]
                leaderboard_data.append([
                    "", "", "", "", "",  # Easy placeholders
                    i + 1 - len(easy_entries),  # Rank
                    entry[0],  # Name
                    entry[1],  # IES
                    entry[2],  # Drift
                    entry[3],  # Stability
                    "", "", "", "", ""   # Hard placeholders
                ])
            # Add hard entries
            else:
                entry = hard_entries[i - len(easy_entries) - len(medium_entries)]
                leaderboard_data.append([
                    "", "", "", "", "",  # Easy placeholders
                    "", "", "", "", "",  # Medium placeholders
                    i + 1 - len(easy_entries) - len(medium_entries),  # Rank
                    entry[0],  # Name
                    entry[1],  # IES
                    entry[2],  # Drift
                    entry[3]   # Stability
                ])
        
        # Clear the leaderboard sheet and write new data
        service.spreadsheets().values().clear(
            spreadsheetId=SHEET_ID, 
            range=f"{leaderboard_sheet_name}!A1:O1000"
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
            range="Leaderboard!A1:O1000"
        ).execute()
        
        leaderboard_data = result.get('values', [])        
        # Format the data for frontend display
        formatted_data = format_leaderboard_data(leaderboard_data)

        response = jsonify({"success": True, "leaderboard": formatted_data})
        return response
    
    except Exception as e:
        safe_log('error', f"Error fetching leaderboard: {str(e)}")
        return jsonify({"success": False, "message": f"Error fetching leaderboard data: {str(e)}"})

@app.route('/submit_results', methods=['POST'])
def submit_results():
    try:
        data = request.json
        
        patient_name = data.get('patientName')
        trial_data = data.get('trialData')
        difficulty = data.get('difficulty')
        duration = data.get('duration')
        
        # Check both possible field names (for backward compatibility)
        board_display_time = data.get('boardDisplayTime')
        if board_display_time is None:
            board_display_time = data.get('hideTime')  # Use the old name as fallback        

        # Map difficulty to display names if needed
        
        
        if difficulty.lower() == "medium":
            display_difficulty = "Easy"
        elif difficulty.lower() == "hard":
            display_difficulty = "Medium"
        elif difficulty.lower() == "very hard":
            display_difficulty = "Hard"
        else:
            display_difficulty = "Easy"

        # Validate required fields
        if not all([patient_name, trial_data, difficulty, board_display_time]):
            safe_log('error', f"Missing required fields - boardDisplayTime: {board_display_time}")
            return jsonify({
                "success": False,
                "message": "Missing required fields"
            }), 400

        # Calculate IES from trial data
        overall_ies, ies1, ies2, ies3, focus_drift, focus_stability = calculate_ies(
            trial_data, 
            duration=duration  # Pass duration to calculate_ies
        )
        
        # Check if we have insufficient trials
        if overall_ies == 999999:
            return jsonify({
                "success": False,
                "message": "Insufficient trials: At least 5 successful trials are required",
                "required": 5,
                "successful": sum(1 for trial in trial_data if trial.get('success') == 1)
            }), 400

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
            ['Overall IES Score', overall_ies],
            ['IES1 (First 60s)', ies1],
            ['IES2 (Second 60s)', ies2],
            ['IES3 (Last 60s)', ies3],
            ['Focus Drift', focus_drift],
            ['Focus Stability', focus_stability],
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
            current_ies=overall_ies,
            current_board_time=board_display_time,
            current_drift=focus_drift,
            current_stability=focus_stability
        )
        
        # 4. Get the updated leaderboard data to return
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range="Leaderboard!A1:O1000"
            ).execute()
            
            leaderboard_data = result.get('values', [])
            
            # Format leaderboard data for response
            formatted_leaderboard = format_leaderboard_data(leaderboard_data)
            
            # Return the leaderboard data with the results
            return jsonify({
                "success": True, 
                "ies": overall_ies,
                "ies1": ies1,
                "ies2": ies2,
                "ies3": ies3,
                "focus_drift": focus_drift,
                "focus_stability": focus_stability,
                "leaderboard": formatted_leaderboard  # Include the leaderboard directly in the response
            })
        except Exception as e:
            safe_log('error', f"Error getting updated leaderboard: {str(e)}")
            # Still return success for the submission, even if leaderboard fetch failed
            return jsonify({"success": True, "ies": overall_ies, "ies1": ies1, "ies2": ies2, "ies3": ies3, "focus_drift": focus_drift, "focus_stability": focus_stability})
        
    except Exception as e:
        safe_log('error', f"Error submitting results: {str(e)}")
        return jsonify({"success": False, "message": "Error submitting results"}), 500
        
def format_leaderboard_data(leaderboard_data):
    if len(leaderboard_data) <= 2:  # Only header rows or empty
        safe_log('warning', "Leaderboard data has only headers or is empty")
        return {"easy": [], "medium": [], "hard": []}

    formatted_data = {
        'easy': [],
        'medium': [],
        'hard': []
    }

    for i, row in enumerate(leaderboard_data[2:]):  # Skip first two header rows
        try:
            # Easy
            if len(row) >= 5 and row[0] and row[0] != "Rank":
                formatted_data['easy'].append({
                    'rank': row[0],
                    'name': row[1],
                    'score': row[2],
                    'drift': row[3],
                    'stability': row[4]
                })
            # Medium
            if len(row) >= 10 and row[5] and row[5] != "Rank":
                formatted_data['medium'].append({
                    'rank': row[5],
                    'name': row[6],
                    'score': row[7],
                    'drift': row[8],
                    'stability': row[9]
                })
            # Hard
            if len(row) >= 15 and row[10] and row[10] != "Rank":
                formatted_data['hard'].append({
                    'rank': row[10],
                    'name': row[11],
                    'score': row[12],
                    'drift': row[13],
                    'stability': row[14]
                })
        except Exception as e:
            safe_log('warning', f"Skipping invalid leaderboard row {i+3}: {row}, error: {str(e)}")
            continue

    safe_log('info', f"Formatted leaderboard entries - Easy: {len(formatted_data['easy'])}, Medium: {len(formatted_data['medium'])}, Hard: {len(formatted_data['hard'])}")
    return formatted_data

def calculate_ies(trial_data, duration):
    """
    Calculate Inverse Efficiency Scores (IES) from trial data.
    IES = median response time / accuracy
    
    Returns:
    - Overall IES
    - IES1: First 60 seconds
    - IES2: Second 60 seconds
    - IES3: Last 60 seconds
    - Focus Drift
    - Focus Stability
    
    Includes:
    - Minimum trial threshold (require at least 5 successful trials)
    - Smoothing factor to prevent explosion when accuracy approaches 0
    """
    if not trial_data:
        return 999999, 999999, 999999, 999999, 0, 0
    
    # Calculate accuracy (proportion of successful trials)
    total_trials = len(trial_data)
    successful_trials = sum(1 for trial in trial_data if trial.get('success') == 1)
    
    # Check minimum trial threshold
    if successful_trials < 5:
        return 999999, 999999, 999999, 999999, 0, 0
    
    # Calculate overall IES
    def calculate_ies_for_trials(trials):
        if not trials:
            return 999999
        
        successful_trials = sum(1 for trial in trials if trial.get('success') == 1)
        total_trials = len(trials)
        if successful_trials < 1:  # Need at least one successful trial
            return 999999
            
        accuracy = successful_trials / total_trials

        # Get all response times for successful trials
        response_times = [trial.get('responseTime', 0) for trial in trials if trial.get('success') == 1]
        
        # Sort response times
        sorted_times = sorted(response_times)
        
        n = len(sorted_times)
        
        if n % 2 == 1:
            median_response_time = sorted_times[n // 2]
        else:
            median_response_time = (sorted_times[n // 2 - 1] + sorted_times[n // 2]) / 2
        
        ies = median_response_time / accuracy if accuracy > 0 else 999999
        return round(ies, 2) if ies is not None else 999999
    
    # Split trials into time intervals
    trials_by_interval = {
        'IES1': [],  # First 60 seconds
        'IES2': [],  # Second 60 seconds
        'IES3': []   # Last 60 seconds
    }
    
    # Sort trials by trial time
    sorted_trials = sorted(trial_data, key=lambda x: x.get('trialTime', 0))
    
    # Calculate time intervals using game duration instead of last trial time
    total_time = duration  # Use the game duration directly
    interval_duration = total_time / 3
    
    for trial in sorted_trials:
        trial_time = trial.get('trialTime', 0)
        if trial_time < interval_duration:
            trials_by_interval['IES1'].append(trial)
        elif trial_time < 2 * interval_duration:
            trials_by_interval['IES2'].append(trial)
        else:
            trials_by_interval['IES3'].append(trial)
    
    # Calculate IES for each interval
    ies1 = calculate_ies_for_trials(trials_by_interval['IES1'])
    ies2 = calculate_ies_for_trials(trials_by_interval['IES2'])
    ies3 = calculate_ies_for_trials(trials_by_interval['IES3'])

    # Calculate overall IES only if all intervals have valid scores
    if ies1 is None or ies2 is None or ies3 is None:
        return None, None, None, None, 0, 0

    # Calculate IES as the geometric mean of all 3 (to penalize inactive people)
    overall_ies = round((ies1 * ies2 * ies3) ** (1/3), 2)

    # Calculate additional informative scores
    try:
        # Calculate drift as the difference between first and last IES (in seconds)
        # Positive value means improvement (became faster)
        # Negative value means decline (became slower)
        focus_drift = round(ies1 - ies3, 2)
        
        # Calculate mean of the three IES values
        mean_ies = (ies1 + ies2 + ies3) / 3
        
        # Calculate AVEDEV (average deviation from mean)
        # AVEDEV = (|IES1 - mean| + |IES2 - mean| + |IES3 - mean|) / 3
        ave_dev = (abs(ies1 - mean_ies) + abs(ies2 - mean_ies) + abs(ies3 - mean_ies)) / 3
        
        # Convert to percentage of mean IES for better readability
        # Lower AVEDEV means more consistent performance
        focus_stability = round(100 * (1 - (ave_dev / mean_ies)))
        
        # Ensure stability is between 0 and 100
        focus_stability = max(0, min(100, focus_stability))
    except (ValueError, ZeroDivisionError):
        # If any calculation fails, return 0
        focus_drift = 0
        focus_stability = 0
    
    return overall_ies, ies1, ies2, ies3, focus_drift, focus_stability

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)