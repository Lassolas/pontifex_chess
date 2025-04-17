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
        this.beginButton = document.getElementById('begin-button');
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
        this.startButton.addEventListener('click', () => this.handleNameInput());

        // Intro screen
        this.difficultyButtons.forEach(btn => {
            btn.addEventListener('click', () => this.handleDifficultySelection(btn));
        });
        this.durationButtons.forEach(btn => {
            btn.addEventListener('click', () => this.handleDurationSelection(btn));
        });
        this.timeSlider.addEventListener('input', () => this.handleTimeSlider());
        this.beginButton.addEventListener('click', () => this.startCountdown());

        // Game screen
        this.chessboard.addEventListener('click', (e) => this.handleChessboardClick(e));

        // Results screen
        this.downloadButton.addEventListener('click', () => this.downloadResults());
    }

    showScreen(screenName) {
        Object.values(this.screens).forEach(screen => screen.style.display = 'none');
        this.screens[screenName].style.display = 'block';
        this.currentScreen = screenName;
    }

    handleNameInput() {
        this.patientName = this.nameInput.value.trim();
        if (this.patientName) {
            this.showScreen('intro');
        }
    }

    handleDifficultySelection(button) {
        this.difficultyButtons.forEach(btn => btn.classList.remove('selected'));
        button.classList.add('selected');
        this.game.difficulty = button.textContent;
    }

    handleDurationSelection(button) {
        this.durationButtons.forEach(btn => btn.classList.remove('selected'));
        button.classList.add('selected');
        // Extract the duration option from the button text (e.g., "Short (1 min)" -> "Short")
        const durationOption = button.textContent.split(' ')[0];
        this.game.setDuration(durationOption);
    }

    handleTimeSlider() {
        this.game.hideTime = parseFloat(this.timeSlider.value);
        this.timeValue.textContent = `${this.game.hideTime.toFixed(1)}s`;
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
        
        }, this.game.hideTime * 1000);
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

    async fetchLeaderboard() {
        const leaderboardLoading = document.getElementById('leaderboard-loading');
    
        try {
            const response = await fetch('/get_leaderboard');
            const data = await response.json();
            
            if (data.success && data.leaderboard.length > 0) {
                this.displayLeaderboard(data.leaderboard);
            } else {
                leaderboardLoading.textContent = 'No leaderboard data available.';
            }
        } catch (error) {
            console.error('Error fetching leaderboard:', error);
            leaderboardLoading.textContent = 'Failed to load leaderboard.';
        }
    }

    async submitResults(IES) {
        try {
            const response = await fetch('/submit_results', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    patientName: this.patientName,
                    trialData: this.game.trialData,
                    difficulty: this.game.difficulty,
                    testDuration: this.game.duration,
                    boardDisplayTime: this.game.hideTime,
                    IES: IES
                })
            });

            const data = await response.json();
            console.log('Results submitted:', data);
            
            // If the response includes leaderboard data, display it
            if (data.leaderboard) {
                this.displayLeaderboard(data.leaderboard);
            } else {
                // Fallback to fetching leaderboard separately if not included
                this.fetchLeaderboard();
            }
        } catch (error) {
            console.error('Error submitting results:', error);
        }
    }
    // New function to display leaderboard data
    displayLeaderboard(leaderboardData) {
        const leaderboardLoading = document.getElementById('leaderboard-loading');
        const leaderboardTable = document.getElementById('leaderboard-table');
        const leaderboardBody = document.getElementById('leaderboard-body');
        
        if (leaderboardData && leaderboardData.length > 0) {
            // Clear previous entries
            leaderboardBody.innerHTML = '';
            
            // Add each leaderboard entry
            leaderboardData.forEach(entry => {
                const row = document.createElement('tr');
                
                // Highlight current user
                if (entry.name === this.patientName) {
                    row.classList.add('current-user');
                }
                
                row.innerHTML = `
                    <td>${entry.rank}</td>
                    <td>${entry.name}</td>
                    <td>${entry.ies}</td>
                    <td>${entry.difficulty}</td>
                    <td>${entry.boardTime}s</td>
                `;
                
                leaderboardBody.appendChild(row);
            });
            
            // Show the table and hide loading message
            leaderboardLoading.style.display = 'none';
            leaderboardTable.style.display = 'table';
        } else {
            leaderboardLoading.textContent = 'No leaderboard data available.';
        }
    }
    downloadResults() {
        const csvContent = [
            ['Difficulty', this.game.difficulty],  // Header for Difficulty
            ['Test Duration', this.game.duration],  // Header for Test Duration
            ['Board Display Time', this.game.hideTime],  // Header for Board Display Time
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