# Chess Attack Recognition Task

A web-based cognitive task that tests your chess rapid vision.

## For Remote Users

To access the application remotely:

https://pontifex-chess.onrender.com

## Features

- Interactive chess board interface
- Configurable display time for positions
- Multiple difficulty levels
- Automatic result logging
- Progress tracking
- Downloadable results in CSV format

## Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)

## Data Storage

Results are stored locally in GSHEET format and downloadable CSV with the following information:
- Patient name
- Trial number
- Response time
- Success rate
- Position details
- Timestamps


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
