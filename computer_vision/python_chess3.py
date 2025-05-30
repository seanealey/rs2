import numpy as np
import chess
import chess.pgn
from typing import Tuple, Optional, List
import matplotlib.pyplot as plt
import cv2
import re
from computer_vision import square_processing as sp

class game:
    def __init__(self, initial_fen=None):
        """
        Initialize the game
        
        Args:
            initial_fen: Optional FEN string to set the initial board state
                         If None, starts with the standard chess starting position
        """
        # Initialize a chess board
        if initial_fen:
            self.board = chess.Board(initial_fen)
        else:
            self.board = chess.Board()
            
        # Initialize PGN game
        self.game = chess.pgn.Game()
        self.game.headers["Event"] = "Computer Vision Chess Analysis"
        self.game.headers["Site"] = "Local Analysis"
        self.game.headers["Date"] = "????.??.??"
        self.game.headers["Round"] = "1"
        self.game.headers["White"] = "Player 1"
        self.game.headers["Black"] = "Player 2"
        self.game.headers["Result"] = "*"
        self.current_node = self.game
        
        # Keep track of the previous board state as a NumPy array
        self.previous_board_array = self.board_to_color_array(self.board)
    
    ############chess_2 methods##################################
    
    def board_to_color_array(self, board):
        """
        Convert a python-chess board to an 8x8 NumPy array showing only piece colors
        
        Array values:
        0 = empty square
        1 = white piece
        -1 = black piece
        """
        board_array = np.zeros((8, 8), dtype=int)
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                # Get rank and file (0-7)
                rank = chess.square_rank(square)
                file = chess.square_file(square)
                
                # Set value based only on color (1 for white, -1 for black)
                value = 1 if piece.color == chess.WHITE else -1
                board_array[7-rank][file] = value
        
        return board_array
    
    def detect_move(self, new_color_array):
        """Detect the move by comparing the previous and new board states with color-only arrays"""
        # Find changed squares
        changed_squares = np.where(self.previous_board_array != new_color_array)
        changed_rows, changed_cols = changed_squares
        
        if len(changed_rows) < 2:
            # No move detected or invalid
            return None
        
        # Find candidate moves
        candidate_moves = []
        
        # Get all legal moves from current board position
        for move in self.board.legal_moves:
            # Make the move on a temporary board
            temp_board = chess.Board(self.board.fen())
            temp_board.push(move)
            
            # Convert to color array and compare with new_color_array
            temp_array = self.board_to_color_array(temp_board)
            
            # Calculate number of matching positions
            matches = np.sum(temp_array == new_color_array)
            total_squares = 64
            
            # Add to candidates with match score
            if matches >= (total_squares - 4):  # Allow for some discrepancy
                candidate_moves.append((move, matches))
                
                # Debug information
                if matches == total_squares:
                    print(f"Perfect match found: {move}")
        
        # If no candidates found, return None
        if not candidate_moves:
            print("No candidate moves found that match the new board state")
            # Print current board FEN for debugging
            print(f"Current board: {self.board.fen()}")
            return None
        
        # Get the best match
        best_match = max(candidate_moves, key=lambda x: x[1])
        best_move, match_score = best_match
        
        print(f"Best move match: {best_move} with {match_score}/{64} matching squares")
        
        return best_move
    
    def update_board(self, new_color_array, forced_turn=None):
        """
        Update the board with a newly detected position and return the PGN move
        
        Args:
            new_color_array: Current observed board state as NumPy array (color only)
            forced_turn: Force a specific turn (chess.WHITE or chess.BLACK)
                         If None, uses the internal turn tracking
        """
        # Use forced turn if provided, otherwise use internal tracking
        if forced_turn is not None:
            actual_turn = forced_turn
            
            # If we're forcing a specific turn, adjust the board's turn if needed
            if actual_turn != self.board.turn:
                print(f"Adjusting turn to {'White' if actual_turn == chess.WHITE else 'Black'}")
                # Create a new board with the same position but different turn
                new_fen_parts = self.board.fen().split()
                new_fen_parts[1] = 'w' if actual_turn == chess.WHITE else 'b'
                new_fen = ' '.join(new_fen_parts)
                self.board = chess.Board(new_fen)
        
        # Detect move
        move = self.detect_move(new_color_array)
        
        if move is None:
            # No valid move detected
            print("No valid move detected")
            return None
        
        try:
            # Check if move is legal in current position
            if move not in self.board.legal_moves:
                print(f"Move {move} is not legal in current position")
                return None
            
            # Get SAN notation of the move before pushing it
            san_move = self.board.san(move)
            
            # Make the move on the board
            self.board.push(move)
            
            # Add the move to the PGN
            self.current_node = self.current_node.add_variation(move)
            
            # Update previous board array
            self.previous_board_array = new_color_array.copy()
            
            # Get current move number and turn
            move_number = (self.board.fullmove_number - 1) + (1 if not self.board.turn else 0)
            is_white_just_moved = self.board.turn == chess.BLACK  # If it's Black's turn now, White just moved
            
            # Format PGN move
            if is_white_just_moved:
                pgn_move = f"{move_number}. {san_move}"
            else:
                pgn_move = san_move
            
            print(f"Successfully updated board with move: {move}")
            return pgn_move
            
        except Exception as e:
            print(f"Error updating board: {e}")
            print(f"Current FEN: {self.board.fen()}")
            print(f"Attempted move: {move}")
            return None
    
       
    def infer_turn(self, current_color_array, new_color_array):
        """
        Try to infer which side is moving based on board changes
        
        Args:
            current_color_array: Previous board state (color only)
            new_color_array: Current board state (color only)
        
        Returns:
            chess.WHITE or chess.BLACK based on likely moving side
        """
        # Find which pieces moved
        if np.array_equal(current_color_array, new_color_array):
            # No change detected
            return None
            
        # Check if piece counts changed
        white_before = np.sum(current_color_array == 1)
        white_after = np.sum(new_color_array == 1)
        
        black_before = np.sum(current_color_array == -1)
        black_after = np.sum(new_color_array == -1)
        
        # If white piece count changed, likely white moved
        if white_before != white_after:
            return chess.WHITE
        
        # If black piece count changed, likely black moved
        if black_before != black_after:
            return chess.BLACK
        
        # If piece counts didn't change, try both turns and see which one gives legal moves
        white_board = chess.Board(self.board.fen())
        if white_board.turn != chess.WHITE:
            # Force white turn
            fen_parts = white_board.fen().split()
            fen_parts[1] = 'w'
            white_board = chess.Board(' '.join(fen_parts))
            
        black_board = chess.Board(self.board.fen())
        if black_board.turn != chess.BLACK:
            # Force black turn
            fen_parts = black_board.fen().split()
            fen_parts[1] = 'b'
            black_board = chess.Board(' '.join(fen_parts))
        
        # Try to find moves for white
        white_moves = []
        for move in white_board.legal_moves:
            temp_board = chess.Board(white_board.fen())
            temp_board.push(move)
            temp_array = self.board_to_color_array(temp_board)
            
            # Calculate match score
            match_score = np.sum(temp_array == new_color_array)
            
            if match_score >= 62:  # Allow for some discrepancy
                white_moves.append((move, match_score))
                
        # Try to find moves for black
        black_moves = []
        for move in black_board.legal_moves:
            temp_board = chess.Board(black_board.fen())
            temp_board.push(move)
            temp_array = self.board_to_color_array(temp_board)
            
            # Calculate match score
            match_score = np.sum(temp_array == new_color_array)
            
            if match_score >= 62:  # Allow for some discrepancy
                black_moves.append((move, match_score))
        
        # Determine which side has better moves
        best_white_score = max([score for _, score in white_moves], default=0)
        best_black_score = max([score for _, score in black_moves], default=0)
        
        if best_white_score > best_black_score:
            return chess.WHITE
        elif best_black_score > best_white_score:
            return chess.BLACK
        elif white_moves and not black_moves:
            return chess.WHITE
        elif black_moves and not white_moves:
            return chess.BLACK
        
        # If we can't determine, use the board's current turn
        return self.board.turn
    
    def process_move(self, new_color_array):
        """
        Process a board state change, inferring whose turn it is if necessary
        
        Args:
            new_color_array: Current observed board state as NumPy array (color only)
            
        Returns:
            PGN formatted move notation
        """
        # First, check if there's actually a change
        if np.array_equal(self.previous_board_array, new_color_array):
            print("No board change detected")
            return None
        
        # Infer whose turn it is
        inferred_turn = self.infer_turn(self.previous_board_array, new_color_array)
        
        if inferred_turn is None:
            print("Couldn't infer which side moved")
            return None
            
        print(f"Inferred turn: {'White' if inferred_turn == chess.WHITE else 'Black'}")
        
        # Update the board with the inferred turn
        return self.update_board(new_color_array, forced_turn=inferred_turn)
    
    def get_pgn(self):
        """Return the current game in PGN format"""
        return str(self.game)

    def analyze_binary_board_state(analyzer, new_board_array):
        """
        Analyzes a new binary board state (0 for empty, 1 for white, -1 for black)
        and updates the chess board analyzer.
        
        Args:
            analyzer (game): An initialized game object
            new_board_array (numpy.ndarray): 8x8 array with 0 (empty), 1 (white), -1 (black)
            
        Returns:
            dict: Analysis results containing:
                - detected_move: The detected move in SAN notation (e.g., 'e4')
                - current_fen: The current FEN representation of the board
                - board_array: The current board array after the move
                - board_visual: ASCII visual representation of the board
                - pgn: Current PGN of the game
        """
        # Update the board with the new state
        detected_move_pgn = analyzer.update_board(new_board_array)
        
        # Extract SAN move from PGN like "1. e4"
        detected_move_san = None
        if detected_move_pgn:
            match = re.match(r"\d+\.\s*(\S+)", detected_move_pgn)
            if match:
                detected_move_san = match.group(1)
            else:
                detected_move_san = detected_move_pgn  # fallback
        
        # Create a visual representation of the board
        board_visual = str(analyzer.board)
        
        # Prepare results
        results = {
            "detected_move": detected_move_san,
            "current_fen": analyzer.board.fen(),
            "board_array": analyzer.previous_board_array.copy(),
            "board_visual": board_visual,
            "pgn": analyzer.get_pgn()
        }
        
        # Print analysis summary
        print(f"Detected move: {detected_move_san if detected_move_san else 'None'}")
        #print(f"Current FEN: {analyzer.board.fen()}")
        print(f"Current board state:")
        print(board_visual)
        
        return results
    #######chessboard analyser methods ###############################

    def analyze_chessboard(self, image_input, auto_calib=True, corners=[], DEBUG=False):
        """
        Analyze a chessboard image and return a 2D array representing the board state.

        Args:
            image_input (str or np.ndarray): Image path or image array
            auto_calib (bool): Whether to auto-calibrate corners
            corners (list): Optional known corners
            DEBUG (bool): Show debug image

        Returns:
            np.ndarray: 8x8 board array, list: used corners
        """
        #print(f"[DEBUG] Type of current_img: {type(image_input)}")

        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"Could not read image at {image_input}")
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            raise TypeError("image_input must be a file path (str) or a NumPy image")
        
            #cv2.imshow("Original Chessboard Image", img)  # Display the image in a window
        # Initialize approx
        approx = None
        #print(f"[DEBUG] Type of current_img: {type(img)}")

        if auto_calib == True:
            #print(f"[DEBUG] attempting to detect corners")
            approx, success = self.detect_blue_corners(img)
            if not success:
                #print(f"[DEBUG] corner detection failed, manually select corners")
                approx = select_points(image_input)
        elif corners is not None and len(corners) > 0:
            approx = corners
        else:
            approx = select_points(image_input)


        # Order the points [top-left, top-right, bottom-right, bottom-left]
        pts = np.array(approx, dtype=np.float32).reshape(-1, 2)
        s = pts.sum(axis=1)
        ordered_pts = np.zeros((4, 2), dtype=np.float32)
        ordered_pts[0] = pts[np.argmin(s)]  # Top-left
        ordered_pts[2] = pts[np.argmax(s)]  # Bottom-right
        diff = np.diff(pts, axis=1)
        ordered_pts[1] = pts[np.argmin(diff)]  # Top-right
        ordered_pts[3] = pts[np.argmax(diff)]  # Bottom-left


        if None in ordered_pts or any(np.isnan(pt).any() for pt in ordered_pts):
            raise ValueError("Corner detection failed — one or more points are missing or invalid.")

        # Create a copy of the original image to draw points on
        img_with_points = img.copy()

        # Draw the corner points on the original image
        colors = [(0, 0, 255),   # Red for top-left
                (0, 255, 0),   # Green for top-right
                (255, 0, 0),   # Blue for bottom-right
                (255, 255, 0)] # Cyan for bottom-left

        point_labels = ["TL", "TR", "BR", "BL"]

        for i, point in enumerate(ordered_pts):
            x, y = int(point[0]), int(point[1])
            cv2.circle(img_with_points, (x, y), 10, colors[i], -1)
            cv2.putText(img_with_points, point_labels[i], (x+10, y+10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, colors[i], 2)

        # Display the original image with corner points
        cv2.imshow("Original with Corners", img_with_points)

        # Get width and height of the chessboard
        width = int(max(
            np.linalg.norm(ordered_pts[0] - ordered_pts[1]),
            np.linalg.norm(ordered_pts[2] - ordered_pts[3])
        ))
        height = int(max(
            np.linalg.norm(ordered_pts[0] - ordered_pts[3]),
            np.linalg.norm(ordered_pts[1] - ordered_pts[2])
        ))

        # Define the destination points for perspective transform
        dst = np.array([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]
        ], dtype=np.float32)

        # Calculate the perspective transform matrix and apply it
        matrix = cv2.getPerspectiveTransform(ordered_pts, dst)
        warped = cv2.warpPerspective(img, matrix, (width, height))

        # Create a copy of the warped image to draw points on
        warped_with_points = warped.copy()

        # Draw the corner points on the warped image
        # Since we know exactly where these points should be after transformation
        warped_corners = [
            (0, 0),                  # Top-left
            (width - 1, 0),          # Top-right
            (width - 1, height - 1), # Bottom-right
            (0, height - 1)          # Bottom-left
        ]

        for i, point in enumerate(warped_corners):
            x, y = point
            cv2.circle(warped_with_points, (x, y), 10, colors[i], -1)
            cv2.putText(warped_with_points, point_labels[i], (x+10, y+10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, colors[i], 2)

        # Display the warped chessboard with corner points
        #cv2.imshow("Corrected Chessboard with Corners", warped_with_points)
        # Step 2: Divide the chessboard into 64 squares
        square_width = width // 8
        square_height = height // 8
        
        # Create a figure to display all squares
        
        fig, axes = plt.subplots(8, 8, figsize=(15, 15))
        if not DEBUG:
            plt.close(fig)
        
        # Initialize the board representation
        board = np.zeros((8, 8), dtype=np.int8)
        
        # Process each square
        square_images = []
        for row in range(8):
            for col in range(8):
                # Extract square
                """
                y1 = row * square_height
                y2 = (row + 1) * square_height
                x1 = col * square_width
                x2 = (col + 1) * square_width
                
                square = warped[y1:y2, x1:x2].copy()
                """
            # Define base square boundaries
                base_x1 = col * square_width
                base_y1 = row * square_height
                base_x2 = (col + 1) * square_width
                base_y2 = (row + 1) * square_height

                # Padding to zoom out (e.g. 25% of square size)
                padding_x = square_width // 10
                padding_y = square_height // 10

                # Expand the boundaries
                x1 = max(base_x1 - padding_x, 0)
                y1 = max(base_y1 - padding_y, 0)
                x2 = min(base_x2 + padding_x, warped.shape[1])
                y2 = min(base_y2 + padding_y, warped.shape[0])

                # Extract expanded square region
                square = warped[y1:y2, x1:x2].copy()


                square_images.append(square)
                
                # Detect if there's a piece and its color
                #is_piece, piece_color = detect_piece_and_color(square)
                is_piece, piece_color, z = sp.detect_chess_piece_colour(square)
                
                
                # Update the board array
                if is_piece:
                    if piece_color == "white":
                        board[row, col] = 1
                    else:  # piece_color == "black"
                        board[row, col] = -1
                
                # Display the square with its classification
                square_rgb = cv2.cvtColor(square, cv2.COLOR_BGR2RGB)
                axes[row, col].imshow(square_rgb)
                axes[row, col].set_title(f"{'Empty' if not is_piece else piece_color}", fontsize=8)
                axes[row, col].axis('off')
        
        #plt.tight_layout()
        #plt.show()
        
        # Display the final board state
        if DEBUG:
            fig, ax = plt.subplots(figsize=(10, 10))
            cmap = plt.cm.colors.ListedColormap(['darkgrey','white', 'lightgrey', ])
            bounds = [-1.5, -0.5, 0.5, 1.5]
            norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)
            ax.imshow(board, cmap=cmap, norm=norm)
        
            # Add piece labels
            for row in range(8):
                for col in range(8):
                    if board[row, col] == 0:
                        text = ""
                    elif board[row, col] == 1:
                        text = "W"
                    else:
                        text = "B"
                    ax.text(col, row, text, ha='center', va='center', fontsize=16)
            
            # Add row and column labels
            columns = 'ABCDEFGH'
            rows = '87654321'
            for i in range(8):
                ax.text(i, -0.5, columns[i], ha='center', fontsize=12)
                ax.text(-0.5, i, rows[i], va='center', fontsize=12)
            
            ax.set_xticks(np.arange(8) - 0.5, minor=True)
            ax.set_yticks(np.arange(8) - 0.5, minor=True)
            ax.grid(which='minor', color='black', linestyle='-', linewidth=2)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title("Chess Board State (0=Empty, 1=White, 2=Black)")
            plt.tight_layout()
            plt.show()
        
        return board, approx
    
    """
    def detect_blue_corners(self, image_input, show_result=False):
        print(f"[DEBUG] detect_blue_corners received type: {type(image_input)}")

        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"Could not read image at {image_input}")
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            raise TypeError("image_input must be a file path (str) or a NumPy image")
        
        h, w = image_input.shape[:2]
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # HSV range for blue
        lower_blue = np.array([0, 199, 70])
        upper_blue = np.array([133, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        #cv2.imshow("Mask Only", mask)
        #key = cv2.waitKey(1) & 0xFF

        # Morphological clean-up
        #kernel = np.ones((3,3), np.uint8)
        #mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        #cv2.imshow("Mask Only", mask)
        key = cv2.waitKey(1) & 0xFF

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Define image corners
        image_corners = {
            "TL": (0, 0),
            "TR": (w, 0),
            "BL": (0, h),
            "BR": (w, h)
        }
        max_distance = min(w, h) * 0.15  # Threshold: 15% of size

        centroids = []
        for cnt in contours:
            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            point = (cx, cy)
            centroids.append(point)
            cv2.circle(img, point, 5, (255, 0, 255), 2)  # magenta


        # Match best centroid to each corner (closest only)
        best_matches = {label: (None, float('inf')) for label in image_corners}

        for point in centroids:
            for label, corner in image_corners.items():
                dist = np.linalg.norm(np.array(point) - np.array(corner))
                if dist < max_distance and dist < best_matches[label][1]:
                    best_matches[label] = (point, dist)

        found_corners = {
            label: pt for label, (pt, dist) in best_matches.items() if pt is not None
        }


        # Ensure all 4 corners were found
        ordered_labels = ["TL", "TR", "BL", "BR"]
        ordered_points = []

        for lbl in ordered_labels:
            pt = found_corners.get(lbl)
            if pt is None:
                ordered_points.append((np.nan, np.nan))
            else:
                ordered_points.append(pt)

        success = all(
            isinstance(pt, (list, tuple)) and
            len(pt) == 2 and
            not np.isnan(pt[0]) and
            not np.isnan(pt[1])
            for pt in ordered_points
        )



        if show_result:
            for point in ordered_points:
                cv2.circle(img, point, 10, (0, 255, 0), 2)
            print("Ordered Corners (TL, TR, BL, BR):", ordered_points)
            cv2.imshow("Detected Corners", img)
            cv2.imshow("Blue Mask", mask)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        
        return ordered_points, success

    """
    def detect_blue_corners(self, image_input, show_result=False):
        #print(f"[DEBUG] detect_blue_corners received type: {type(image_input)}")

        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"Could not read image at {image_input}")
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            raise TypeError("image_input must be a file path (str) or a NumPy image")
        
        # Fix: Use img.shape instead of image_input.shape
        h, w = img.shape[:2]
        
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # HSV range for blue
        lower_blue = np.array([0, 199, 70])
        upper_blue = np.array([133, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Fix: Use correct image corner coordinates (0-indexed)
        image_corners = {
            "TL": (0, 0),
            "TR": (w-1, 0),
            "BL": (0, h-1),
            "BR": (w-1, h-1)
        }
        #max_distance = min(w, h) * 0.75  # Threshold: 35% of size (increased for better detection)
        max_distance = 800
        

        centroids = []
        for cnt in contours:
            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            point = (cx, cy)
            centroids.append(point)
            #cv2.circle(img, point, 5, (255, 0, 255), 2)  # magenta

        #print(f"[DEBUG] Found {len(centroids)} centroids: {centroids}")
        #print(f"[DEBUG] Image corners: {image_corners}")
        #print(f"[DEBUG] Max distance threshold: {max_distance}")

        # Match best centroid to each corner (closest only)
        best_matches = {label: (None, float('inf')) for label in image_corners}

        for point in centroids:
            for label, corner in image_corners.items():
                dist = np.linalg.norm(np.array(point) - np.array(corner))
                #print(f"[DEBUG] Distance from {point} to {label} {corner}: {dist}")
                if dist < max_distance and dist < best_matches[label][1]:
                    best_matches[label] = (point, dist)
                    #print(f"[DEBUG] New best match for {label}: {point} (dist: {dist})")

        found_corners = {
            label: pt for label, (pt, dist) in best_matches.items() if pt is not None
        }

        #print(f"[DEBUG] Found corners: {found_corners}")

        # Ensure all 4 corners were found
        ordered_labels = ["TL", "TR", "BL", "BR"]
        ordered_points = []

        for lbl in ordered_labels:
            pt = found_corners.get(lbl)
            if pt is None:
                ordered_points.append((np.nan, np.nan))
            else:
                ordered_points.append(pt)

        success = all(
            isinstance(pt, (list, tuple)) and
            len(pt) == 2 and
            not np.isnan(pt[0]) and
            not np.isnan(pt[1])
            for pt in ordered_points
        )

        #print(f"[DEBUG] Success: {success}")
        #print(f"[DEBUG] Ordered points: {ordered_points}")

        if show_result:
            # Fix: Only draw circles for valid points
            for point in ordered_points:
                if not (np.isnan(point[0]) or np.isnan(point[1])):
                    cv2.circle(img, tuple(map(int, point)), 10, (0, 255, 0), 2)
            
            #print("Ordered Corners (TL, TR, BL, BR):", ordered_points)
            #cv2.imshow("Detected Corners", img)
            #cv2.imshow("Blue Mask", mask)
            #cv2.waitKey(0)
            #cv2.destroyAllWindows()

        return ordered_points, success

def select_points(image_path, num_points=4, max_height=900, max_width=1600):
    """
    Opens an image and allows the user to select points by clicking.
    Resizes the image to fit on screen if necessary.
    
    Parameters:
    image_path (str): Path to the image file
    num_points (int): Number of points to select (default is 4)
    max_height (int): Maximum height for display (default 900)
    max_width (int): Maximum width for display (default 1600)
    
    Returns:
    numpy.ndarray: Array of (x, y) coordinates of selected points in original image scale
    """
    print(f"[DEBUG] Type of current_img: {type(image_path)}")

    if isinstance(image_path, str):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image at {image_path}")
    elif isinstance(image_path, np.ndarray):
        img = image_path
    else:
        raise TypeError("image_input must be a file path (str) or a NumPy image")
        
    
    # Get original dimensions
    original_height, original_width = img.shape[:2]
    
    # Calculate scaling factor to fit on screen
    scale_width = min(1.0, max_width / original_width)
    scale_height = min(1.0, max_height / original_height)
    scale = min(scale_width, scale_height)
    
    # Resize image if needed
    if scale < 1.0:
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        img = cv2.resize(img, (new_width, new_height))
        print(f"Image resized from {original_width}x{original_height} to {new_width}x{new_height}")
    
    # Make a copy of the image for drawing
    img_copy = img.copy()
    
    # Flag to track if scaling was applied
    scaled = scale < 1.0
    
    # List to store the selected points
    points = []
    
    # Mouse callback function
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Add the point to our list
            points.append((x, y))
            
            # Draw a circle at the clicked position
            cv2.circle(img_copy, (x, y), 5, (0, 255, 0), -1)
            
            # Display the point number
            cv2.putText(img_copy, str(len(points)), (x+10, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Update the displayed image
            cv2.imshow("Image", img_copy)
            
            # If we've collected all points, print them
            if len(points) == num_points:
                print(f"All {num_points} points selected: {points}")
    
    # Create a window and set the mouse callback
    cv2.namedWindow("Image")
    cv2.setMouseCallback("Image", mouse_callback)
    
    # Display the image
    cv2.imshow("Image", img)
    
    # Wait until all points are selected or user presses ESC
    while len(points) < num_points:
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key
            break
    
    # Close all windows
    cv2.destroyAllWindows()
    
    # If we scaled the image, convert points back to original scale
    if scaled:
        scale_factor = 1.0 / scale
        original_points = [(int(x * scale_factor), int(y * scale_factor)) for x, y in points]
        return np.array(original_points)
    
    return np.array(points)

def main():
    # Initialize the analyzer
    analyzer = game()
    
    print("---- Using color-only board representation ----")
    # Simulate a series of board states
    test_board = chess.Board()
    
    # Store initial state
    initial_array = analyzer.board_to_color_array(test_board)
    print("Initial board (color array):")
    print(initial_array)
    
    # First move: e4
    test_board.push_san("e4")
    board1_array = analyzer.board_to_color_array(test_board)
    print("\nBoard after e4:")
    print(board1_array)
    move1 = analyzer.update_board(board1_array)
    print(f"Detected move: {move1}")
    
    # Second move: e5
    test_board.push_san("e5")
    board2_array = analyzer.board_to_color_array(test_board)
    print("\nBoard after e5:")
    print(board2_array)
    move2 = analyzer.update_board(board2_array)
    print(f"Detected move: {move2}")
    
    # Third move: Nf3
    test_board.push_san("Nf3")
    board3_array = analyzer.board_to_color_array(test_board)
    print("\nBoard after Nf3:")
    print(board3_array)
    move3 = analyzer.update_board(board3_array)
    print(f"Detected move: {move3}")
    
    # Get the PGN
    pgn = analyzer.get_pgn()
    print("\nFull PGN:")
    print(pgn)
    
    print("\n---- Example with auto turn inference ----")
    # Reset analyzer
    analyzer2 = game()
    
    # Create a new test board and make multiple moves
    test_board2 = chess.Board()
    test_board2.push_san("e4")
    test_board2.push_san("e5")
    test_board2.push_san("Nf3")
    
    # Show what happens when we detect this state directly
    # (skipping intermediate states)
    board_array = analyzer2.board_to_color_array(test_board2)
    print("Board after several moves:")
    print(board_array)
    
    # Process using automatic turn inference
    print("Processing with automatic turn inference...")
    move = analyzer2.process_move(board_array)
    print(f"Detected move: {move}")
    
    # Continue the game
    test_board2.push_san("Nc6")
    next_array = analyzer2.board_to_color_array(test_board2)
    print("\nBoard after Nc6:")
    print(next_array)
    
    # Process next move
    next_move = analyzer2.process_move(next_array)
    print(f"Detected move: {next_move}")
    
    # Get the PGN
    pgn2 = analyzer2.get_pgn()
    print("\nFull PGN:")
    print(pgn2)

def main(self, img1, img2):
    analyzer = game()
    current_board = []
    corners = []
    i = 1
    results = ""
    while i ==1:
        if current_board is None or len(current_board) == 0:
            current_board, corners  = self.analyze_chessboard(img1, auto_calib=False)
            print(current_board)
        else:
            board_array, _ = self.analyze_chessboard(img2, auto_calib=False, corners=corners)
            #print("Board representation (0=empty, 1=white, 2=black):")

            results = self.analyze_binary_board_state(analyzer, board_array)

            # Access the analysis results
            if results["detected_move"]:
                print(f"Move detected: {results['detected_move']}")
            else:
                print("No valid move detected")

            # The PGN so far
            print(results["pgn"])
            i = 2
    return results['detected_move']
if __name__ == "__main__":
    img1 = "chessboards/screen1.png"
    img2 = "chessboards/screen2.png"
    main(game, img1, img2)