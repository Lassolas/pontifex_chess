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
        this.isTrainingMode = false; // Add training mode flag
        
        console.log('GameUI initialized');
        console.log('Initial state:', {
            showBoard: this.showBoard,
            showAttackingPiece: this.showAttackingPiece,
            isTrainingMode: this.isTrainingMode
        });
        
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
        this.timerDisplay = document.getElementById('timer');
        this.trialCount = document.getElementById('trial-count');

        this.resultsSummary = document.getElementById('results-summary');
        this.leaderboardLoading = document.getElementById('leaderboard-loading');
        
        // Initialize leaderboard loading text
        if (this.leaderboardLoading) {
            this.leaderboardLoading.textContent = '';
        }

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

        // Restart button - reload the page instead of using our logic
        if (this.restartButton) {
            this.restartButton.addEventListener('click', () => {
                window.location.reload();
            });
        }

        // Mode buttons
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
            // Removed restartGame event listener
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
                this.isTrainingMode = true; // Set training mode flag
                break;
            case 'easy':
                this.game.difficulty = 'Medium';
                this.game.boardDisplayTime = 5;
                this.game.duration = 180; // 3 minutes
                this.game.saveResults = true;
                this.isTrainingMode = false; // Clear training mode flag
                break;
            case 'medium':
                this.game.difficulty = 'Hard';
                this.game.boardDisplayTime = 3;
                this.game.duration= 180; // 3 minutes
                this.game.saveResults = true;
                this.isTrainingMode = false; // Clear training mode flag
                break;
            case 'hard':
                this.game.difficulty = 'Very Hard';
                this.game.boardDisplayTime = 1;
                this.game.duration = 180; // 3 minutes
                this.game.saveResults = true;
                this.isTrainingMode = false; // Clear training mode flag
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
        
        // Increment trial counter
        this.game.currentTrial++;
        
        // Update trial count display
        this.trialCount.textContent = `Trial ${this.game.currentTrial}`;

        // Clear the attacking piece display
        this.attackingPieceContainer.innerHTML = '';
        
        // Log the trial time when the attacking piece is shown
        this.game.trialTime = Date.now();
        this.game.trialStartTime = Date.now();
        this.trialStartTime = Date.now();
        
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
        console.log('drawChessboard called');
        console.log('Current state:', {
            showBoard: this.showBoard,
            isTrainingMode: this.isTrainingMode
        });

        // If we have existing squares, update them instead of recreating
        if (this.chessboard.children.length > 0) {
            console.log('Updating existing squares');
            // First, clear all pieces
            this.chessboard.querySelectorAll('.piece').forEach(piece => piece.remove());
            
            // Update pieces
            if (this.showBoard) {
                this.game.board.forEach((row, r) => {
                    row.forEach((piece, c) => {
                        if (piece) {
                            const square = this.chessboard.querySelector(`[data-row="${r}"][data-col="${c}"]`);
                            if (square) {
                                const pieceElement = document.createElement('div');
                                pieceElement.className = 'piece';
                                pieceElement.innerHTML = this.images[piece];
                                square.appendChild(pieceElement);
                            }
                        }
                    });
                });
            }
        } else {
            console.log('Creating new squares');
            // Create new squares only if none exist
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
        
        console.log('Chessboard drawn');
    }

    updateAttackingPiece() {
        if (this.showAttackingPiece) {
            const [piece, row, col] = this.game.attackingPiece;
            this.attackingPieceContainer.innerHTML = '';
            const pieceElement = document.createElement('div');
            pieceElement.className = 'piece';
            pieceElement.innerHTML = this.images[piece];
            this.attackingPieceContainer.appendChild(pieceElement);
        }
    }

    handleChessboardClick(event) {
        console.log('handleChessboardClick called');
        console.log('Event target:', event.target);
        console.log('Current state:', {
            showAttackingPiece: this.showAttackingPiece,
            hasResponded: this.game.hasResponded,
            isTrainingMode: this.isTrainingMode
        });

        if (!this.showAttackingPiece || this.game.hasResponded) {
            console.log('Early return - conditions not met');
            return;
        }

        const square = event.target.closest('.square');
        if (!square) {
            console.log('No square found in click event');
            return;
        }

        console.log('Square found:', square);
        
        const row = parseInt(square.dataset.row);
        const col = parseInt(square.dataset.col);
        const piece = this.game.board[row][col];

        if (!this.game.attackingPieceShownTime || this.game.hasResponded) {
            console.log('Early return - time conditions not met');
            return;
        }

        this.game.hasResponded = true;
        const responseTime = (Date.now() - this.game.attackingPieceShownTime) / 1000;

        // Check if clicked square is in attacked squares
        const isCorrect = piece && this.game.attackedPieces.some(([r, c]) => r === row && c === col);
        console.log('Response evaluation:', {
            row, col,
            piece,
            isCorrect,
            attackedPieces: this.game.attackedPieces
        });

        // Log trial data with reaction time
        const responsePosition = `${String.fromCharCode(97 + col)}${8 - row}`;
        this.game.logTrialData(responseTime, isCorrect ? 1 : 0, responsePosition);

        // Training mode feedback
        if (this.isTrainingMode) {
            console.log('Training mode feedback starting');
            
            // Highlight clicked square
            square.classList.add(isCorrect ? 'success' : 'failure');
            square.classList.add(isCorrect ? 'debug-success' : 'debug-failure');
            console.log('Added feedback classes to clicked square:', {
                classes: [...square.classList],
                isCorrect
            });

            // Highlight correct squares
            console.log('Highlighting correct squares...');
            this.game.attackedPieces.forEach(([r, c]) => {
                const correctSquare = this.chessboard.querySelector(`[data-row="${r}"][data-col="${c}"]`);
                if (correctSquare) {
                    console.log('Found correct square:', { r, c });
                    correctSquare.classList.add('success');
                    correctSquare.classList.add('debug-success');
                    console.log('Added success classes to correct square:', [...correctSquare.classList]);
                } else {
                    console.log('Could not find correct square:', { r, c });
                }
            });

            // Reveal the board with pieces
            this.showBoard = true;
            console.log('Setting showBoard to true');
            this.drawChessboard();
            console.log('Chessboard redrawn');

            // Add debug logging
            console.log('Training mode feedback state:', {
                clicked: { row, col, isCorrect },
                attackedPieces: this.game.attackedPieces,
                showBoard: this.showBoard
            });

            // Clear feedback after 1 second
            setTimeout(() => {
                console.log('Clearing feedback after 1 second...');
                // Remove all feedback classes
                this.chessboard.querySelectorAll('.square').forEach(square => {
                    console.log('Removing classes from square:', {
                        classes: [...square.classList]
                    });
                    square.classList.remove('success', 'failure', 'debug-success', 'debug-failure');
                });
                
                // Hide board again
                this.showBoard = false;
                console.log('Setting showBoard to false');
                this.drawChessboard();
                console.log('Chessboard redrawn');
                
                // Move to next trial
                console.log('Starting next trial...');
                this.startNewTrial();
            }, 1000);
        } else {
            console.log('Not in training mode - normal mode flow');
            // Normal mode - hide board and move to next trial
            
            // Add yellow highlight for 0.1s
            square.classList.add('normal-click');
            
            // Remove highlight after 0.1s
            setTimeout(() => {
                square.classList.remove('normal-click');
                this.showBoard = false;
                this.drawChessboard();
                this.startNewTrial();
            }, 50);
        }
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
        const IES = this.game.overall_ies || (rawAverageRT / accuracy);
        const IES_fixed = IES.toFixed(2);

        // Display rounded values
        const averageRT = rawAverageRT.toFixed(2);

        // Get focus scores from game object
        const focusDrift = this.game.focus_drift;
        const focusStability = this.game.focus_stability;

        // Determine color for focus drift using IES-based threshold
        const driftThreshold = 0.2 * IES; // 20% of IES
        const driftColor = focusDrift > driftThreshold ? 'darkgreen' :
                        focusDrift >= -driftThreshold ? 'darkgoldenrod' : 'darkred';

        // Determine color for focus stability
        const stabilityColor = focusStability >= 80 ? 'darkgreen' :
                            focusStability >= 60 ? 'darkgoldenrod' : 'darkred';

        // Format focus stability with %
        const stabilityValue = focusStability ? `${focusStability}%` : 'computing...';
        const driftValue = focusDrift ? focusDrift : 'computing...';

        this.resultsSummary.innerHTML = `
            <p>Total Trials: ${totalTrials}</p>
            <p>Success Rate: ${successRate}%</p>
            <p>Average Response Time: ${averageRT}s</p>
            <p>IES: ${IES_fixed} seconds</p>
            <p style="color: ${driftColor || 'gray'}">Focus Drift: ${driftValue}s</p>
            <p style="color: ${stabilityColor || 'gray'}">Focus Stability: ${stabilityValue}</p>
        `;

        // Store IES for leaderboard comparison
        this.game.IES = IES;

        // Automatically submit results to server
        this.submitResults();
    }

    submitResults() {
        // Submit the trial data to get server-calculated IES values
        fetch('/submit_results', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                patientName: this.patientName,
                trialData: this.game.trialData,
                difficulty: this.game.difficulty,
                duration: this.game.duration,
                boardDisplayTime: this.game.boardDisplayTime
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Store all IES values from server response
                this.game.overall_ies = data.ies;  // Overall IES (geometric mean of IES1, IES2, IES3)
                this.game.ies1 = data.ies1;
                this.game.ies2 = data.ies2;
                this.game.ies3 = data.ies3;
                this.game.focus_drift = data.focus_drift;
                this.game.focus_stability = data.focus_stability;
                
                // Update results display with server-calculated values
                const totalTrials = this.game.trialData.length;
                const successfulTrials = this.game.trialData.filter(trial => trial.success === 1).length;
                const successRate = ((successfulTrials / totalTrials) * 100).toFixed(1);

                // Calculate average response time for successful trials
                const rawAverageRT = this.game.trialData
                    .filter(trial => trial.success === 1)
                    .reduce((sum, trial) => sum + trial.responseTime, 0) / successfulTrials;

                // Display rounded values
                const averageRT = rawAverageRT.toFixed(2);
                const IES = this.game.overall_ies;  // Use the server-calculated overall IES
                const IES_fixed = IES.toFixed(2);
                // Calculate drift threshold based on IES
                const driftThreshold = 0.2 * IES; // 20% of IES

                // Determine color for focus drift using IES-based threshold
                const driftColor = this.game.focus_drift > driftThreshold ? 'darkgreen' :
                                this.game.focus_drift >= -driftThreshold ? 'darkgoldenrod' : 'darkred';

                // Add this logging after the submitResults call
                console.log('All Drift Values:', {
                    driftValues: this.game.trialData.map(trial => ({
                        trial: trial.trialNumber,
                        drift: trial.focus_drift,
                        responseTime: trial.responseTime,
                        success: trial.success
                    }))
                });

                // Determine color for focus stability
                const stabilityColor = this.game.focus_stability >= 80 ? 'darkgreen' :
                                    this.game.focus_stability >= 60 ? 'darkgoldenrod' : 'darkred';
                
                // Format focus stability with %
                const stabilityValue = this.game.focus_stability ? `${this.game.focus_stability}%` : 'computing...';
                const driftValue = this.game.focus_drift ? this.game.focus_drift : 'computing...';

                this.resultsSummary.innerHTML = `
                    <p>Total Trials: ${totalTrials}</p>
                    <p>Success Rate: ${successRate}%</p>
                    <p>Average Response Time: ${averageRT}s</p>
                    <p>IES: ${IES_fixed} seconds</p>
                    <p style="color: ${driftColor || 'gray'}">Focus Drift: ${driftValue}s</p>
                    <p style="color: ${stabilityColor || 'gray'}">Focus Stability: ${stabilityValue}</p>
                `;

                // Update leaderboard after successful submission
                this.fetchLeaderboard(true);  // Pass true to highlight current user
            }
        })
        .catch(error => console.error('Error:', error));
    }

    restartGame() {
        // Clear the leaderboard display
        const leaderboardContainer = document.getElementById('leaderboard-container');
        if (leaderboardContainer) {
            leaderboardContainer.innerHTML = '';
        }
        
        // Reset game state
        this.showScreen('name-input');
        this.game = new ChessGame();
        this.patientName = '';
        this.nameInput.value = '';
        
        // Clear any pending timers
        if (this.timer) {
            clearInterval(this.timer);
        }
        if (this.countdownTimer) {
            clearInterval(this.countdownTimer);
        }
        
        // Reset game state variables
        this.remainingTime = null;
        this.showBoard = false;
        this.showAttackingPiece = false;
        this.boardDisplayTime = null;
        this.trialStartTime = null;
        this.startTime = null;
        this.isTrainingMode = false;
        
        // Reset UI elements
        this.chessboard.innerHTML = '';
        this.attackingPieceContainer.innerHTML = '';
        this.timerDisplay.textContent = '';
        this.trialCount.textContent = '';
        this.resultsSummary.innerHTML = '';
        
        // Reinitialize loading text
        this.leaderboardLoading = document.getElementById('leaderboard-loading');
        if (this.leaderboardLoading) {
            this.leaderboardLoading.textContent = '';
        }
    }

    async fetchLeaderboard(highlightCurrentUser = false) {
        console.log('Starting fetchLeaderboard');
        
        // Safely handle loading element
        try {
            if (this.leaderboardLoading) {
                this.leaderboardLoading.textContent = 'Loading leaderboard...';
            } else {
                this.leaderboardLoading = document.getElementById('leaderboard-loading');
                if (this.leaderboardLoading) {
                    this.leaderboardLoading.textContent = 'Loading leaderboard...';
                }
            }
        } catch (e) {
            console.warn('Could not access loading element:', e);
        }
        
        console.log('Fetching leaderboard data...');
        
        try {
            console.log('Before fetch request');
            const response = await fetch('/get_leaderboard');
            console.log('Fetch response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Parsed JSON data:', data);
            
            this.displayLeaderboard(data.leaderboard, highlightCurrentUser);
            
            // Clear loading text if element exists
            if (this.leaderboardLoading) {
                this.leaderboardLoading.textContent = '';
            }
        } catch (error) {
            console.error('Error fetching leaderboard:', error);
            
            // Show error message if element exists
            if (this.leaderboardLoading) {
                this.leaderboardLoading.textContent = 'Failed to load leaderboard';
            }
        }
    }

    displayLeaderboard(leaderboardData, highlightCurrentUser = false) {
        console.log('displayLeaderboard called with data:', leaderboardData);
        
        // Check if we received valid data
        if (!leaderboardData || typeof leaderboardData !== 'object') {
            console.error('Invalid leaderboard data:', leaderboardData);
            return;
        }

        // Clear existing content
        const leaderboardContainer = document.getElementById('leaderboard-container');
        if (!leaderboardContainer) {
            console.error('Leaderboard container not found');
            return;
        }
        leaderboardContainer.innerHTML = '';

        // Create leaderboard columns
        const difficulties = ['hard', 'medium', 'easy'];
        difficulties.forEach(difficulty => {
            const column = document.createElement('div');
            column.className = 'leaderboard-column';

            // Add column header
            const header = document.createElement('h3');
            header.textContent = difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
            column.appendChild(header);

            // Add table
            const table = document.createElement('table');
            table.className = 'leaderboard-table';

            // Add table header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            headerRow.innerHTML = `
                <th>Rank</th>
                <th>Name</th>
                <th>IES (s)</th>
                <th>Drift (s)</th>
                <th>Stability (%)</th>
            `;
            thead.appendChild(headerRow);
            table.appendChild(thead);

            // Add table body
            const tbody = document.createElement('tbody');

            // Get entries for this difficulty - use case-insensitive comparison
            const entries = (leaderboardData[difficulty.toLowerCase()] || 
                            leaderboardData[difficulty.toUpperCase()] || 
                            leaderboardData[difficulty.charAt(0).toUpperCase() + difficulty.slice(1)] || 
                            [])
                            .sort((a, b) => parseFloat(a.score) - parseFloat(b.score));
            
            // Add top 10 entries with highlighting for current user
            entries.slice(0, 10).forEach((entry, index) => {
                const row = document.createElement('tr');
                
                // Highlight current user's row
                if (highlightCurrentUser && entry.name === this.patientName) {
                    row.className = 'highlight-current-user';
                }
                
                // Calculate drift threshold based on IES (using entry's IES value if available)
                const IES = entry.score; // Fallback to 1000 if IES is not available
                const driftThreshold = 0.2 * IES; // 20% of IES

                // Determine colors for drift and stability
                const driftColor = entry.drift > driftThreshold ? 'darkgreen' :
                                    entry.drift >= -driftThreshold ? 'darkgoldenrod' : 'darkred';

                const stabilityColor = entry.stability >= 80 ? 'darkgreen' :
                                    entry.stability >= 60 ? 'darkgoldenrod' : 'darkred';
                
                // Format drift value with '+' for positive numbers
                const driftDisplay = entry.drift >= 0 ? `+${entry.drift}` : entry.drift;
                
                row.innerHTML = `
                    <td>${index + 1}</td>
                    <td>${entry.name}</td>
                    <td>${entry.score}</td>
                    <td style="color: ${driftColor}">${driftDisplay}</td>
                    <td style="color: ${stabilityColor}">${entry.stability}%</td>
                `;
                tbody.appendChild(row);
            });

            // If highlighting current user and they're beyond top 10
            if (highlightCurrentUser) {
                const currentUserEntry = entries.find(entry => entry.name === this.patientName);
                if (currentUserEntry && entries.indexOf(currentUserEntry) >= 10) {
                    const separator = document.createElement('tr');
                    separator.className = 'leaderboard-separator';
                    separator.innerHTML = `
                        <td colspan="5">Your Score:</td>
                    `;
                    tbody.appendChild(separator);

                    const currentUserRow = document.createElement('tr');
                    currentUserRow.className = 'highlight-current-user';
                    
                    // Calculate drift threshold based on IES (using entry's IES value if available)
                    const IES = entry.ies || 1000; // Fallback to 1000 if IES is not available
                    const driftThreshold = 0.2 * IES; // 20% of IES
    
                    // Determine colors for drift and stability
                    const driftColor = entry.drift > driftThreshold ? 'darkgreen' :
                                        entry.drift >= -driftThreshold ? 'darkgoldenrod' : 'darkred';
    
                    const stabilityColor = entry.stability >= 80 ? 'darkgreen' :
                                        entry.stability >= 60 ? 'darkgoldenrod' : 'darkred';
                    
                    // Format drift value with '+' for positive numbers
                    const driftDisplay = currentUserEntry.drift >= 0 ? `+${currentUserEntry.drift}` : currentUserEntry.drift;
                    
                    currentUserRow.innerHTML = `
                        <td>${entries.indexOf(currentUserEntry) + 1}</td>
                        <td>${currentUserEntry.name}</td>
                        <td>${currentUserEntry.score}</td>
                        <td style="color: ${driftColor}">${driftDisplay}</td>
                        <td style="color: ${stabilityColor}">${currentUserEntry.stability}%</td>
                    `;
                    tbody.appendChild(currentUserRow);
                }
            }

            table.appendChild(tbody);
            column.appendChild(table);
            leaderboardContainer.appendChild(column);
        });

        // Hide loading text if element exists
        if (this.leaderboardLoading) {
            this.leaderboardLoading.textContent = '';
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

// Initialize GameUI when DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    const gameUI = new GameUI();
});

// If we're in a module context, export the class
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameUI;
} else {
    window.GameUI = GameUI;
}