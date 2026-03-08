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

DATA_SHEET_HEADERS = [
    'Date', 'Time', 'Patient Name', 'Difficulty', 'Duration',
    'Board Display Time', 'Overall IES Score', 'IES1 (First 60s)',
    'IES2 (Second 60s)', 'IES3 (Last 60s)', 'Focus Drift', 'Focus Stability',
    'Overall Accuracy (%)', 'Overall Median RT (s)', 'Overall RT CV', 'Overall Lapse Rate (%)',
    'Accuracy 1st Third (%)', 'Accuracy 2nd Third (%)', 'Accuracy 3rd Third (%)',
    'Median RT 1st Third (s)', 'Median RT 2nd Third (s)', 'Median RT 3rd Third (s)',
    'RT CV 1st Third', 'RT CV 2nd Third', 'RT CV 3rd Third',
    'Lapse Rate 1st Third (%)', 'Lapse Rate 2nd Third (%)', 'Lapse Rate 3rd Third (%)',
    'RT Decrement (%)', 'Accuracy Decrement (%)', 'IES Decrement (%)',
    'RT Slope', 'Success Slope', 'IES Slope', 'Error Rate Slope',
    'Post-Error RT Delta (s)', 'Post-Error Accuracy Delta (pp)', 'RT-Success Correlation'
]

TRIALS_SHEET_HEADERS = [
    'Date', 'Time', 'Patient Name', 'Trial', 'Trial Time',
    'Attacking Piece', 'Attacking Position', 'Attacked Pieces',
    'Response Time', 'Success', 'Response Position'
]

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


def to_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def median(values):
    if not values:
        return None

    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2

    if len(sorted_values) % 2 == 1:
        return sorted_values[midpoint]

    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2


def mean(values):
    if not values:
        return None
    return sum(values) / len(values)


def standard_deviation(values):
    if not values:
        return None

    average = mean(values)
    variance = sum((value - average) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def round_metric(value, digits=2):
    if value is None or not math.isfinite(value):
        return ""
    return round(value, digits)


def percent(value, digits=2):
    if value is None or not math.isfinite(value):
        return ""
    return round(value * 100, digits)


def coefficient_of_variation(values):
    average = mean(values)
    if average in (None, 0):
        return None

    deviation = standard_deviation(values)
    if deviation is None:
        return None

    return deviation / average


def percent_change(first_value, last_value):
    if first_value in (None, 0) or last_value is None:
        return None
    return ((last_value - first_value) / first_value) * 100


def linear_slope(x_values, y_values):
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None

    x_mean = mean(x_values)
    y_mean = mean(y_values)
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    if denominator == 0:
        return None

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    return numerator / denominator


def pearson_correlation(x_values, y_values):
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None

    x_mean = mean(x_values)
    y_mean = mean(y_values)
    x_sd = standard_deviation(x_values)
    y_sd = standard_deviation(y_values)

    if x_sd in (None, 0) or y_sd in (None, 0):
        return None

    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values)) / len(x_values)
    return covariance / (x_sd * y_sd)


def calculate_ies_for_trials(trials):
    if not trials:
        return 999999

    successful_trials = [trial for trial in trials if trial['success'] == 1 and trial['response_time'] is not None]
    if not successful_trials:
        return 999999

    accuracy = len(successful_trials) / len(trials)
    median_response_time = median([trial['response_time'] for trial in successful_trials])

    if median_response_time is None or accuracy <= 0:
        return 999999

    return round(median_response_time / accuracy, 2)


def split_trials_by_time_thirds(trials, duration):
    sorted_trials = sorted(trials, key=lambda trial: trial['trial_time'])
    total_time = to_float(duration)

    if total_time in (None, 0):
        total_time = max((trial['trial_time'] for trial in sorted_trials), default=0)

    if total_time == 0:
        total_time = max(len(sorted_trials), 1)

    interval_duration = total_time / 3
    trial_groups = {'first': [], 'second': [], 'third': []}

    for trial in sorted_trials:
        trial_time = trial['trial_time']

        if trial_time < interval_duration:
            trial_groups['first'].append(trial)
        elif trial_time < 2 * interval_duration:
            trial_groups['second'].append(trial)
        else:
            trial_groups['third'].append(trial)

    return trial_groups


def summarize_block(trials, lapse_threshold):
    response_times = [trial['response_time'] for trial in trials if trial['response_time'] is not None]
    accuracy = (sum(trial['success'] for trial in trials) / len(trials)) if trials else None
    lapse_rate = None

    if response_times and lapse_threshold is not None:
        lapse_rate = sum(1 for response_time in response_times if response_time > lapse_threshold) / len(response_times)

    return {
        'accuracy': accuracy,
        'median_rt': median(response_times),
        'rt_cv': coefficient_of_variation(response_times),
        'lapse_rate': lapse_rate,
        'ies': calculate_ies_for_trials(trials)
    }


def calculate_session_metrics(trial_data, duration):
    if not trial_data:
        return None

    normalized_trials = []
    for index, trial in enumerate(trial_data, start=1):
        response_time = to_float(trial.get('responseTime'))
        success = 1 if str(trial.get('success', 0)) == '1' else 0
        trial_time = to_float(trial.get('trialTime'))
        if trial_time is None:
            trial_time = index

        normalized_trials.append({
            'trial_number': index,
            'trial_time': trial_time,
            'response_time': response_time,
            'success': success
        })

    successful_trials = sum(trial['success'] for trial in normalized_trials)
    if successful_trials < 5:
        return {
            'overall_ies': 999999,
            'ies1': 999999,
            'ies2': 999999,
            'ies3': 999999,
            'focus_drift': 0,
            'focus_stability': 0,
            'extra_metrics': {}
        }

    response_times = [trial['response_time'] for trial in normalized_trials if trial['response_time'] is not None]
    overall_accuracy = successful_trials / len(normalized_trials) if normalized_trials else None
    overall_median_rt = median(response_times)
    overall_rt_cv = coefficient_of_variation(response_times)
    response_time_sd = standard_deviation(response_times)
    lapse_threshold = None

    if overall_median_rt is not None and response_time_sd is not None:
        lapse_threshold = overall_median_rt + (2 * response_time_sd)

    overall_lapse_rate = None
    if response_times and lapse_threshold is not None:
        overall_lapse_rate = sum(1 for response_time in response_times if response_time > lapse_threshold) / len(response_times)

    blocks = split_trials_by_time_thirds(normalized_trials, duration)
    first_block = summarize_block(blocks['first'], lapse_threshold)
    second_block = summarize_block(blocks['second'], lapse_threshold)
    third_block = summarize_block(blocks['third'], lapse_threshold)

    ies1 = first_block['ies']
    ies2 = second_block['ies']
    ies3 = third_block['ies']
    overall_ies = round((ies1 * ies2 * ies3) ** (1 / 3), 2)

    try:
        focus_drift = round(ies1 - ies3, 2)
        mean_ies = (ies1 + ies2 + ies3) / 3
        average_deviation = (abs(ies1 - mean_ies) + abs(ies2 - mean_ies) + abs(ies3 - mean_ies)) / 3
        focus_stability = round(100 * (1 - (average_deviation / mean_ies)))
        focus_stability = max(0, min(100, focus_stability))
    except (ValueError, ZeroDivisionError):
        focus_drift = 0
        focus_stability = 0

    valid_ies_points = [
        (1, first_block['ies'] if first_block['ies'] != 999999 else None),
        (2, second_block['ies'] if second_block['ies'] != 999999 else None),
        (3, third_block['ies'] if third_block['ies'] != 999999 else None)
    ]
    ies_x_values = [point[0] for point in valid_ies_points if point[1] is not None]
    ies_y_values = [point[1] for point in valid_ies_points if point[1] is not None]

    post_error_trials = []
    post_correct_trials = []
    for previous_trial, current_trial in zip(normalized_trials, normalized_trials[1:]):
        if previous_trial['success'] == 0:
            post_error_trials.append(current_trial)
        else:
            post_correct_trials.append(current_trial)

    post_error_rt_delta = None
    post_error_accuracy_delta = None

    if post_error_trials and post_correct_trials:
        post_error_rt = mean([trial['response_time'] for trial in post_error_trials if trial['response_time'] is not None])
        post_correct_rt = mean([trial['response_time'] for trial in post_correct_trials if trial['response_time'] is not None])
        post_error_accuracy = mean([trial['success'] for trial in post_error_trials])
        post_correct_accuracy = mean([trial['success'] for trial in post_correct_trials])

        if post_error_rt is not None and post_correct_rt is not None:
            post_error_rt_delta = post_error_rt - post_correct_rt

        if post_error_accuracy is not None and post_correct_accuracy is not None:
            post_error_accuracy_delta = (post_error_accuracy - post_correct_accuracy) * 100

    trial_numbers = [trial['trial_number'] for trial in normalized_trials if trial['response_time'] is not None]
    rt_values = [trial['response_time'] for trial in normalized_trials if trial['response_time'] is not None]
    success_values = [trial['success'] for trial in normalized_trials]

    extra_metrics = {
        'overall_accuracy_pct': percent(overall_accuracy),
        'overall_median_rt': round_metric(overall_median_rt),
        'overall_rt_cv': round_metric(overall_rt_cv, 4),
        'overall_lapse_rate_pct': percent(overall_lapse_rate),
        'accuracy_first_pct': percent(first_block['accuracy']),
        'accuracy_second_pct': percent(second_block['accuracy']),
        'accuracy_third_pct': percent(third_block['accuracy']),
        'median_rt_first': round_metric(first_block['median_rt']),
        'median_rt_second': round_metric(second_block['median_rt']),
        'median_rt_third': round_metric(third_block['median_rt']),
        'rt_cv_first': round_metric(first_block['rt_cv'], 4),
        'rt_cv_second': round_metric(second_block['rt_cv'], 4),
        'rt_cv_third': round_metric(third_block['rt_cv'], 4),
        'lapse_rate_first_pct': percent(first_block['lapse_rate']),
        'lapse_rate_second_pct': percent(second_block['lapse_rate']),
        'lapse_rate_third_pct': percent(third_block['lapse_rate']),
        'rt_decrement_pct': round_metric(percent_change(first_block['median_rt'], third_block['median_rt'])),
        'accuracy_decrement_pct': round_metric(percent_change(first_block['accuracy'], third_block['accuracy'])),
        'ies_decrement_pct': round_metric(percent_change(ies_y_values[0], ies_y_values[-1])) if len(ies_y_values) >= 2 else "",
        'rt_slope': round_metric(linear_slope(trial_numbers, rt_values), 4),
        'success_slope': round_metric(linear_slope([trial['trial_number'] for trial in normalized_trials], success_values), 4),
        'ies_slope': round_metric(linear_slope(ies_x_values, ies_y_values), 4),
        'error_rate_slope': round_metric(linear_slope([trial['trial_number'] for trial in normalized_trials], [1 - success for success in success_values]), 4),
        'post_error_rt_delta': round_metric(post_error_rt_delta),
        'post_error_accuracy_delta_pp': round_metric(post_error_accuracy_delta),
        'rt_success_correlation': round_metric(
            pearson_correlation(rt_values, [trial['success'] for trial in normalized_trials if trial['response_time'] is not None]),
            4
        )
    }

    return {
        'overall_ies': overall_ies,
        'ies1': ies1,
        'ies2': ies2,
        'ies3': ies3,
        'focus_drift': focus_drift,
        'focus_stability': focus_stability,
        'extra_metrics': extra_metrics
    }


def calculate_ies(trial_data, duration):
    metrics = calculate_session_metrics(trial_data, duration)
    if not metrics:
        return 999999, 999999, 999999, 999999, 0, 0

    return (
        metrics['overall_ies'],
        metrics['ies1'],
        metrics['ies2'],
        metrics['ies3'],
        metrics['focus_drift'],
        metrics['focus_stability']
    )


def ensure_sheet_header(service, sheet_name, headers):
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        body={"values": [headers]}
    ).execute()

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

        # Collect existing entries from Data sheet
        data_sheet_name = "Data"
        if data_sheet_name in sheet_titles:
            try:
                # Get all data rows from Data sheet (skip header row)
                values = service.spreadsheets().values().get(
                    spreadsheetId=SHEET_ID, 
                    range=f"{data_sheet_name}!A2:L10000"  # Columns A-L, starting from row 2
                ).execute().get("values", [])
                
                # Data sheet columns: Date, Time, Patient Name, Difficulty, Duration, 
                # Board Display Time, Overall IES Score, IES1, IES2, IES3, Focus Drift, Focus Stability
                for row in values:
                    if len(row) < 7:  # Need at least Date, Time, Patient Name, Difficulty, Duration, Board Display Time, Overall IES Score
                        continue
                    
                    try:
                        patient_name = row[2] if len(row) > 2 else ""
                        difficulty = row[3] if len(row) > 3 else "N/A"
                        
                        # Skip current user's entry if it's being added separately
                        if current_user and patient_name == current_user:
                            continue
                        
                        # Extract IES
                        ies_str = row[6] if len(row) > 6 else "999999"
                        try:
                            ies = float(ies_str)
                        except (ValueError, TypeError):
                            ies = 999999
                        
                        # Extract board time
                        board_time_str = row[5] if len(row) > 5 else "0"
                        try:
                            board_time = float(board_time_str)
                        except (ValueError, TypeError):
                            board_time = 0
                        
                        # Extract drift and stability
                        drift_str = row[10] if len(row) > 10 else "0"
                        stability_str = row[11] if len(row) > 11 else "0"
                        try:
                            drift = float(drift_str)
                            stability = float(stability_str)
                        except (ValueError, TypeError):
                            drift = 0
                            stability = 0
                        
                        entry = [patient_name, ies, drift, stability, difficulty, board_time]
                        
                        # Add to appropriate difficulty list
                        if difficulty.lower() == "easy":
                            easy_entries.append(entry)
                        elif difficulty.lower() == "medium":
                            medium_entries.append(entry)
                        elif difficulty.lower() == "hard":
                            hard_entries.append(entry)
                    except Exception as e:
                        safe_log('warning', f"Skipping data row due to error: {e}")
                        continue
            except Exception as e:
                safe_log('warning', f"Error reading from Data sheet: {e}")
            
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
        # Each row contains entries from all three difficulties side by side
        for i in range(max_entries):
            row = []
            
            # Easy difficulty column (columns 0-4)
            if i < len(easy_entries):
                entry = easy_entries[i]
                row.extend([i + 1, entry[0], entry[1], entry[2], entry[3]])  # Rank, Name, IES, Drift, Stability
            else:
                row.extend(["", "", "", "", ""])
            
            # Medium difficulty column (columns 5-9)
            if i < len(medium_entries):
                entry = medium_entries[i]
                row.extend([i + 1, entry[0], entry[1], entry[2], entry[3]])  # Rank, Name, IES, Drift, Stability
            else:
                row.extend(["", "", "", "", ""])
            
            # Hard difficulty column (columns 10-14)
            if i < len(hard_entries):
                entry = hard_entries[i]
                row.extend([i + 1, entry[0], entry[1], entry[2], entry[3]])  # Rank, Name, IES, Drift, Stability
            else:
                row.extend(["", "", "", "", ""])
            
            leaderboard_data.append(row)
        
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


def get_sheet_title_case_insensitive(sheet_titles, target_title):
    """Return the sheet title matching target_title, case-insensitively."""
    target_lower = target_title.lower()
    return next((title for title in sheet_titles if title.lower() == target_lower), None)

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
        
        # Resolve leaderboard sheet name case-insensitively
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheet_titles = [s['properties']['title'] for s in spreadsheet['sheets']]
        leaderboard_sheet_name = get_sheet_title_case_insensitive(sheet_titles, "Leaderboard")

        if not leaderboard_sheet_name:
            safe_log('warning', "Leaderboard sheet not found")
            return jsonify({"success": True, "leaderboard": {"easy": [], "medium": [], "hard": []}})

        # Get leaderboard data
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{leaderboard_sheet_name}!A1:O1000"
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

        metrics = calculate_session_metrics(trial_data, duration)
        if not metrics:
            return jsonify({
                "success": False,
                "message": "Missing trial data"
            }), 400

        overall_ies = metrics['overall_ies']
        ies1 = metrics['ies1']
        ies2 = metrics['ies2']
        ies3 = metrics['ies3']
        focus_drift = metrics['focus_drift']
        focus_stability = metrics['focus_stability']
        extra_metrics = metrics['extra_metrics']
        
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
        
        # 1. Save data to single "Data" sheet (one row per submission)
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Get spreadsheet to check for existing sheets
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheet_titles = [s['properties']['title'] for s in spreadsheet['sheets']]
        
        data_sheet_name = "Data"
        trials_sheet_name = "Trials"
        
        # Create Data sheet if it doesn't exist
        if data_sheet_name not in sheet_titles:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={
                    "requests": [{
                        "addSheet": {
                            "properties": {"title": data_sheet_name}
                        }
                    }]
                }
            ).execute()
            ensure_sheet_header(service, data_sheet_name, DATA_SHEET_HEADERS)
        else:
            ensure_sheet_header(service, data_sheet_name, DATA_SHEET_HEADERS)
        
        # Create Trials sheet if it doesn't exist
        if trials_sheet_name not in sheet_titles:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={
                    "requests": [{
                        "addSheet": {
                            "properties": {"title": trials_sheet_name}
                        }
                    }]
                }
            ).execute()
            ensure_sheet_header(service, trials_sheet_name, TRIALS_SHEET_HEADERS)
        else:
            ensure_sheet_header(service, trials_sheet_name, TRIALS_SHEET_HEADERS)
        
        # 2. Append summary data row to Data sheet
        data_row = [
            current_date,
            current_time,
            patient_name,
            display_difficulty,
            duration,
            board_display_time,
            overall_ies,
            ies1,
            ies2,
            ies3,
            focus_drift,
            focus_stability,
            extra_metrics.get('overall_accuracy_pct', ''),
            extra_metrics.get('overall_median_rt', ''),
            extra_metrics.get('overall_rt_cv', ''),
            extra_metrics.get('overall_lapse_rate_pct', ''),
            extra_metrics.get('accuracy_first_pct', ''),
            extra_metrics.get('accuracy_second_pct', ''),
            extra_metrics.get('accuracy_third_pct', ''),
            extra_metrics.get('median_rt_first', ''),
            extra_metrics.get('median_rt_second', ''),
            extra_metrics.get('median_rt_third', ''),
            extra_metrics.get('rt_cv_first', ''),
            extra_metrics.get('rt_cv_second', ''),
            extra_metrics.get('rt_cv_third', ''),
            extra_metrics.get('lapse_rate_first_pct', ''),
            extra_metrics.get('lapse_rate_second_pct', ''),
            extra_metrics.get('lapse_rate_third_pct', ''),
            extra_metrics.get('rt_decrement_pct', ''),
            extra_metrics.get('accuracy_decrement_pct', ''),
            extra_metrics.get('ies_decrement_pct', ''),
            extra_metrics.get('rt_slope', ''),
            extra_metrics.get('success_slope', ''),
            extra_metrics.get('ies_slope', ''),
            extra_metrics.get('error_rate_slope', ''),
            extra_metrics.get('post_error_rt_delta', ''),
            extra_metrics.get('post_error_accuracy_delta_pp', ''),
            extra_metrics.get('rt_success_correlation', '')
        ]
        
        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"{data_sheet_name}!A:A",
            valueInputOption="RAW",
            body={"values": [data_row]}
        ).execute()
        
        # 3. Append trial data rows to Trials sheet
        trial_rows = []
        for trial in trial_data:
            trial_rows.append([
                current_date,
                current_time,
                patient_name,
                trial.get('trial', ''),
                trial.get('trialTime', ''),
                trial.get('attackingPiece', ''),
                trial.get('attackingPosition', ''),
                trial.get('attackedPieces', ''),
                trial.get('responseTime', ''),
                trial.get('success', ''),
                trial.get('responsePosition', '')
            ])
        
        if trial_rows:
            service.spreadsheets().values().append(
                spreadsheetId=SHEET_ID,
                range=f"{trials_sheet_name}!A:A",
                valueInputOption="RAW",
                body={"values": trial_rows}
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

    for i, raw_row in enumerate(leaderboard_data[2:]):  # Skip first two header rows
        try:
            # Google Sheets can omit trailing empty cells; pad to expected 15 columns.
            row = list(raw_row) + [""] * max(0, 15 - len(raw_row))

            # Skip accidental repeated header row content.
            if row[0] == "Rank" and row[5] == "Rank" and row[10] == "Rank":
                continue

            # Easy column (columns 0-4: Rank, Name, IES, Drift, Stability)
            if row[1] and row[1] != "Name":
                formatted_data['easy'].append({
                    'rank': row[0],
                    'name': row[1],
                    'score': row[2],
                    'drift': row[3],
                    'stability': row[4]
                })
            # Medium column (columns 5-9: Rank, Name, IES, Drift, Stability)
            if row[6] and row[6] != "Name":
                formatted_data['medium'].append({
                    'rank': row[5],
                    'name': row[6],
                    'score': row[7],
                    'drift': row[8],
                    'stability': row[9]
                })
            # Hard column (columns 10-14: Rank, Name, IES, Drift, Stability)
            if row[11] and row[11] != "Name":
                formatted_data['hard'].append({
                    'rank': row[10],
                    'name': row[11],
                    'score': row[12],
                    'drift': row[13],
                    'stability': row[14]
                })
        except (IndexError, ValueError) as e:
            safe_log('warning', f"Skipping invalid leaderboard row {i+1}: {raw_row}, error: {str(e)}")
    
    safe_log('info', f"Formatted leaderboard entries - Easy: {len(formatted_data['easy'])}, Medium: {len(formatted_data['medium'])}, Hard: {len(formatted_data['hard'])}")
    return formatted_data

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
