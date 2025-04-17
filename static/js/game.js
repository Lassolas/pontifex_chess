class GameUI {
    constructor() {
        this.game = new ChessGame();
        this.currentScreen = 'name-input';
        this.patientName = '';
        this.timer = null;
        this.countdownTimer = null;
        this.remainingTime = this.game.duration;
        this.showBoard = false;
        this.showAttackingPiece = false;
        this.boardDisplayTime = null;
        this.trialStartTime = null;  // Track the start time of the trial
        this.startTime = null;  // Store the start time of the experience
        
        this.screens = {
            'name-input': document.getElementById('name-input-screen'),
            'intro': document.getElementById('intro-screen'),
            'countdown': document.getElementById('countdown-screen'),
            'game': document.getElementById('game-screen'),
            'results': document.getElementById('results-screen')
        };

        this.nameInput = document.getElementById('patient-name');
        this.startButton = document.getElementById('start-button');
        
        // Mode buttons
        this.trainingBtn = document.getElementById('training-btn');
        this.easyBtn = document.getElementById('easy-btn');
        this.mediumBtn = document.getElementById('medium-btn');
        this.hardBtn = document.getElementById('hard-btn');
        
        this.downloadButton = document.getElementById('download-button');
        this.restartButton = document.getElementById('restart-button');

        this.difficultyButtons = document.querySelectorAll('.difficulty-btn');
        this.durationButtons = document.querySelectorAll('.duration-btn');
        this.timeSlider = document.getElementById('time-slider');
        this.timeValue = document.getElementById('time-value');

        this.countdownText = document.getElementById('countdown-text');

        this.chessboard = document.getElementById('chessboard');
        this.attackingPieceContainer = document.getElementById('attacking-piece');
        this.instructionText = document.getElementById('instruction-text');
        this.timerDisplay = document.getElementById('timer');
        this.trialCount = document.getElementById('trial-count');

        this.resultsSummary = document.getElementById('results-summary');

        this.initializeEventListeners();
        this.loadImages();
    }

    async loadImages() {
        this.images = {};
        const pieces = ['bP', 'bN', 'bB', 'bR', 'bQ', 'bK', 'wP', 'wN', 'wB', 'wR', 'wQ', 'wK'];
        
        for (const piece of pieces) {
            try {
                const response = await fetch(`/static/assets/${piece}.svg`);
                const svgText = await response.text();
                this.images[piece] = svgText;
            } catch (error) {
                console.error(`Error loading image for ${piece}:`, error);
            }
        }
    }

    initializeEventListeners() {
        // Name input screen
        this.startButton.addEventListener('click', (e) => {
            e.preventDefault();
            const name = this.nameInput.value.trim();
            if (name) {
                this.patientName = name;
                this.showScreen('intro');
            } else {
                alert('Please enter your name to continue.');
            }
        });
        
        // Add touch event listener for mobile devices
        this.startButton.addEventListener('touchend', (e) => {
            e.preventDefault();
            const name = this.nameInput.value.trim();
            if (name) {
                this.patientName = name;
                this.showScreen('intro');
            } else {
                alert('Please enter your name to continue.');
            }
        });
        
        // Mode button event listeners
        this.trainingBtn.addEventListener('click', () => this.handleModeSelection('training'));
        this.easyBtn.addEventListener('click', () => this.handleModeSelection('easy'));
        this.mediumBtn.addEventListener('click', () => this.handleModeSelection('medium'));
        this.hardBtn.addEventListener('click', () => this.handleModeSelection('hard'));
        
        // Game screen
        this.chessboard.addEventListener('click', (e) => this.handleChessboardClick(e));
        
        // Results screen
        this.downloadButton.addEventListener('click', () => this.downloadResults());
        
        // Only add event listener if the button exists
        if (this.restartButton) {
            this.restartButton.addEventListener('click', () => this.restartGame());
        }
    }

    showScreen(screenName) {
        Object.values(this.screens).forEach(screen => screen.style.display = 'none');
        this.screens[screenName].style.display = 'block';
        this.currentScreen = screenName;
    }

    handleStartClick() {
        const name = this.nameInput.value.trim();
        if (name) {
            this.patientName = name;
            this.showScreen('intro');
        } else {
            alert('Please enter your name to continue.');
        }
    }
    
    // Add a new method for handling mode selection
    handleModeSelection(mode) {
        // Set game configuration based on selected mode
        switch (mode) {
            case 'training':
                this.game.difficulty = 'Easy';
                this.game.boardDisplayTime = 5;
                this.game.duration = 60; // 1 minute
                this.game.saveResults = false; // Don't save training results
                break;
            case 'easy':
                this.game.difficulty = 'Easy';
                this.game.boardDisplayTime = 5;
                this.game.duration = 10; // 3 minutes
                this.game.saveResults = true;
                break;
            case 'medium':
                this.game.difficulty = 'Hard';
                this.game.boardDisplayTime = 3;
                this.game.duration = 180; // 3 minutes
                this.game.saveResults = true;
                break;
            case 'hard':
                this.game.difficulty = 'Very Hard';
                this.game.boardDisplayTime = 1;
                this.game.duration = 180; // 3 minutes
                this.game.saveResults = true;
                break;
        }
        
        // Start countdown
        this.startCountdown();
    }

    startCountdown() {
        this.showScreen('countdown');
        let count = 3;
        this.countdownText.textContent = count;

        this.countdownTimer = setInterval(() => {
            count--;
            this.countdownText.textContent = count;
            if (count <= 0) {
                clearInterval(this.countdownTimer);
                this.startGame();
            }
        }, 1000);
    }

    startGame() {
        this.showScreen('game');
        this.game.startTime = Date.now();
        this.remainingTime = this.game.duration;
        this.updateTimer();
        this.startTimer();
        this.startTime = Date.now(); // Set up the start time of the experience
        this.startNewTrial();
    }

    startNewTrial() {
        this.game.generatePosition();
        this.showBoard = true;
        this.showAttackingPiece = false;
        this.drawChessboard();
        this.game.hasResponded = false;
        this.trialCount.textContent = `Trial ${this.game.currentTrial + 1}`;

        // Clear the attacking piece display
        this.attackingPieceContainer.innerHTML = '';
        this.instructionText.textContent = '';
        // Log the trial time when the attacking piece is shown
        this.game.trialTime = Date.now(); // Set trial time here
        this.game.trialStartTime = Date.now(); // Set trial time here
        this.trialStartTime = Date.now(); // Set trial time here
        
        
        // Hide board after specified time
        setTimeout(() => {
            this.showBoard = false;
            this.showAttackingPiece = true;
            this.drawChessboard();
            this.updateAttackingPiece();
            
            // Store the time when the attacking piece is shown
            this.game.attackingPieceShownTime = Date.now();
        
        }, this.game.boardDisplayTime * 1000);
    }

    startTimer() {
        this.timer = setInterval(() => {
            this.remainingTime--;
            this.updateTimer();
            if (this.remainingTime <= 0) {
                this.endGame();
            }
        }, 1000);
    }

    updateTimer() {
        const minutes = Math.floor(this.remainingTime / 60);
        const seconds = this.remainingTime % 60;
        this.timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    drawChessboard() {
        this.chessboard.innerHTML = '';
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const square = document.createElement('div');
                square.className = `square ${(row + col) % 2 === 0 ? 'white' : 'black'}`;
                square.dataset.row = row;
                square.dataset.col = col;

                if (this.showBoard) {
                    const piece = this.game.board[row][col];
                    if (piece) {
                        const pieceElement = document.createElement('div');
                        pieceElement.className = 'piece';
                        pieceElement.innerHTML = this.images[piece];
                        square.appendChild(pieceElement);
                    }
                }

                this.chessboard.appendChild(square);
            }
        }
    }

    updateAttackingPiece() {
        if (this.showAttackingPiece) {
            const [piece, row, col] = this.game.attackingPiece;
            this.attackingPieceContainer.innerHTML = '';
            const pieceElement = document.createElement('div');
            pieceElement.className = 'piece';
            pieceElement.innerHTML = this.images[piece];
            this.attackingPieceContainer.appendChild(pieceElement);
            this.instructionText.textContent = `Click on a piece that ${piece[0] === 'w' ? 'White' : 'Black'} ${piece[1]} can capture`;
        }
    }

    handleChessboardClick(event) {
        if (!this.showAttackingPiece || this.game.hasResponded) return;

        const square = event.target.closest('.square');
        if (!square) return;

        const row = parseInt(square.dataset.row);
        const col = parseInt(square.dataset.col);
        const piece = this.game.board[row][col];

        // Highlight the clicked square
        square.classList.add('clicked');

        if (!this.game.attackingPieceShownTime || this.game.hasResponded) return;

        this.game.hasResponded = true;
        const responseTime = (Date.now() - this.game.attackingPieceShownTime) / 1000;  // Calculate response time based on when the piece was shown

        // Check if clicked square is in attacked squares
        const isCorrect = piece && this.game.attackedPieces.some(([r, c]) => r === row && c === col);

        // Log trial data with reaction time
        const responsePosition = `${String.fromCharCode(97 + col)}${8 - row}`;
        this.game.logTrialData(responseTime, isCorrect ? 1 : 0, responsePosition);
        this.game.currentTrial++;

        // Move to next trial after a short delay
        setTimeout(() => {
            this.startNewTrial();
        }, 100);
    }

    endGame() {
        clearInterval(this.timer);
        this.showScreen('results');

        // Calculate and display summary
        const totalTrials = this.game.trialData.length;
        const successfulTrials = this.game.trialData.filter(trial => trial.success === 1).length;
        const successRate = ((successfulTrials / totalTrials) * 100).toFixed(1);

    
        // Calculate average response time for successful trials (raw value, unrounded)
        const rawAverageRT = this.game.trialData
            .filter(trial => trial.success === 1)
            .reduce((sum, trial) => sum + trial.responseTime, 0) / successfulTrials;

        // Calculate IES using unrounded averageRT
        const accuracy = successfulTrials / totalTrials || 1; // Avoid division by zero
        const rawIES = rawAverageRT / accuracy;

        // Display rounded values
        const averageRT = rawAverageRT.toFixed(2);
        const IES = rawIES.toFixed(2);
        
        this.resultsSummary.innerHTML = `
            <p>Total Trials: ${totalTrials}</p>
            <p>Successful Trials: ${successfulTrials}</p>
            <p>Success Rate: ${successRate}%</p>
            <p>Average Response Time: ${averageRT}s</p>
            <p>IES: ${IES} seconds</p>
        `;

        // Store IES for leaderboard comparison
        this.game.IES = IES;

        // Automatically submit results to server
        this.submitResults(IES);
        
    }
    
    restartGame() {
        this.showScreen('name-input');
        this.game = new ChessGame(); // Reset the game
        this.patientName = '';
        this.nameInput.value = '';
    }

    async fetchLeaderboard() {
        console.log('Starting fetchLeaderboard');
        const leaderboardLoading = document.getElementById('leaderboard-loading');
        leaderboardLoading.textContent = 'Loading leaderboard...';
        
        console.log('Fetching leaderboard data...');
        
        try {
            console.log('Before fetch request');
            const response = await fetch('/get_leaderboard');
            console.log('Fetch response status:', response.status);
            
            const responseText = await response.text();
            console.log('Raw response text:', responseText);
            
            // Try to parse as JSON (this might fail if the response isn't valid JSON)
            let data;
            try {
                data = JSON.parse(responseText);
                console.log('Parsed JSON data:', data);
            } catch (parseError) {
                console.error('Error parsing JSON:', parseError);
                leaderboardLoading.textContent = 'Error parsing leaderboard data';
                return;
            }
            // After parsing the JSON
            console.log('Response object type:', typeof data);
            console.log('Response keys:', Object.keys(data));
            
            if (data.success) {
                console.log('Success is true');
                console.log('Leaderboard present:', !!data.leaderboard);
                console.log('Leaderboard type:', typeof data.leaderboard);
            } else {
                console.log('Success is false, message:', data.message);
            }
            console.log('Response success:', data.success);
            console.log('Has leaderboard property:', data.hasOwnProperty('leaderboard'));
            
            if (data.success && data.leaderboard) {
                console.log('Leaderboard data structure:', Object.keys(data.leaderboard));
                console.log('Easy entries:', data.leaderboard.easy?.length || 0);
                console.log('Medium entries:', data.leaderboard.medium?.length || 0);
                console.log('Hard entries:', data.leaderboard.hard?.length || 0);
                
                this.displayLeaderboard(data.leaderboard);
            } else {
                console.warn('Leaderboard data not available or empty:', data);
                leaderboardLoading.textContent = 'No leaderboard data available.';
            }
        } catch (error) {
            console.error('Error fetching leaderboard:', error);
            leaderboardLoading.textContent = 'Failed to load leaderboard.';
        }
    }

    async submitResults(IES) {
        // Skip submission for training mode
        if (!this.game.saveResults) {
            console.log('Training mode - results not saved');
            // Still show the leaderboard
            this.fetchLeaderboard();
            return;
        }
        
        try {
            // Log values before sending
            console.log('Submitting with boardDisplayTime:', this.game.boardDisplayTime);
            
            const response = await fetch('/submit_results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    patientName: this.patientName,
                    trialData: this.game.trialData,
                    difficulty: this.game.difficulty,
                    duration: this.game.duration,
                    boardDisplayTime: this.game.boardDisplayTime,  // Use the new name consistently
                    IES: IES
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // If leaderboard data is included in the response, use it
                if (data.leaderboard) {
                    console.log('Leaderboard received with submission response');
                    this.displayLeaderboard(data.leaderboard);
                } else {
                    // Otherwise fetch it separately (backwards compatibility)
                    this.fetchLeaderboard();
                }
            } else {
                console.error('Error submitting results:', data.message);
            }
            
        } catch (error) {
            console.error('Error submitting results:', error);
            // Try to fetch leaderboard anyway
            this.fetchLeaderboard();
        }
    }
    // New function to display leaderboard data
    // In game.js, update the displayLeaderboard function:
    displayLeaderboard(leaderboardData) {
        console.log('displayLeaderboard called with data:', leaderboardData);
        
        // Check data validity
        const isValid = leaderboardData && 
            typeof leaderboardData === 'object' &&
            (Array.isArray(leaderboardData.easy) || 
            Array.isArray(leaderboardData.medium) || 
            Array.isArray(leaderboardData.hard));
        
        console.log('Is leaderboard data valid?', isValid);
        
        if (!isValid) {
            console.error('Invalid leaderboard data structure:', leaderboardData);
            document.getElementById('leaderboard-loading').textContent = 
                'Error: Received invalid leaderboard data format';
            return;
        }
        const leaderboardLoading = document.getElementById('leaderboard-loading');
        const leaderboardTables = document.getElementById('leaderboard-tables');
        const leaderboardEasy = document.getElementById('leaderboard-easy');
        const leaderboardMedium = document.getElementById('leaderboard-medium');
        const leaderboardHard = document.getElementById('leaderboard-hard');
        
        if (leaderboardData && 
            (leaderboardData.easy?.length > 0 || 
            leaderboardData.medium?.length > 0 || 
            leaderboardData.hard?.length > 0)) {
            
            // Show table, hide loading
            leaderboardTables.style.display = 'block';
            leaderboardLoading.style.display = 'none';
            
            // Clear previous entries
            leaderboardEasy.innerHTML = '';
            leaderboardMedium.innerHTML = '';
            leaderboardHard.innerHTML = '';
            
            // Helper function to display rows
            const displayRows = (entries, container, difficulty) => {
                const currentUserName = this.patientName;
                const currentEntry = entries.find(e => e.name === currentUserName);
                
                // Display top 10 entries
                entries
                    .slice(0, 10)
                    .forEach(entry => {
                        const row = document.createElement('tr');
                        row.className = entry.name === currentUserName ? 'current-user' : '';
                        row.innerHTML = `
                            <td>${entry.rank}</td>
                            <td>${entry.name}</td>
                            <td>${entry.score}</td>
                        `;
                        container.appendChild(row);
                    });
                
                // In the displayRows function
                if (currentEntry && parseInt(currentEntry.rank) > 10) {
                    const separator = document.createElement('tr');
                    separator.className = 'current-user';  // Use current-user class for highlighting
                    separator.innerHTML = `
                        <td colspan="3" style="text-align: center;">
                            <span style="font-weight: bold;">${currentEntry.name}</span> - Rank: ${currentEntry.rank} - IES: ${currentEntry.score}
                        </td>
                    `;
                    container.appendChild(separator);
                }
            };
            
            // Display for each difficulty
            displayRows(leaderboardData.easy, leaderboardEasy, 'Easy');
            displayRows(leaderboardData.medium, leaderboardMedium, 'Medium');
            displayRows(leaderboardData.hard, leaderboardHard, 'Hard');
        } else {
            // No data available
            leaderboardTables.style.display = 'none';
            leaderboardLoading.style.display = 'block';
            leaderboardLoading.textContent = 'No leaderboard data available.';
        }
    }

    downloadResults() {
        // Map difficulty values to button names
        let displayDifficulty = "Easy";
        if (this.game.difficulty === "Hard") {
            displayDifficulty = "Medium";
        } else if (this.game.difficulty === "Very Hard") {
            displayDifficulty = "Hard";
        }
        
        const csvContent = [
            ['Difficulty', displayDifficulty],  // Header for Difficulty with mapped name
            ['Test Duration', this.game.duration],  // Header for Test Duration
            ['Board Display Time', this.game.boardDisplayTime],  // Header for Board Display Time
            ['IES', this.game.IES],  // Header for IES
            ['Trial', 'Trial Time', 'Attacking Piece', 'Attacking Position', 'Attacked Pieces', 'Response Time', 'Success', 'Response Position'],
            ...this.game.trialData.map(trial => [
                trial.trial,
                trial.trialTime,
                trial.attackingPiece,
                trial.attackingPosition,
                trial.attackedPieces,
                trial.responseTime,
                trial.success,
                trial.responsePosition
            ])
        ].map(row => row.join(',')).join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.patientName}_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
}

// Initialize the game when the page loads
window.addEventListener('load', () => {
    new GameUI();
});