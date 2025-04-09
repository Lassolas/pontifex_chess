# Chess Attack Recognition Task

A web-based cognitive task that tests chess piece attack recognition.

## For Remote Users

To access the application remotely:

1. Ask the host (person running the server) for their public IP address
2. Once they have the server running, access the application through your web browser using:
   ```
   http://[HOST_IP]:5000
   ```
   Replace [HOST_IP] with the IP address provided by the host.

## For Hosts (Server Setup)

To make the application available for remote users:

1. Install Python 3.7 or higher if not already installed
2. Open a terminal and navigate to the application directory:
   ```bash
   cd path/to/pontifex_chess_online
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the server:
   ```bash
   python app.py
   ```

5. Find your public IP address:
   - On macOS/Linux: Visit https://ifconfig.me in your browser
   - On Windows: Visit https://ifconfig.me in your browser
   
6. Share your public IP address with remote users

Important Security Notes:
- Make sure port 5000 is open on your network/firewall
- The application runs without encryption (HTTP), so don't use it for sensitive data
- Consider using a VPN or SSH tunnel for additional security

## Features

- Interactive chess board interface
- Configurable display time for positions
- Multiple difficulty levels
- Automatic result logging
- Progress tracking
- Downloadable results in CSV format

## Requirements

- Python 3.7+
- Flask 3.0.2
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Data Storage

Results are stored locally in CSV format with the following information:
- Patient name
- Trial number
- Response time
- Success rate
- Position details
- Timestamps

## Troubleshooting

If you cannot connect:
1. Check if the server is running (terminal should show "Running on http://0.0.0.0:5000")
2. Verify the IP address and port
3. Check your firewall settings
4. Ensure your router allows port 5000

For any issues, please check the terminal output for error messages.

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your web browser and navigate to:
```
http://localhost:5000
```

## Directory Structure

```
pontifex_chess_online/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── static/            # Static files
│   ├── css/
│   │   └── style.css  # Stylesheet
│   └── js/
│       ├── chess.js   # Chess game logic
│       └── game.js    # Game interface logic
└── templates/
    └── index.html     # Main HTML template
```

## Usage

1. Enter your name on the initial screen
2. Select difficulty level and board display time
3. Click "Begin Test" to start
4. For each trial:
   - Identify the attacking piece shown
   - Click on a piece that can be captured by the attacking piece
   - Receive immediate feedback on your response
5. View your results at the end of the test
6. Download the CSV file containing detailed trial data

## Data Collection

The application logs the following data for each trial:
- Trial number
- Trial time
- Attacking piece and its position
- Attacked pieces and their positions
- Response time
- Success (1 for correct, 0 for incorrect)
- Response position

## License

This project is open source and available under the MIT License. 