from stockfish import Stockfish
import time
# Set the correct Stockfish binary path here
STOCKFISH_PATH = "/usr/games/stockfish"  # Change this based on your OS

stockfish = Stockfish(STOCKFISH_PATH)
stockfish.set_depth(18)  # Search depth (higher = stronger but slower)
stockfish.update_engine_parameters({
    "Threads": 2, 
    "Hash": 512,
    "Skill Level": 20  # 0 (weakest) to 20 (strongest)
})

def get_best_move(fen: str) -> str:
    """Takes a FEN string and returns the best move."""
    if not stockfish.is_fen_valid(fen):
        return "Invalid FEN position."
    
    # start timeing
    start_time = time.time()
    
    stockfish.set_fen_position(fen)
    best_move = stockfish.get_best_move()

    #End Timing
    end_time = time.time()
    computation_time = end_time - start_time

    return best_move, computation_time

# Example: Receiving a FEN position and getting the best move
fen_position = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"  # Initial position
print("Best Move:", get_best_move(fen_position))
# rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq     e2e4
# rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1  Starting position of chess board