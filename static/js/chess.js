// Chess piece movement patterns
const PIECE_MOVEMENTS = {
    'K': [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]],  // King
    'Q': [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]],  // Queen
    'R': [[1, 0], [0, 1], [-1, 0], [0, -1]],  // Rook
    'B': [[1, 1], [-1, 1], [-1, -1], [1, -1]],  // Bishop
    'N': [[2, 1], [1, 2], [-1, 2], [-2, 1], [-2, -1], [-1, -2], [1, -2], [2, -1]],  // Knight
    'P': [[-1, 1], [1, 1]],  // White pawn capture moves (up diagonally)
    'p': [[-1, -1], [1, -1]]  // Black pawn capture moves (down diagonally)
};

// Chess pieces Unicode symbols
const PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
};

// Difficulty levels
const DIFFICULTY_LEVELS = {
    "Easy": { minPieces: 4, maxPieces: 6 },
    "Medium": { minPieces: 6, maxPieces: 8 },
    "Hard": { minPieces: 8, maxPieces: 10 },
    "Very Hard": { minPieces: 10, maxPieces: 12 }
};

// Add duration options at the top with other constants
const DURATION_OPTIONS = {
    "Short": 20,     // 20 seconds
    "Medium": 90,    // 1.5 minutes
    "Long": 180,     // 3 minutes
    "Extended": 360  // 6 minutes
};

class ChessGame {
    constructor() {
        this.board = Array(8).fill().map(() => Array(8).fill(null));
        this.attackingPiece = null;
        this.attackedPieces = [];
        this.selectedSquare = null;
        this.hasResponded = false;
        this.trialData = [];
        this.currentTrial = 0;
        this.duration = DURATION_OPTIONS.Medium; // Default to 3 minutes
        this.hideTime = 3.0;
        this.difficulty = "Medium";
        this.timeOptions = [0.1, 0.5, 1, 3, 5, 10];  // Available time options in seconds
        this.attackingPieceShownTime = null;  // Track when the attacking piece is shown
        this.trialStartTime = null;  // Track the start time of the trial
        this.startTime = Date.now();  // Store the start time of the experience

    }

    initializeControls() {
        // Create time selector
        const timeSelector = document.createElement('div');
        timeSelector.className = 'time-selector';
        timeSelector.innerHTML = `
            <label>Board Display Time:</label>
            <select id="timeSelect" class="time-select">
                ${this.timeOptions.map(time => 
                    `<option value="${time}" ${time === 3 ? 'selected' : ''}>${time}s</option>`
                ).join('')}
            </select>
        `;

        // Add event listener
        document.getElementById('timeSelect').addEventListener('change', (e) => {
            this.hideTime = parseFloat(e.target.value);
        });

        // Add controls to the page
        const controlsContainer = document.createElement('div');
        controlsContainer.className = 'controls-container';
        controlsContainer.appendChild(timeSelector);
        document.querySelector('#game-container').appendChild(controlsContainer);
    }

    isValidMove(piece, startRow, startCol, endRow, endCol) {
        const pieceType = piece[1];
        const color = piece[0];
        const movements = PIECE_MOVEMENTS[pieceType];
        
        for (const [dx, dy] of movements) {
            if (['K', 'N'].includes(pieceType)) {
                if (endRow === startRow + dy && endCol === startCol + dx) {
                    return true;
                }
            } else if (pieceType === 'P' || pieceType === 'p') {
                // For pawns, use the correct movement pattern based on color
                const pawnMovements = PIECE_MOVEMENTS[pieceType];
                for (const [pawnDx, pawnDy] of pawnMovements) {
                    if (endRow === startRow + pawnDy && endCol === startCol + pawnDx) {
                        return true;
                    }
                }
            } else {
                let currentRow = startRow + dy;
                let currentCol = startCol + dx;
                while (currentRow >= 0 && currentRow < 8 && currentCol >= 0 && currentCol < 8) {
                    if (currentRow === endRow && currentCol === endCol) {
                        return true;
                    }
                    if (this.board[currentRow][currentCol] !== null) {
                        break;
                    }
                    currentRow += dy;
                    currentCol += dx;
                }
            }
        }
        return false;
    }

    findAttackedPieces(piece, row, col) {
        const attacked = [];
        const pieceType = piece[1];
        const color = piece[0];
        
        for (const [dx, dy] of PIECE_MOVEMENTS[pieceType]) {
            if (['K', 'N'].includes(pieceType)) {
                const newRow = row + dy;
                const newCol = col + dx;
                if (newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8) {
                    const target = this.board[newRow][newCol];
                    if (target !== null && target[0] !== color) {
                        attacked.push([newRow, newCol]);
                    }
                }
            } else if (pieceType === 'P' || pieceType === 'p') {
                // For pawns, we need to check in the correct direction based on color
                const newCol = color === 'w' ? col + 1 : col - 1;  // White moves up (-1), Black moves down (+1)
                const newRow = row + dx;  // Use the dx from the movement pattern for diagonal direction
                if (newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8) {
                    const target = this.board[newRow][newCol];
                    if (target !== null && target[0] !== color) {
                        attacked.push([newRow, newCol]);
                    }
                }
            } else {
                let currentRow = row + dy;
                let currentCol = col + dx;
                while (currentRow >= 0 && currentRow < 8 && currentCol >= 0 && currentCol < 8) {
                    const target = this.board[currentRow][currentCol];
                    if (target !== null) {
                        if (target[0] !== color) {
                            attacked.push([currentRow, currentCol]);
                        }
                        break;
                    }
                    currentRow += dy;
                    currentCol += dx;
                }
            }
        }
        return attacked;
    }

    areKingsAdjacent() {
        let whiteKing = null;
        let blackKing = null;
        
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const piece = this.board[row][col];
                if (piece === 'wK') {
                    whiteKing = [row, col];
                } else if (piece === 'bK') {
                    blackKing = [row, col];
                }
            }
        }
        
        if (whiteKing && blackKing) {
            const rowDiff = Math.abs(whiteKing[0] - blackKing[0]);
            const colDiff = Math.abs(whiteKing[1] - blackKing[1]);
            return rowDiff <= 1 && colDiff <= 1;
        }
        return false;
    }

    generatePosition() {
        this.board = Array(8).fill().map(() => Array(8).fill(null));
        const { minPieces, maxPieces } = DIFFICULTY_LEVELS[this.difficulty];
        const numPieces = Math.floor(Math.random() * (maxPieces - minPieces + 1)) + minPieces;
        
        // Track used pieces for each color
        const usedPieces = {
            w: new Set(),
            b: new Set()
        };
        
        // Step 1: Choose attacking piece and color
        const attackingColor = Math.random() < 0.5 ? 'w' : 'b';
        const pieceTypes = ['P', 'N', 'B', 'R', 'Q', 'K'];  // All possible piece types
        const attackingType = pieceTypes[Math.floor(Math.random() * pieceTypes.length)];
        const attackingPiece = attackingColor + attackingType;
        
        // Mark attacking piece as used
        usedPieces[attackingColor].add(attackingType);
        
        // Step 2: Place attacking piece
        let validPosition = false;
        let attackingRow, attackingCol;
        
        while (!validPosition) {
            // For pawns, ensure they're placed on valid ranks based on color
            if (attackingType === 'P') {
                if (attackingColor === 'w') {
                    // White pawns start on ranks 2-7 (rows 1-6)
                    attackingRow = Math.floor(Math.random() * 6) + 1;
                } else {
                    // Black pawns start on ranks 2-7 (rows 1-6)
                    attackingRow = Math.floor(Math.random() * 6) + 1;
                }
            } else {
                attackingRow = Math.floor(Math.random() * 8);
            }
            attackingCol = Math.floor(Math.random() * 8);
            
            // Place the attacking piece temporarily
            this.board[attackingRow][attackingCol] = attackingPiece;
            
            // Find all possible attacked squares
            const possibleSquares = [];
            for (const [dx, dy] of PIECE_MOVEMENTS[attackingType]) {
                if (['K', 'N'].includes(attackingType)) {
                    const newRow = attackingRow + dy;
                    const newCol = attackingCol + dx;
                    if (newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8) {
                        possibleSquares.push([newRow, newCol]);
                    }
                } else if (attackingType === 'P') {
                    // Handle pawn moves based on color
                    if (attackingColor === 'w') {
                        // White pawns move up (negative row direction)
                        const newRow = attackingRow - 1;
                        const newCol = attackingCol + dx;
                        if (newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8) {
                            possibleSquares.push([newRow, newCol]);
                        }
                    } else {
                        // Black pawns move down (positive row direction)
                        const newRow = attackingRow + 1;
                        const newCol = attackingCol + dx;
                        if (newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8) {
                            possibleSquares.push([newRow, newCol]);
                        }
                    }
                } else {
                    let currentRow = attackingRow + dy;
                    let currentCol = attackingCol + dx;
                    while (currentRow >= 0 && currentRow < 8 && currentCol >= 0 && currentCol < 8) {
                        possibleSquares.push([currentRow, currentCol]);
                        currentRow += dy;
                        currentCol += dx;
                    }
                }
            }
            
            if (possibleSquares.length > 0) {
                // Step 3: Place attacked piece
                const [attackedRow, attackedCol] = possibleSquares[Math.floor(Math.random() * possibleSquares.length)];
                const defendingColor = attackingColor === 'w' ? 'b' : 'w';
                
                // Choose a random unused piece type for the attacked piece
                const availableDefendingTypes = pieceTypes.filter(type => !usedPieces[defendingColor].has(type));
                if (availableDefendingTypes.length === 0) {
                    // If no pieces available, reset and try again
                    this.board[attackingRow][attackingCol] = null;
                    continue;
                }
                const defendingType = availableDefendingTypes[Math.floor(Math.random() * availableDefendingTypes.length)];
                
                // If defending piece is a pawn, ensure it's not on first or last rank
                if (defendingType === 'P') {
                    if (defendingColor === 'w' && (attackedRow === 0 || attackedRow === 7)) {
                        this.board[attackingRow][attackingCol] = null;
                        continue;
                    }
                    if (defendingColor === 'b' && (attackedRow === 0 || attackedRow === 7)) {
                        this.board[attackingRow][attackingCol] = null;
                        continue;
                    }
                }
                
                // Mark defending piece as used
                usedPieces[defendingColor].add(defendingType);
                
                this.board[attackedRow][attackedCol] = defendingColor + defendingType;
                this.attackingPiece = [attackingPiece, attackingRow, attackingCol];
                //this.attackedPieces = [[attackedRow, attackedCol]];
                this.attackedPieces = [[attackedRow, attackedCol]];
                validPosition = true;
            } else {
                this.board[attackingRow][attackingCol] = null;
            }
        }
        
        // Step 4: Fill remaining pieces randomly
        let piecesPlaced = 2;  // We've placed 2 pieces so far
        let attempts = 0;
        const maxAttempts = 100;  // Prevent infinite loops
        
        while (piecesPlaced < numPieces && attempts < maxAttempts) {
            const color = Math.random() < 0.5 ? 'w' : 'b';
            
            // Get available piece types for this color
            const availableTypes = pieceTypes.filter(type => !usedPieces[color].has(type));
            if (availableTypes.length === 0) {
                attempts++;
                continue;  // Skip if no pieces available for this color
            }
            
            const type = availableTypes[Math.floor(Math.random() * availableTypes.length)];
            const piece = color + type;
            
            let row = type === 'P' ? Math.floor(Math.random() * 6) + 1 : Math.floor(Math.random() * 8);
            let col = Math.floor(Math.random() * 8);
            
            if (this.board[row][col] === null) {
                this.board[row][col] = piece;
                
                // Check if kings are adjacent
                if (this.areKingsAdjacent()) {
                    this.board[row][col] = null;
                    attempts++;
                    continue;
                }
                
                usedPieces[color].add(type);
                piecesPlaced++;
                attempts = 0;  // Reset attempts counter after successful placement
            }
            attempts++;
        }
        
        // Check for attacked pieces after placing remaining pieces
        const attackedSet = new Set(); // Use a Set to track unique attacked positions

        for (let r = 0; r < 8; r++) {
            for (let c = 0; c < 8; c++) {
                const placedPiece = this.board[r][c];
                if (placedPiece && placedPiece[0] !== this.attackingPiece[0]) { // Ensure different color
                    const attacked = this.findAttackedPieces(this.attackingPiece[0], this.attackingPiece[1], this.attackingPiece[2]);
                    if (attacked.some(([ar, ac]) => ar === r && ac === c)) {
                        const positionKey = `${r},${c}`; // Create a unique key for the position
                        if (!attackedSet.has(positionKey) && !this.attackedPieces.some(([pr, pc]) => pr === r && pc === c)) { // Check if the position is already added
                            attackedSet.add(positionKey); // Add to the Set
                            this.attackedPieces.push([r, c]); // Update attackedPieces
                        }
                    }
                }
            }
        }
        
        // If we couldn't place all pieces, try again
        if (piecesPlaced < numPieces) {
            this.generatePosition();
        }
    }

    logTrialData(responseTime, success, responsePosition) {
        const trialData = {
            trial: this.currentTrial,
            trialTime: Math.abs(this.trialStartTime - this.startTime) / 1000,
            attackingPiece: this.attackingPiece[0],
            attackingPosition: `${String.fromCharCode(97 + this.attackingPiece[2])}${8 - this.attackingPiece[1]}`,
            attackedPieces: this.attackedPieces.map(([row, col]) => 
                `${String.fromCharCode(97 + col)}${8 - row}`).join(';'),
            responseTime,
            success,
            responsePosition
        };
        
        this.trialData.push(trialData);
        return trialData;
    }

    drawBoard() {
        const board = document.getElementById('chessboard');
        board.innerHTML = '';  // Clear existing board
        
        // Create container for board and labels
        const container = document.createElement('div');
        container.id = 'chessboard-container';
        board.appendChild(container);
        
        // Add rank labels (8-1)
        for (let i = 0; i < 8; i++) {
            const label = document.createElement('div');
            label.className = 'coordinate-label rank-label';
            label.style.top = `${i * 75}px`;  // Adjust based on your square size
            label.textContent = 8 - i;
            container.appendChild(label);
        }
        
        // Add file labels (a-h)
        for (let i = 0; i < 8; i++) {
            const label = document.createElement('div');
            label.className = 'coordinate-label file-label';
            label.style.left = `${i * 75 + 25}px`;  // Adjust based on your square size
            label.textContent = String.fromCharCode(97 + i);  // 'a' through 'h'
            container.appendChild(label);
        }
        
        // Draw the squares and pieces
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const square = document.createElement('div');
                square.className = 'square';
                square.dataset.row = row;
                square.dataset.col = col;
                
                // Add checkered pattern
                if ((row + col) % 2 === 0) {
                    square.classList.add('light');
                } else {
                    square.classList.add('dark');
                }
                
                // Add piece if present
                const piece = this.board[row][col];
                if (piece) {
                    const pieceElement = document.createElement('div');
                    pieceElement.className = 'piece';
                    pieceElement.textContent = PIECES[piece[1]];  // Use Unicode chess symbols
                    pieceElement.classList.add(piece[0] === 'w' ? 'white' : 'black');
                    square.appendChild(pieceElement);
                }
                
                container.appendChild(square);
            }
        }
    }

    hideBoard() {
        this.showBoard = false;
        this.showAttackingPiece = true;
        this.attackingPieceShownTime = Date.now();  // Record the time when attacking piece is shown
    }

    handleSquareClick(row, col) {
        if (!this.attackingPieceShownTime || this.hasResponded) return;

        this.hasResponded = true;
        const responseTime = (Date.now() - this.attackingPieceShownTime) / 1000;  // Convert to seconds

        // Check if clicked square is in attacked squares
        const isCorrect = this.attackedPieces.some(([r, c]) => r === row && c === col);

        // Log trial data with reaction time
        const responsePosition = `${String.fromCharCode(97 + col)}${8 - row}`;
        this.logTrialData(responseTime, isCorrect ? 1 : 0, responsePosition);

        return isCorrect;
    }

    startNewTrial() {
        // Clear the previous attacking piece's position if it exists
        if (this.attackingPiece) {
            const [piece, row, col] = this.attackingPiece;
            this.board[row][col] = '';
        }
        
        this.generatePosition();
        this.showBoard = true;
        this.showAttackingPiece = false;
        this.hasResponded = false;
        this.currentTrial++;

        // Set the trial start time
        this.trialStartTime = Date.now();  // Capture the start time of the trial

        // Hide board after specified time
        setTimeout(() => {
            this.showBoard = false;
            this.showAttackingPiece = true;
            this.attackingPieceShownTime = Date.now();
        }, this.hideTime * 1000);

        console.log("Start Time:", this.startTime);
        console.log("Trial Start Time:", this.trialStartTime);
        console.log("Trial Time:", (this.trialStartTime - this.startTime) / 1000);
    }

    // Add CSS styles for the new controls
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .controls-container {
                margin: 20px;
                display: flex;
                gap: 20px;
                align-items: center;
            }

            .time-selector {
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .time-select {
                padding: 5px;
                font-size: 14px;
            }
        `;
        document.head.appendChild(style);
    }

    // Add method to change duration
    setDuration(durationOption) {
        if (DURATION_OPTIONS[durationOption] !== undefined) {
            this.duration = DURATION_OPTIONS[durationOption];
            return true;
        }
        return false;
    }
} 