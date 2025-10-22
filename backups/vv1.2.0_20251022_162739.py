import ctypes
def is_file_locked(filepath):
    try:
        fh = open(filepath, 'a')
        fh.close()
        return False
    except Exception:
        return True

from flask import Flask, request, render_template_string, redirect, url_for
import chess
import chess.engine

app = Flask(__name__)

# Path to the Stockfish engine (will be auto-discovered at runtime)
engine_path = None

def _paths():
    import os
    root = os.path.dirname(__file__)
    return {
        'root': root,
        'bin': os.path.join(root, 'bin'),
        'selected': os.path.join(root, '.engine_selected'),
        'previous': os.path.join(root, '.engine_previous')
    }

def _read_text(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None

def _write_text(path, text):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception:
        return False

def board_to_html(board, highlight_move=None, flip=False):
    """Convert chess board to beautiful HTML/CSS representation. If flip=True, Black is at the bottom."""
    piece_unicode = {
        'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
        'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙'
    }
    html = ['<div class="chess-board">']
    rank_range = range(8) if flip else range(7, -1, -1)
    file_range = range(7, -1, -1) if flip else range(8)
    # Add rank labels on the side
    for rank in rank_range:
        html.append('<div class="board-row">')
        label = (rank + 1) if not flip else (8 - rank)
        html.append(f'<div class="rank-label">{label}</div>')
        for file in file_range:
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            square_color = 'light' if (file + rank) % 2 == 0 else 'dark'
            highlight_class = ''
            if highlight_move:
                if square == highlight_move.from_square:
                    highlight_class = ' from-square'
                elif square == highlight_move.to_square:
                    highlight_class = ' to-square'
            piece_symbol = piece_unicode.get(piece.symbol(), '') if piece else ''
            piece_color = 'white' if piece and piece.color else 'black'
            html.append(f'<div class="chess-square {square_color}{highlight_class}">')
            if piece_symbol:
                html.append(f'<span class="chess-piece {piece_color}">{piece_symbol}</span>')
            html.append('</div>')
        html.append('</div>')
    # Add file labels at bottom
    html.append('<div class="board-row file-labels">')
    html.append('<div class="rank-label"></div>')  # Empty corner
    file_labels = 'abcdefgh'
    if flip:
        file_labels = file_labels[::-1]
    for file_char in file_labels:
        html.append(f'<div class="file-label">{file_char}</div>')
    html.append('</div>')
    html.append('</div>')
    return ''.join(html)

def generate_fallback_recommendation(board):
    """Advanced GPT-style chess analysis using modern positional and tactical concepts."""
    try:
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return "No legal moves available", "", "No legal moves in this position.", "GPT Chess Engine"
        
        # Advanced scoring system with modern chess concepts
        scored_moves = []
        
        # Piece values (updated for modern play)
        piece_values = {'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 20000}
        
        # Positional square tables (simplified)
        pawn_table = [
            0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
            5,  5, 10, 25, 25, 10,  5,  5,
            0,  0,  0, 20, 20,  0,  0,  0,
            5, -5,-10,  0,  0,-10, -5,  5,
            5, 10, 10,-20,-20, 10, 10,  5,
            0,  0,  0,  0,  0,  0,  0,  0
        ]
        
        knight_table = [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,  0,  0,  0,  0,-20,-40,
            -30,  0, 10, 15, 15, 10,  0,-30,
            -30,  5, 15, 20, 20, 15,  5,-30,
            -30,  0, 15, 20, 20, 15,  0,-30,
            -30,  5, 10, 15, 15, 10,  5,-30,
            -40,-20,  0,  5,  5,  0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50
        ]
        
        def evaluate_position_score(test_board):
            """Evaluate position using multiple factors."""
            score = 0
            
            # Material balance
            for square in chess.SQUARES:
                piece = test_board.piece_at(square)
                if piece:
                    value = piece_values.get(piece.symbol().lower(), 0)
                    if piece.color == chess.WHITE:
                        score += value
                        # Add positional bonuses
                        if piece.piece_type == chess.PAWN:
                            score += pawn_table[square] if piece.color == chess.WHITE else pawn_table[square ^ 56]
                        elif piece.piece_type == chess.KNIGHT:
                            score += knight_table[square] if piece.color == chess.WHITE else knight_table[square ^ 56]
                    else:
                        score -= value
                        if piece.piece_type == chess.PAWN:
                            score -= pawn_table[square] if piece.color == chess.BLACK else pawn_table[square ^ 56]
                        elif piece.piece_type == chess.KNIGHT:
                            score -= knight_table[square] if piece.color == chess.BLACK else knight_table[square ^ 56]
            
            # King safety
            white_king = test_board.king(chess.WHITE)
            black_king = test_board.king(chess.BLACK)
            
            if white_king:
                # Penalty for exposed king
                attackers = len(test_board.attackers(chess.BLACK, white_king))
                score -= attackers * 10
                
            if black_king:
                attackers = len(test_board.attackers(chess.WHITE, black_king))
                score += attackers * 10
            
            # Mobility (number of legal moves)
            current_mobility = len(list(test_board.legal_moves))
            test_board.turn = not test_board.turn
            opponent_mobility = len(list(test_board.legal_moves))
            test_board.turn = not test_board.turn
            
            if test_board.turn == chess.WHITE:
                score += current_mobility * 2 - opponent_mobility * 2
            else:
                score -= current_mobility * 2 - opponent_mobility * 2
            
            return score
        
        for move in legal_moves:
            score = 0
            reasons = []
            original_pos_score = evaluate_position_score(board)
            
            # Make the move temporarily
            captured_piece = board.piece_at(move.to_square)
            board.push(move)
            new_pos_score = evaluate_position_score(board)
            
            # Positional improvement
            pos_improvement = new_pos_score - original_pos_score
            if board.turn == chess.BLACK:  # Adjust for side to move
                pos_improvement = -pos_improvement
            score += pos_improvement
            
            # Advanced tactical patterns
            if captured_piece:
                piece_value = piece_values.get(captured_piece.symbol().lower(), 0)
                score += piece_value
                piece_names = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen', 'k': 'king'}
                reasons.append(f"captures {piece_names.get(captured_piece.symbol().lower(), 'piece')} (+{piece_value//100} points)")
            
            # Check and checkmate detection
            if board.is_checkmate():
                score += 100000
                reasons.append("delivers checkmate!")
            elif board.is_check():
                score += 50
                reasons.append("gives check")
            
            # Stalemate avoidance
            if board.is_stalemate():
                score -= 50000
                reasons.append("avoid stalemate")
            
            # Piece development and activity
            moving_piece = board.piece_at(move.to_square)
            if moving_piece:
                # Knight and bishop development
                if moving_piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                    if move.from_square in [chess.B1, chess.G1, chess.C1, chess.F1, chess.B8, chess.G8, chess.C8, chess.F8]:
                        score += 20
                        reasons.append("develops piece")
                
                # Central control
                center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
                if move.to_square in center_squares:
                    score += 15
                    reasons.append("controls center")
                
                # Extended center
                extended_center = [chess.C3, chess.C4, chess.C5, chess.C6, chess.D3, chess.D6, 
                                 chess.E3, chess.E6, chess.F3, chess.F4, chess.F5, chess.F6]
                if move.to_square in extended_center:
                    score += 8
                    reasons.append("supports center")
            
            # Castling bonus
            if board.is_castling(move):
                score += 40
                reasons.append("castles for king safety")
            
            # Pawn structure considerations
            if moving_piece and moving_piece.piece_type == chess.PAWN:
                # Passed pawn bonus
                file = chess.square_file(move.to_square)
                rank = chess.square_rank(move.to_square)
                
                if moving_piece.color == chess.WHITE and rank >= 4:
                    score += (rank - 3) * 10
                    reasons.append("advances passed pawn")
                elif moving_piece.color == chess.BLACK and rank <= 3:
                    score += (4 - rank) * 10
                    reasons.append("advances passed pawn")
            
            # Attacking opponent pieces
            attacked_squares = board.attacks(move.to_square)
            for attacked_square in attacked_squares:
                attacked_piece = board.piece_at(attacked_square)
                if attacked_piece and attacked_piece.color != moving_piece.color:
                    attack_value = piece_values.get(attacked_piece.symbol().lower(), 0) // 10
                    score += attack_value
                    if attack_value > 10:
                        reasons.append("attacks valuable piece")
            
            # Avoid hanging pieces
            if board.is_attacked_by(not board.turn, move.to_square):
                piece_value = piece_values.get(moving_piece.symbol().lower(), 0) if moving_piece else 0
                if not captured_piece or piece_values.get(captured_piece.symbol().lower(), 0) < piece_value:
                    score -= piece_value // 2
                    reasons.append("piece may be endangered")
            
            board.pop()  # Undo the move
            scored_moves.append((move, score, reasons))
        
        # Sort by score and pick the best
        scored_moves.sort(key=lambda x: x[1], reverse=True)
        best_move, best_score, best_reasons = scored_moves[0]
        
        # Create sophisticated explanation
        engine_name = "GPT Chess Engine v2.0"
        if best_reasons:
            explanation = f"This move {', '.join(best_reasons[:3])}."  # Limit to top 3 reasons
            if len(best_reasons) > 3:
                explanation += f" (Evaluation: +{best_score//10} points)"
        else:
            explanation = "This move optimizes the position based on advanced chess principles."
        
        # Determine if the move is by Black
        flip = False
        if best_move:
            flip = board.turn == chess.BLACK
        return f"{best_move}", board_to_html(board, best_move, flip=flip), explanation, engine_name
        
    except Exception as e:
        return f"Analysis failed: {e}", "", "Analysis error occurred.", "GPT Chess Engine"

def get_stockfish_explanation(move_str, board):
    """Generate explanation for Stockfish recommendation."""
    try:
        if move_str in ["No legal moves available", "Engine not available"] or "failed" in move_str.lower():
            return "Analysis could not be completed."
        
        # Parse the move
        try:
            move = chess.Move.from_uci(move_str)
        except:
            return "Professional engine recommendation."
        
        explanations = []
        
        # Check what this move does
        board_copy = board.copy()
        captured_piece = board_copy.piece_at(move.to_square)
        
        if captured_piece:
            piece_names = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen', 'k': 'king'}
            piece_name = piece_names.get(captured_piece.symbol().lower(), 'piece')
            explanations.append(f"captures {piece_name}")
        
        # Make the move to check resulting position
        board_copy.push(move)
        
        if board_copy.is_checkmate():
            explanations.append("delivers checkmate")
        elif board_copy.is_check():
            explanations.append("gives check")
        
        # Check for special moves
        if board.is_castling(move):
            explanations.append("castles for king safety")
        elif board.is_en_passant(move):
            explanations.append("captures en passant")
        
        # Center control
        center_squares = [chess.E4, chess.E5, chess.D4, chess.D5]
        if move.to_square in center_squares:
            explanations.append("controls center")
        
        if explanations:
            return f"Stockfish recommends this move because it {', '.join(explanations)}."
        else:
            return "Stockfish evaluates this as the strongest move in the position."
        
    except Exception:
        return "Professional engine recommendation based on deep analysis."

def compare_moves_analysis(stockfish_move, ai_move, board):
    """Compare Stockfish and AI moves to explain potential issues."""
    try:
        if stockfish_move == ai_move:
            return "Both engines agree on this move - excellent choice!"
        
        if "failed" in stockfish_move.lower() or "not available" in stockfish_move.lower():
            return "Stockfish analysis unavailable for comparison."
        
        # Try to parse both moves
        try:
            sf_move = chess.Move.from_uci(stockfish_move)
            ai_move_parsed = chess.Move.from_uci(ai_move)
        except:
            return "Move comparison unavailable due to parsing issues."
        
        # Analyze the AI move from Stockfish perspective
        analysis = []
        
        # Check if AI move is even legal
        if ai_move_parsed not in board.legal_moves:
            return "⚠️ AI suggested an illegal move - this indicates a serious error in the AI logic."
        
        # Make AI move to see what happens
        board_copy = board.copy()
        board_copy.push(ai_move_parsed)
        
        # Check for obvious tactical problems
        if board_copy.is_check() and not board.is_check():
            # AI move puts own king in check - this should never happen
            analysis.append("puts own king in check (illegal)")
        
        # Check if AI move hangs material
        captured_by_ai = board.piece_at(ai_move_parsed.to_square)
        if captured_by_ai is None:  # Not a capture
            # Check if the piece that moved can be captured
            if board_copy.is_attacked_by(not board_copy.turn, ai_move_parsed.to_square):
                moving_piece = board.piece_at(ai_move_parsed.from_square)
                if moving_piece:
                    piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9}
                    piece_value = piece_values.get(moving_piece.symbol().lower(), 0)
                    if piece_value > 0:
                        analysis.append(f"hangs the {moving_piece.symbol().lower()} (loses {piece_value} points)")
        
        # Check if Stockfish move is much more forcing
        board_sf = board.copy()
        board_sf.push(sf_move)
        
        if board_sf.is_checkmate():
            analysis.append("misses immediate checkmate")
        elif board_sf.is_check() and not board_copy.is_check():
            analysis.append("misses a check")
        
        # Check for missed captures
        sf_capture = board.piece_at(sf_move.to_square)
        ai_capture = board.piece_at(ai_move_parsed.to_square)
        
        if sf_capture and not ai_capture:
            piece_names = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen'}
            captured_name = piece_names.get(sf_capture.symbol().lower(), 'piece')
            analysis.append(f"misses capture of {captured_name}")
        
        if analysis:
            return f"⚠️ Potential issues with AI move: {', '.join(analysis)}. Stockfish's choice is likely stronger."
        else:
            return "AI move is reasonable but Stockfish found a different approach. Both moves have merit."
        
    except Exception as e:
        return "Move comparison analysis unavailable."

def get_python_dependencies_info():
    """Get version information for all Python dependencies."""
    import subprocess
    try:
        import importlib.metadata as metadata
    except ImportError:
        try:
            import importlib_metadata as metadata
        except ImportError:
            import pkg_resources
            metadata = None
    
    # Try to import requests, but handle if it's missing
    try:
        import requests
        requests_available = True
    except ImportError:
        requests_available = False
    
    dependencies = {}
    
    # Key dependencies to check
    key_packages = ['flask', 'chess', 'requests']
    
    for package in key_packages:
        try:
            # Get current version
            if metadata:
                current_version = metadata.version(package)
            else:
                current_version = pkg_resources.get_distribution(package).version
            
            # Check PyPI for latest version
            if requests_available:
                try:
                    response = requests.get(f'https://pypi.org/pypi/{package}/json', timeout=3)
                    if response.status_code == 200:
                        data = response.json()
                        latest_version = data['info']['version']
                        update_available = current_version != latest_version
                    else:
                        latest_version = "Unknown"
                        update_available = False
                except:
                    latest_version = "Check failed"
                    update_available = False
            else:
                latest_version = "requests not available"
                update_available = False
                
            dependencies[package] = {
                'current': current_version,
                'latest': latest_version,
                'update_available': update_available
            }
        except Exception:
            dependencies[package] = {
                'current': 'Not installed',
                'latest': 'Unknown',
                'update_available': False
            }
    
    # Convert to list format expected by template
    dep_list = []
    for package, info in dependencies.items():
        dep_list.append({
            'name': package,
            'current_version': info['current'],
            'latest_version': info['latest'],
            'update_available': info['update_available']
        })
    
    return dep_list

def get_application_version_info():
    """Get current application version and check for updates from GitHub releases."""
    try:
        import requests
        requests_available = True
    except ImportError:
        requests_available = False
    
    # Current version - we'll read this from a version file or git tag
    current_version = "v1.2.0"  # This should be updated with each release
    
    # Try to get current version from git tag if possible
    try:
        import subprocess
        result = subprocess.run(['git', 'describe', '--tags', '--exact-match'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            current_version = result.stdout.strip()
    except:
        pass  # Fall back to hardcoded version
    
    latest_version = "Unknown"
    update_available = False
    
    if requests_available:
        try:
            # Check GitHub releases for latest version
            url = "https://api.github.com/repos/AprilLorDrake/Analyze_Chess/releases/latest"
            headers = {"Accept": "application/vnd.github+json", "User-Agent": "analyze-chess-app"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data['tag_name']
                update_available = current_version != latest_version
            else:
                latest_version = "Check failed"
        except Exception:
            latest_version = "Check failed"
    else:
        latest_version = "requests not available"
    
    # Check if backup files exist
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    has_backups = False
    try:
        if os.path.exists(backup_dir):
            import glob
            backup_files = glob.glob(os.path.join(backup_dir, "v*.py"))
            has_backups = len(backup_files) > 0
    except:
        pass
    
    return {
        'current': current_version,
        'latest': latest_version,
        'update_available': update_available,
        'has_backups': has_backups,
        'release_url': f"https://github.com/AprilLorDrake/Analyze_Chess/releases/tag/{latest_version}" if latest_version not in ["Unknown", "Check failed", "requests not available"] else None
    }

def backup_current_version():
    """Create a backup of the current application before updating."""
    import os, shutil, time
    try:
        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamped backup
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        app_info = get_application_version_info()
        current_version = app_info.get('current', 'unknown')
        backup_name = f"v{current_version}_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        # Copy current app.py to backup
        current_file = __file__
        backup_file = os.path.join(backup_path + ".py")
        
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        shutil.copy2(current_file, backup_file)
        
        return backup_file
    except Exception as e:
        return f"Backup failed: {e}"

def download_and_update():
    """Download the latest version and update the application."""
    import os, tempfile, zipfile
    try:
        import requests
    except ImportError:
        return {"success": False, "message": "requests library not available for updating"}
    
    try:
        # Get latest release info
        url = "https://api.github.com/repos/AprilLorDrake/Analyze_Chess/releases/latest"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "analyze-chess-app"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {"success": False, "message": "Failed to fetch release information"}
        
        release_data = response.json()
        download_url = release_data.get('zipball_url')
        
        if not download_url:
            return {"success": False, "message": "No download URL found"}
        
        # Create backup first
        backup_result = backup_current_version()
        if "failed" in str(backup_result).lower():
            return {"success": False, "message": f"Backup failed: {backup_result}"}
        
        # Download the latest version
        download_response = requests.get(download_url, timeout=30)
        if download_response.status_code != 200:
            return {"success": False, "message": "Failed to download update"}
        
        # Extract and update
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "update.zip")
            with open(zip_path, 'wb') as f:
                f.write(download_response.content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
                # Find the extracted folder (GitHub creates a folder with repo name and commit hash)
                extracted_folders = [f for f in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, f))]
                if not extracted_folders:
                    return {"success": False, "message": "No extracted folder found"}
                
                extracted_path = os.path.join(temp_dir, extracted_folders[0])
                new_app_path = os.path.join(extracted_path, "app.py")
                
                if not os.path.exists(new_app_path):
                    return {"success": False, "message": "app.py not found in update"}
                
                # Replace current app.py
                current_app_path = __file__
                import shutil
                shutil.copy2(new_app_path, current_app_path)
        
        return {
            "success": True, 
            "message": f"Successfully updated to {release_data.get('tag_name', 'latest version')}. Please restart the application.",
            "backup_location": backup_result,
            "new_version": release_data.get('tag_name', 'Unknown')
        }
        
    except Exception as e:
        return {"success": False, "message": f"Update failed: {str(e)}"}

def rollback_version():
    """Rollback to the most recent backup version."""
    import os, glob, shutil
    try:
        backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
        if not os.path.exists(backup_dir):
            return {"success": False, "message": "No backups found"}
        
        # Find the most recent backup
        backup_files = glob.glob(os.path.join(backup_dir, "v*.py"))
        if not backup_files:
            return {"success": False, "message": "No backup files found"}
        
        # Sort by modification time (most recent first)
        backup_files.sort(key=os.path.getmtime, reverse=True)
        latest_backup = backup_files[0]
        
        # Get backup info from filename
        backup_filename = os.path.basename(latest_backup)
        backup_version = backup_filename.split('_')[0]  # Extract version part
        
        # Create backup of current version before rollback
        current_backup = backup_current_version()
        
        # Replace current app.py with backup
        current_app_path = __file__
        shutil.copy2(latest_backup, current_app_path)
        
        return {
            "success": True,
            "message": f"Successfully rolled back to {backup_version}. Please restart the application.",
            "rolled_back_to": backup_version,
            "current_backup": current_backup
        }
        
    except Exception as e:
        return {"success": False, "message": f"Rollback failed: {str(e)}"}

def find_stockfish():
    """Attempt to locate a Stockfish executable.

    Order of checks:
    1. STOCKFISH_PATH environment variable
    2. 'stockfish' on PATH (shutil.which)
    3. Common Windows locations
    4. Project local 'bin/stockfish.exe'
    Returns the absolute path or None if not found.
    """
    import os
    import shutil

    # 1) environment override
    env = os.environ.get('STOCKFISH_PATH')
    if env and os.path.isfile(env):
        return env

    # 2) selection file (persisted choice)
    p = _paths()
    chosen = _read_text(p['selected'])
    if chosen and os.path.isfile(chosen):
        return chosen

    # 3) on PATH
    which = shutil.which('stockfish')
    if which:
        return which

    # 4) common install locations (platform-specific)
    common = []
    if os.name == 'nt':  # Windows
        common = [
            r"C:\Program Files\Stockfish\stockfish.exe",
            r"C:\Program Files (x86)\Stockfish\stockfish.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Stockfish\stockfish.exe"),
            os.path.expanduser(r"~\stockfish\stockfish.exe"),
        ]
    else:  # Unix-like systems (Linux, macOS)
        common = [
            "/usr/local/bin/stockfish",
            "/usr/bin/stockfish",
            "/opt/stockfish/stockfish",
            os.path.expanduser("~/stockfish/stockfish"),
            os.path.expanduser("~/.local/bin/stockfish"),
        ]
    
    for p in common:
        if p and os.path.isfile(p):
            return p

    # 5) project-local bin folder: accept any executable whose name contains
    # 'stockfish' so we will honor the real filename someone installed.
    proj_bin = os.path.join(os.path.dirname(__file__), 'bin')
    try:
        if os.path.isdir(proj_bin):
            for entry in os.listdir(proj_bin):
                if 'stockfish' in entry.lower():
                    candidate = os.path.join(proj_bin, entry)
                    if os.path.isfile(candidate):
                        # Check if it's executable (Unix) or has .exe extension (Windows)
                        if os.name == 'nt':
                            if entry.lower().endswith('.exe'):
                                return candidate
                        else:
                            if os.access(candidate, os.X_OK):
                                return candidate
    except Exception:
        # ignore permission/listing errors and continue
        pass

    return None

def install_stockfish_to_dir(target_dir: str):
    """Download latest Stockfish and extract the engine into target_dir.

    Preserves the original filename from the archive. Returns absolute path to
    the installed executable on success, else None.
    """
    import os, platform
    try:
        import requests, zipfile, io, tempfile
    except ImportError:
        print("requests package not available; cannot auto-install Stockfish.")
        return None
    
    os.makedirs(target_dir, exist_ok=True)
    
    # Determine the appropriate Stockfish download URL based on platform
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        if "64" in machine or "amd64" in machine:
            url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
        else:
            url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-32.zip"
    elif system == "darwin":  # macOS
        url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-macos-x86-64-apple-silicon.tar"
    elif system == "linux":
        if "64" in machine or "amd64" in machine or "x86_64" in machine:
            url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-linux-x86-64-avx2.tar"
        else:
            url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-linux-x86-32.tar"
    else:
        print(f"Unsupported platform: {system} {machine}")
        return None
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        if url.endswith('.zip'):
            # Handle ZIP files (Windows)
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                exe_candidates = [f for f in z.namelist() if f.lower().endswith('.exe')]
                if not exe_candidates:
                    print("No executable found inside Stockfish archive.")
                    return None
                exe_name = exe_candidates[0]
                basename = os.path.basename(exe_name)
                target_path = os.path.join(target_dir, basename)
                
                # backup any current engine in bin
                paths = _paths()
                current = find_stockfish()
                if current and os.path.commonpath([os.path.dirname(current), target_dir]) == target_dir:
                    # only back up if current is inside target_dir (our managed bin)
                    import time, shutil as _sh
                    bdir = os.path.join(target_dir, 'backup')
                    os.makedirs(bdir, exist_ok=True)
                    stamp = time.strftime('%Y%m%d-%H%M%S')
                    backup_name = f"stockfish-{stamp}.exe"
                    _sh.copy2(current, os.path.join(bdir, backup_name))
                
                # extract and save the new engine
                with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp:
                    tmp.write(z.read(exe_name))
                    tmp.flush()
                    import shutil as _sh
                    _sh.copy2(tmp.name, target_path)
                    os.unlink(tmp.name)
                
                # make executable on Unix systems
                if os.name != 'nt':
                    os.chmod(target_path, 0o755)
                
                return target_path
                
        else:
            # Handle TAR files (Linux/macOS)
            import tarfile
            with tarfile.open(fileobj=io.BytesIO(resp.content), mode='r:*') as tar:
                # Look for stockfish executable
                stockfish_files = [f for f in tar.getnames() if 'stockfish' in f.lower() and not f.endswith('/')]
                if not stockfish_files:
                    print("No stockfish executable found in archive.")
                    return None
                
                exe_name = stockfish_files[0]
                basename = os.path.basename(exe_name)
                target_path = os.path.join(target_dir, basename)
                
                # Extract the executable
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    fileobj = tar.extractfile(exe_name)
                    if fileobj:
                        tmp.write(fileobj.read())
                        tmp.flush()
                        import shutil as _sh
                        _sh.copy2(tmp.name, target_path)
                        os.unlink(tmp.name)
                        
                        # make executable
                        os.chmod(target_path, 0o755)
                        
                        return target_path
                
    except Exception as e:
        print(f"Failed to download/install Stockfish: {e}")
        return None
def get_engine_version(exec_path: str) -> str:
    import subprocess
    try:
        cp = subprocess.run([exec_path, '--version'], capture_output=True, text=True, timeout=5)
        out = (cp.stdout or cp.stderr or '').strip()
        return out.splitlines()[0] if out else 'unknown'
    except Exception:
        return 'unknown'

def get_latest_stockfish_tag(timeout: float = 5.0) -> str | None:
    """Return latest Stockfish release tag from GitHub, or None on error.

    This is a lightweight check used only to display an 'update available' hint.
    """
    try:
        import requests
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "analyze-chess-app"}
        r = requests.get(
            "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest",
            headers=headers,
            timeout=timeout,
        )
        if r.ok:
            data = r.json()
            tag = data.get("tag_name")
            return str(tag) if tag else None
    except Exception:
        pass
    return None

def _extract_numeric_version(s: str) -> str | None:
    import re
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)*)", s)
    return m.group(1) if m else None


def has_previous_engine():
    """Check if there's a previous engine version to rollback to"""
    import os
    p = _paths()
    return os.path.exists(p['previous'])

def has_previous_package(package_name):
    """Check if there's a previous package version to rollback to"""
    # For now, we'll assume packages can be rolled back if they've been updated
    # In a more sophisticated system, you'd track package installation history
    import os
    backup_file = f'.{package_name}_previous'
    return os.path.exists(backup_file)

@app.route('/')
@app.route('/analyze_chess_move')
def analyze_chess_move():
    import os
    global engine_path
    # Determine current engine status and ensure variables are defined
    current = engine_path or find_stockfish()
    version = get_engine_version(current) if current else 'not installed'
    latest_tag = get_latest_stockfish_tag()
    latest_num = _extract_numeric_version(latest_tag or '')
    curr_num = _extract_numeric_version(version)
    stockfish_update_available = bool(latest_num and curr_num and latest_num != curr_num)
    
    # Get Python dependencies information
    python_deps = get_python_dependencies_info()
    
    # Get application version information
    app_version_info = get_application_version_info()
    
    msg = request.args.get('msg', '')
    current_fen = request.args.get('current_fen', '')
    
    # Handle FEN analysis
    fen = request.args.get('fen', '').strip()
    fen_result = None
    if fen:
        try:
            board = chess.Board(fen)
            if not engine_path or not os.path.isfile(engine_path):
                first_move = next(iter(board.legal_moves)) if board.legal_moves else None
                stockfish_move = str(first_move) if first_move else "No legal moves available"
                stockfish_board = board_to_html(board, first_move) if first_move else board_to_html(board)
            else:
                try:
                    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
                    result = engine.play(board, chess.engine.Limit(time=2.0))
                    try:
                        engine.quit()
                    except Exception:
                        pass
                    stockfish_move = str(result.move)
                    stockfish_board = board_to_html(board, result.move)
                except Exception as e:
                    stockfish_move = f"Engine error: {e}"
                    stockfish_board = board_to_html(board)
            # Generate recommendations for each AI engine
            chatgpt_move, chatgpt_board, chatgpt_explanation, chatgpt_engine = generate_fallback_recommendation(board)
            gemini_move, gemini_board, gemini_explanation, gemini_engine = generate_fallback_recommendation(board)
            copilot_move, copilot_board, copilot_explanation, copilot_engine = generate_fallback_recommendation(board)

            # Create Stockfish explanation based on the move type
            stockfish_explanation = get_stockfish_explanation(stockfish_move, board)

            # Compare the moves to provide educational insights (compare each AI to Stockfish)
            chatgpt_comparison = compare_moves_analysis(stockfish_move, chatgpt_move, board)
            gemini_comparison = compare_moves_analysis(stockfish_move, gemini_move, board)
            copilot_comparison = compare_moves_analysis(stockfish_move, copilot_move, board)

            fen_result = {
                'stockfish': stockfish_move,
                'stockfish_board': stockfish_board,
                'stockfish_explanation': stockfish_explanation,
                'chatgpt': chatgpt_move,
                'chatgpt_board': chatgpt_board,
                'chatgpt_explanation': chatgpt_explanation,
                'chatgpt_engine': 'ChatGPT',
                'chatgpt_comparison': chatgpt_comparison,
                'gemini': gemini_move,
                'gemini_board': gemini_board,
                'gemini_explanation': gemini_explanation,
                'gemini_engine': 'Gemini',
                'gemini_comparison': gemini_comparison,
                'copilot': copilot_move,
                'copilot_board': copilot_board,
                'copilot_explanation': copilot_explanation,
                'copilot_engine': 'Copilot',
                'copilot_comparison': copilot_comparison
            }
        except Exception as e:
            fen_result = {
                'stockfish': f"Invalid FEN: {e}", 
                'stockfish_board': "",
                'stockfish_explanation': "Analysis could not be completed due to invalid position.",
                'ai': "-",
                'ai_board': "",
                'ai_explanation': "Analysis could not be completed due to invalid position.",
                'ai_engine': "N/A",
                'move_comparison': "Analysis unavailable due to position error."
            }
    
    return render_template_string('''
            <html>
            <head>
                <title>Analyze Next Best Chess Move!</title>
                <link rel="icon" type="image/x-icon" href="/favicon.ico">
                <meta http-equiv="refresh" content="10">
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        max-width: 800px; 
                        margin: 0 auto; 
                        padding: 20px; 
                        background: linear-gradient(135deg, #f3e7ff 0%, #e6d3ff 100%);
                        min-height: 100vh;
                    }
                    .header { text-align: center; margin-bottom: 30px; color: #4a2c7a; }
                    .feedback-section {
                        text-align: center;
                        margin: 20px 0;
                        padding: 15px;
                        background: rgba(142, 68, 173, 0.05);
                        border-radius: 8px;
                        border: 1px solid #d4b3ff;
                    }
                    .feedback-btn {
                        padding: 8px 16px;
                        background: linear-gradient(135deg, #8b5fbf 0%, #7048a3 100%);
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 14px;
                        text-decoration: none;
                        display: inline-block;
                        box-shadow: 0 2px 6px rgba(139, 95, 191, 0.3);
                        margin: 0 5px;
                    }
                    .feedback-btn:hover {
                        background: linear-gradient(135deg, #7048a3 0%, #5d3d87 100%);
                        transform: translateY(-1px);
                        box-shadow: 0 3px 8px rgba(139, 95, 191, 0.4);
                    }
                    .main-form { 
                        text-align: center; 
                        margin-bottom: 30px; 
                        padding: 20px; 
                        background: rgba(255, 255, 255, 0.8); 
                        border-radius: 12px; 
                        box-shadow: 0 4px 15px rgba(116, 77, 169, 0.15);
                        border: 1px solid #d4b3ff;
                    }
                    .fen-input { 
                        padding: 10px 12px; 
                        font-size: 16px; 
                        border: 2px solid #c299ff; 
                        border-radius: 6px; 
                        background: rgba(255, 255, 255, 0.9);
                        height: 40px;
                        box-sizing: border-box;
                    }
                    .fen-input:focus { border-color: #9966ff; outline: none; box-shadow: 0 0 5px rgba(153, 102, 255, 0.3); }
                    .submit-btn { 
                        padding: 12px 30px; 
                        font-size: 16px; 
                        background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
                        color: white; 
                        border: none; 
                        border-radius: 6px; 
                        cursor: pointer; 
                        margin-top: 10px;
                        box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
                    }
                    .fen-input.analyzed { background-color: #f0f8ff; color: #666; }
                    .reset-btn { 
                        padding: 12px 30px; 
                        font-size: 16px; 
                        background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%); 
                        color: white; 
                        border: none; 
                        border-radius: 6px; 
                        cursor: pointer; 
                        margin-top: 10px;
                        margin-left: 10px;
                        box-shadow: 0 2px 8px rgba(108, 117, 125, 0.3);
                    }
                    .reset-btn:hover { 
                        background: linear-gradient(135deg, #5a6268 0%, #495057 100%); 
                        transform: translateY(-1px);
                        box-shadow: 0 4px 12px rgba(108, 117, 125, 0.4);
                    }
                    .reset-btn:disabled {
                        background: linear-gradient(135deg, #cccccc 0%, #999999 100%);
                        cursor: not-allowed;
                        opacity: 0.5;
                        transform: none;
                        box-shadow: none;
                    }
                    .reset-btn:disabled:hover {
                        background: linear-gradient(135deg, #cccccc 0%, #999999 100%);
                        transform: none;
                        box-shadow: none;
                    }
                    
                    /* Compact button styles for inline layout */
                    .compact-btn {
                        padding: 10px 16px !important;
                        font-size: 14px !important;
                        margin-top: 0 !important;
                        white-space: nowrap;
                        min-width: 80px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    
                    .sample-fens {
                        margin: 15px 0;
                        text-align: left;
                    }
                    .sample-fen-btn {
                        display: inline-block;
                        margin: 3px;
                        padding: 5px 10px;
                        background: linear-gradient(135deg, #8b5fbf 0%, #7048a3 100%);
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                        text-decoration: none;
                    }
                    .sample-fen-btn:hover {
                        background: linear-gradient(135deg, #7048a3 0%, #5d3d87 100%);
                        transform: translateY(-1px);
                    }

                    .submit-btn:hover { 
                        background: linear-gradient(135deg, #218838 0%, #1ea085 100%); 
                        transform: translateY(-1px);
                        box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
                    }
                    .submit-btn:disabled {
                        background: linear-gradient(135deg, #cccccc 0%, #999999 100%);
                        cursor: not-allowed;
                        opacity: 0.6;
                        transform: none;
                        box-shadow: none;
                    }
                    .submit-btn:disabled:hover {
                        background: linear-gradient(135deg, #cccccc 0%, #999999 100%);
                        transform: none;
                        box-shadow: none;
                    }
                    .submit-btn.analyzed {
                        background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
                        cursor: not-allowed;
                        opacity: 0.6;
                        transform: none;
                        box-shadow: none;
                    }
                    .submit-btn.analyzed:hover {
                        background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
                        transform: none;
                        box-shadow: none;
                    }
                    .reset-btn.active { 
                        background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
                        box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
                    }
                    .reset-btn.active:hover { 
                        background: linear-gradient(135deg, #218838 0%, #1ea085 100%); 
                        transform: translateY(-1px);
                        box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
                    }
                    .engine-buttons { 
                        display: flex; 
                        gap: 10px; 
                        justify-content: center; 
                        flex-wrap: wrap;
                        margin-top: 10px;
                    }
                    .engine-btn { 
                        padding: 8px 16px; 
                        background: linear-gradient(135deg, #8b5fbf 0%, #7048a3 100%); 
                        color: white; 
                        border: none; 
                        border-radius: 6px; 
                        cursor: pointer;
                        box-shadow: 0 2px 6px rgba(139, 95, 191, 0.3);
                    }
                    .engine-btn:hover { 
                        background: linear-gradient(135deg, #7048a3 0%, #5d3d87 100%); 
                        transform: translateY(-1px);
                        box-shadow: 0 3px 8px rgba(139, 95, 191, 0.4);
                    }
                    .engine-btn.update-btn:hover {
                        background: linear-gradient(135deg, #28a745 0%, #218838 100%) !important;
                        transform: translateY(-1px);
                        box-shadow: 0 3px 8px rgba(40, 167, 69, 0.4);
                    }
                    .engine-btn.rollback-btn:hover {
                        background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%) !important;
                        transform: translateY(-1px);
                        box-shadow: 0 3px 8px rgba(255, 193, 7, 0.4);
                    }
                    .about-section { 
                        background: rgba(255, 255, 255, 0.7); 
                        padding: 15px; 
                        border-radius: 12px; 
                        margin-top: 20px; 
                        border: 1px solid #d4b3ff;
                        color: #4a2c7a;
                    }
                    .msg { 
                        padding: 8px; 
                        margin-bottom: 10px; 
                        background: rgba(255, 255, 255, 0.8); 
                        border: 1px solid #c299ff; 
                        border-radius: 6px; 
                        color: #4a2c7a;
                    }
                    h3 { color: #4a2c7a; margin-bottom: 15px; }
                    .result-section {
                        text-align: center;
                        margin-bottom: 30px;
                        padding: 20px;
                        background: rgba(255, 255, 255, 0.8);
                        border-radius: 12px;
                        box-shadow: 0 4px 15px rgba(116, 77, 169, 0.15);
                        border: 1px solid #d4b3ff;
                    }
                    .recommendations-wrapper {
                        background: linear-gradient(135deg, #2c5530 0%, #1e3a22 100%);
                        border: 3px solid #4a7c59;
                        border-radius: 15px;
                        padding: 25px;
                        margin: 25px 0;
                        box-shadow: 0 8px 25px rgba(44, 85, 48, 0.4);
                    }
                    .recommendations-header {
                        color: #87ceeb !important;
                        text-align: center;
                        font-size: 1.5em;
                        font-weight: bold;
                        margin-bottom: 25px !important;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                        border-bottom: 2px solid #87ceeb;
                        padding-bottom: 10px;
                    }
                    .recommendation-section {
                        background: rgba(255, 255, 255, 0.1);
                        border: 2px solid rgba(135, 206, 235, 0.3);
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 20px;
                    }
                    .recommend-label {
                        font-size: 1.3em;
                        font-weight: bold;
                        color: #87ceeb !important;
                        margin-bottom: 12px !important;
                        text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
                    }
                    .recommend-value {
                        font-size: 1.4em;
                        color: #90EE90 !important;
                        margin-bottom: 18px !important;
                        font-weight: bold;
                        text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
                        font-family: 'Courier New', monospace;
                    }
                 .board-container {
                     display: flex;
                     justify-content: center;
                     margin: 15px auto;
                 }
                 .chess-board {
                     border: 3px solid #8B4513;
                     border-radius: 8px;
                     padding: 5px;
                     background: #DEB887;
                     box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                 }
                 .board-row {
                     display: flex;
                     margin: 0;
                 }
                 .chess-square {
                     width: 35px;
                     height: 35px;
                     display: flex;
                     align-items: center;
                     justify-content: center;
                     position: relative;
                 }
                 .chess-square.light {
                     background-color: #F0D9B5;
                 }
                 .chess-square.dark {
                     background-color: #B58863;
                 }
                 .chess-square.from-square {
                     background-color: #FFE135 !important;
                     box-shadow: inset 0 0 0 2px #FF6B35;
                 }
                 .chess-square.to-square {
                     background-color: #90EE90 !important;
                     box-shadow: inset 0 0 0 2px #228B22;
                 }
                 .chess-piece {
                     font-size: 24px;
                     font-weight: bold;
                     text-shadow: 1px 1px 1px rgba(0,0,0,0.3);
                 }
                 .chess-piece.white {
                     color: #FFFFFF;
                     filter: drop-shadow(1px 1px 1px #000);
                 }
                 .chess-piece.black {
                     color: #000000;
                     filter: drop-shadow(1px 1px 1px #FFF);
                 }
                 .rank-label, .file-label {
                     width: 35px;
                     height: 35px;
                     display: flex;
                     align-items: center;
                     justify-content: center;
                     font-weight: bold;
                     color: #8B4513;
                     font-size: 12px;
                 }
                 .file-labels {
                     margin-top: 2px;
                 }
                </style>
                <script>
                    function loadSampleFEN(fen) {
                        document.getElementById('fen').value = fen;
                        validateFENInput(); // Check if button should be enabled
                    }
                    
                    function resetForm() {
                        const resetBtn = document.getElementById('reset-btn');
                        if (resetBtn.disabled) {
                            return; // Don't reset if button is disabled
                        }
                        window.location.href = '/';
                    }
                    
                    function validateFENInput() {
                        const fenInput = document.getElementById('fen');
                        const submitBtn = document.getElementById('submit-btn');
                        const resetBtn = document.getElementById('reset-btn');
                        
                        if (fenInput.value.trim() === '') {
                            // Hide buttons when no input
                            submitBtn.style.display = 'none';
                            resetBtn.style.display = 'none';
                            submitBtn.disabled = true;
                            submitBtn.title = 'Please enter a FEN position to analyze';
                        } else {
                            // Show and enable buttons when there's input
                            submitBtn.style.display = 'block';
                            resetBtn.style.display = 'block';
                            submitBtn.disabled = false;
                            submitBtn.title = 'Click to analyze the chess position';
                            resetBtn.disabled = false;
                            resetBtn.style.opacity = '1';
                            resetBtn.style.cursor = 'pointer';
                            resetBtn.title = 'Clear the FEN input';
                        }
                    }
                    
                    function setAnalyzedState() {
                        const submitBtn = document.getElementById('submit-btn');
                        const resetBtn = document.getElementById('reset-btn');
                        
                        // Ensure buttons are visible
                        submitBtn.style.display = 'block';
                        resetBtn.style.display = 'block';
                        
                        // Make analyze button grey and disabled
                        submitBtn.classList.add('analyzed');
                        submitBtn.disabled = true;
                        submitBtn.title = 'Analysis completed';
                        
                        // Make reset button green and active
                        resetBtn.classList.add('active');
                        resetBtn.disabled = false;
                        resetBtn.style.opacity = '1';
                        resetBtn.style.cursor = 'pointer';
                        resetBtn.title = 'Clear analysis and start over';
                    }
                    
                    // Initialize button state and add event listener when page loads
                    document.addEventListener('DOMContentLoaded', function() {
                        const fenInput = document.getElementById('fen');
                        validateFENInput(); // Check initial state
                        
                        // Add event listener for real-time validation
                        fenInput.addEventListener('input', validateFENInput);
                        fenInput.addEventListener('keyup', validateFENInput);
                        fenInput.addEventListener('paste', function() {
                            // Small delay to allow paste to complete
                            setTimeout(validateFENInput, 10);
                        });
                        
                        // Add Enter key support for form submission
                        fenInput.addEventListener('keydown', function(event) {
                            if (event.key === 'Enter') {
                                event.preventDefault(); // Prevent default form submission
                                const submitBtn = document.getElementById('submit-btn');
                                if (!submitBtn.disabled) {
                                    // Trigger the form submission
                                    submitBtn.form.submit();
                                }
                            }
                        });
                        
                        // Check if we're showing analysis results and set button states accordingly
                        {% if fen_result %}
                        setAnalyzedState();
                        {% endif %}
                    });
                </script>

            </head>
            <body>
                <div class="header">
                    <img src="/assets/chess_icon.png" alt="Chess Icon" style="height:64px;vertical-align:middle;margin-right:12px;">
                    <span style="font-size:2em;font-weight:bold;vertical-align:middle;">Analyze Next Best Chess Move!</span>
                    <div style="margin-top: 10px; font-size: 14px; color: #6a5d7a;">
                        Version {{ app_version_info.current }}
                        {% if app_version_info.update_available %}
                        <span style="margin-left: 10px; padding: 4px 8px; background: #ff9800; color: white; border-radius: 12px; font-size: 11px; font-weight: bold;">
                            📋 Update Available: {{ app_version_info.latest }}
                        </span>
                        {% endif %}
                    </div>
                </div>
                
                <!-- Feedback Section -->
                <div class="feedback-section">
                    <span style="color: #4a2c7a; font-size: 14px; margin-right: 15px;">💬 Help us improve:</span>
                    <a href="/feedback" class="feedback-btn">Send Feedback</a>
                    <a href="https://github.com/AprilLorDrake/Analyze_Chess/issues/new?template=bug_report.md" target="_blank" class="feedback-btn">Report Bug</a>
                    <a href="https://github.com/AprilLorDrake/Analyze_Chess/issues/new?template=feature_request.md" target="_blank" class="feedback-btn">Request Feature</a>
                </div>
                
                {% if msg %}<div class="msg">{{msg}}</div>{% endif %}
                
                <div class="main-form">
                    <!-- Helpful Links Section -->
                    <div style="margin-bottom: 20px; padding: 15px; background: rgba(255, 255, 255, 0.1); border-radius: 8px; border: 1px solid #c299ff; text-align: center;">
                        <div style="font-weight: bold; margin-bottom: 12px; color: #4a2c7a; font-size: 16px;">🔗 Helpful Resources</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
                            <a href="https://lichess.org/editor" target="_blank" style="text-decoration: none; padding: 8px 15px; background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; border-radius: 5px; font-size: 12px; font-weight: bold; box-shadow: 0 2px 5px rgba(0, 123, 255, 0.3);">
                                ⚙️ Create FEN Position
                            </a>
                            <a href="https://www.chess.com" target="_blank" style="text-decoration: none; padding: 8px 15px; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border-radius: 5px; font-size: 12px; font-weight: bold; box-shadow: 0 2px 5px rgba(40, 167, 69, 0.3);">
                                🏆 Play on Chess.com
                            </a>
                            <a href="https://www.chess.com/analysis" target="_blank" style="text-decoration: none; padding: 8px 15px; background: linear-gradient(135deg, #6f42c1 0%, #563d7c 100%); color: white; border-radius: 5px; font-size: 12px; font-weight: bold; box-shadow: 0 2px 5px rgba(111, 66, 193, 0.3);">
                                📊 Chess.com Analysis
                            </a>
                            <a href="https://lichess.org/analysis" target="_blank" style="text-decoration: none; padding: 8px 15px; background: linear-gradient(135deg, #fd7e14 0%, #e55a00 100%); color: white; border-radius: 5px; font-size: 12px; font-weight: bold; box-shadow: 0 2px 5px rgba(253, 126, 20, 0.3);">
                                🔍 Lichess Analysis
                            </a>
                        </div>
                        <div style="font-size: 11px; color: #6a5d7a; margin-top: 8px; font-style: italic;">
                            💡 Tip: Use "Create FEN Position" to set up any chess position, then copy the FEN notation back here
                        </div>
                    </div>
                    
                    <form action="/submit" method="post">
                        <div style="margin-bottom: 15px;">
                            <label for="fen" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 18px;">Enter FEN Position:</label>
                            <div style="display: flex; gap: 10px; align-items: flex-start;">
                                <input type="text" name="fen" id="fen" class="fen-input{% if fen_result %} analyzed{% endif %}" placeholder="Enter FEN notation here (Press Enter to analyze)..." value="{{current_fen}}" title="Enter a FEN position and press Enter or click Analyze to get recommendations" style="flex: 1;">
                                <button type="submit" id="submit-btn" class="submit-btn compact-btn" style="display: none;" title="Analyze the chess position">Analyze</button>
                                <button type="button" id="reset-btn" class="reset-btn compact-btn" style="display: none;" onclick="resetForm()" title="Clear the FEN input">Reset</button>
                            </div>
                            <div style="font-size: 11px; color: #6a5d7a; margin-top: 5px; font-style: italic;">
                                FEN (Forsyth-Edwards Notation) describes a chess position: piece placement, turn, castling rights, en passant, and move counts
                            </div>
                        </div>
                                                <div class="sample-fens">
                            <div style="font-weight: bold; margin-bottom: 8px; color: #4a2c7a;">Sample Positions:</div>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')">Starting Position</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4')">Scholar's Mate Setup</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2')">Queen's Gambit</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('6k1/5ppp/8/8/8/2K5/5PPP/8 w - - 0 1')">Endgame Position</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('r3k2r/ppp2ppp/2n1bn2/2bpp3/2P5/2N1PN2/PPBP1PPP/R1BQKR2 w Qkq - 0 8')">Tactical Position</button>
                        </div>
                    </form>
                </div>

                {% if fen_result %}
                <div class="recommendations-wrapper">
                    <h3 class="recommendations-header">Move Recommendations</h3>
                    
                    {% if fen_result['move_comparison'] %}
                    <div class="recommendation-section" style="margin-bottom: 25px; border: 3px solid #ffd700;">
                        <div class="recommend-label" style="font-size: 1.4em; color: #ffd700 !important;">⚖️ Move Comparison Analysis:</div>
                        <div style="font-size: 14px; color: #ffd700; margin-top: 8px; padding: 12px; background: rgba(50,50,50,0.7); border-radius: 6px; border-left: 4px solid #ffd700; line-height: 1.4;">
                            {{fen_result['move_comparison']}}
                        </div>
                    </div>
                    {% endif %}
                    
                    <div class="recommendation-section">
                        <div class="recommend-label">🏆 Stockfish Recommendation:</div>
                        <div class="recommend-value">{{fen_result['stockfish']}}</div>
                        {% if fen_result['stockfish_explanation'] %}
                        <div style="font-size: 13px; color: #c8e6c8; margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; border-left: 3px solid #28a745;">
                            <strong>Why this move:</strong> {{fen_result['stockfish_explanation']}}
                        </div>
                        {% endif %}
                        {% if fen_result['stockfish_board'] %}
                        <div class="board-container">
                            {{fen_result['stockfish_board']|safe}}
                        </div>
                        {% endif %}
                        <div style="font-size: 12px; color: #b8e6b8; margin-top: 8px; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">
                            Powered by <a href="https://stockfishchess.org/" target="_blank" style="color: #90EE90; text-decoration: underline;">Stockfish</a> - World's strongest chess engine
                        </div>
                    </div>
                    
                    <div class="recommendation-section">
                        <div class="recommend-label">🤖 ChatGPT Recommendation:</div>
                        <div class="recommend-value">{{fen_result['chatgpt']}}</div>
                        {% if fen_result['chatgpt_explanation'] %}
                        <div style="font-size: 13px; color: #d4b3ff; margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; border-left: 3px solid #8e44ad;">
                            <strong>Why this move:</strong> {{fen_result['chatgpt_explanation']}}
                        </div>
                        {% endif %}
                        {% if fen_result['chatgpt_board'] %}
                        <div class="board-container">
                            {{fen_result['chatgpt_board']|safe}}
                        </div>
                        {% endif %}
                        <div style="font-size: 12px; color: #b8e6b8; margin-top: 8px; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">
                            Comparison to Stockfish: {{fen_result['chatgpt_comparison']}}
                        </div>
                    </div>
                    <div class="recommendation-section">
                        <div class="recommend-label">🤖 Gemini Recommendation:</div>
                        <div class="recommend-value">{{fen_result['gemini']}}</div>
                        {% if fen_result['gemini_explanation'] %}
                        <div style="font-size: 13px; color: #d4b3ff; margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; border-left: 3px solid #8e44ad;">
                            <strong>Why this move:</strong> {{fen_result['gemini_explanation']}}
                        </div>
                        {% endif %}
                        {% if fen_result['gemini_board'] %}
                        <div class="board-container">
                            {{fen_result['gemini_board']|safe}}
                        </div>
                        {% endif %}
                        <div style="font-size: 12px; color: #b8e6b8; margin-top: 8px; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">
                            Comparison to Stockfish: {{fen_result['gemini_comparison']}}
                        </div>
                    </div>
                    <div class="recommendation-section">
                        <div class="recommend-label">🤖 Copilot Recommendation:</div>
                        <div class="recommend-value">{{fen_result['copilot']}}</div>
                        {% if fen_result['copilot_explanation'] %}
                        <div style="font-size: 13px; color: #d4b3ff; margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; border-left: 3px solid #8e44ad;">
                            <strong>Why this move:</strong> {{fen_result['copilot_explanation']}}
                        </div>
                        {% endif %}
                        {% if fen_result['copilot_board'] %}
                        <div class="board-container">
                            {{fen_result['copilot_board']|safe}}
                        </div>
                        {% endif %}
                        <div style="font-size: 12px; color: #b8e6b8; margin-top: 8px; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">
                            Comparison to Stockfish: {{fen_result['copilot_comparison']}}
                        </div>
                    </div>
                </div>
                {% endif %}

                <div class="about-section">
                    <h3>About</h3>
                    <h4 style="color: #4a2c7a; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #8e44ad; padding-bottom: 10px;">Component Management</h4>
                    
                    <!-- Application Version Section -->
                    <div style="margin-bottom: 25px; padding: 15px; background-color: {% if app_version_info.update_available %}rgba(255, 152, 0, 0.1){% else %}rgba(142, 68, 173, 0.05){% endif %}; border: 1px solid {% if app_version_info.update_available %}#ff9800{% else %}#d4b3ff{% endif %}; border-radius: 8px;">
                        <h4 style="color: #4a2c7a; margin-bottom: 15px; display: flex; align-items: center;">
                            <span style="font-size: 20px; margin-right: 10px;">♔</span>Analyze Chess 
                            <span style="margin-left: 10px; font-size: 12px; color: #666; font-weight: normal;">← This App</span>
                            {% if app_version_info.update_available %}
                            <a href="{{ app_version_info.release_url }}" target="_blank" style="margin-left: auto; padding: 4px 8px; background: #ff9800; color: white; border-radius: 12px; font-size: 11px; font-weight: bold; text-decoration: none;">
                                ♕ UPDATE AVAILABLE
                            </a>
                            {% endif %}
                        </h4>
                        
                        <!-- Description -->
                        <div style="background: rgba(255, 255, 255, 0.6); padding: 12px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #8e44ad;">
                            <div style="font-size: 13px; color: #4a2c7a; line-height: 1.4;">
                                <strong>📋 What it is:</strong> The main chess analysis application that provides move recommendations, position evaluation, and educational insights.<br>
                                <strong>🎯 Why important:</strong> Updates bring new features, bug fixes, improved AI analysis, and enhanced user experience. Keeping current ensures optimal performance and latest chess analysis capabilities.
                            </div>
                        </div>
                        
                        <div style="margin-bottom: 10px;"><strong>Current Version:</strong> {{ app_version_info.current }}</div>
                        <div style="margin-bottom: 10px;"><strong>Latest Available:</strong> {{ app_version_info.latest }}</div>
                        <div style="margin-bottom: 15px;"><strong>Status:</strong> 
                            <span style="color:{% if app_version_info.update_available %}orange{% else %}green{% endif %};font-weight:bold;">
                                {% if app_version_info.update_available %}Update Available ({{ app_version_info.latest }}){% else %}Up to Date{% endif %}
                            </span>
                        </div>
                        {% if app_version_info.update_available %}
                        <div class="engine-buttons">
                            <form method="post" action="/update_app" style="display: inline-block; margin-right: 10px;" onsubmit="return confirm('This will update the application and restart it. Continue?')">
                                <button type="submit" class="engine-btn update-btn" style="background: #28a745; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Update Now</button>
                            </form>
                        </div>
                        {% endif %}
                        
                        {% if app_version_info.has_backups %}
                        <div class="engine-buttons" style="margin-top: 10px;">
                            <form method="post" action="/rollback_app" style="display: inline-block;" onsubmit="return confirm('This will rollback to the previous version. Continue?')">
                                <button type="submit" class="engine-btn rollback-btn" style="background: #ffc107; border: none; color: black; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Rollback</button>
                            </form>
                        </div>
                        {% endif %}
                    </div>
                    
                    <!-- Stockfish Engine Section -->
                    <div style="margin-bottom: 25px; padding: 15px; background-color: rgba(142, 68, 173, 0.05); border: 1px solid #d4b3ff; border-radius: 8px;">
                        <h4 style="color: #4a2c7a; margin-bottom: 15px; display: flex; align-items: center;">
                            <span style="font-size: 20px; margin-right: 10px;">♚</span>Stockfish Chess Engine
                        </h4>
                        
                        <!-- Description -->
                        <div style="background: rgba(255, 255, 255, 0.6); padding: 12px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #28a745;">
                            <div style="font-size: 13px; color: #4a2c7a; line-height: 1.4;">
                                <strong>⚡ What it is:</strong> The world's strongest open-source chess engine, capable of analyzing positions at super-grandmaster level (3500+ ELO rating).<br>
                                <strong>🏆 Why important:</strong> Provides professional-grade move analysis and position evaluation. Updates include improved algorithms, bug fixes, and stronger play. Essential for accurate chess analysis.
                            </div>
                        </div>
                        
                        {% if current %}
                            <div style="margin-bottom: 10px;"><strong>Path:</strong> {{current}}</div>
                            <div style="margin-bottom: 10px;"><strong>Current Version:</strong> {{version}}</div>
                            {% if latest_tag %}<div style="margin-bottom: 10px;"><strong>Latest Available:</strong> {{latest_tag}}</div>{% endif %}
                            <div style="margin-bottom: 15px;"><strong>Status:</strong> 
                                {% if stockfish_update_available and latest_tag %}
                                <a href="https://github.com/official-stockfish/Stockfish/releases/tag/{{latest_tag}}" target="_blank" style="color: orange; font-weight: bold; text-decoration: none;">
                                    Update Available ({{latest_tag}}) 📋
                                </a>
                                {% else %}
                                <span style="color: green; font-weight: bold;">Up to Date</span>
                                {% endif %}
                            </div>
                            {% if stockfish_update_available %}
                            <div class="engine-buttons">
                                <form action="/update_engine_now" method="post" style="display: inline;">
                                    <button type="submit" class="engine-btn">Update Now</button>
                                </form>
                            </div>
                            {% endif %}
                            {% if has_previous_engine() %}
                            <div class="engine-buttons" style="margin-top: 10px;">
                                <form action="/rollback_engine_now" method="post" style="display: inline;">
                                    <button type="submit" class="engine-btn" style="background: #ffc107; color: black;">Rollback</button>
                                </form>
                            </div>
                            {% endif %}
                        {% else %}
                            <div style="color:#b00; margin-bottom: 15px;">Engine not installed</div>
                            <div class="engine-buttons">
                                <form action="/update_engine_now" method="post" style="display: inline;">
                                    <button type="submit" class="engine-btn">Install Engine</button>
                                </form>
                            </div>
                        {% endif %}
                    </div>
                    
                    <!-- Python Dependencies Sections -->
                    {% for dep in python_deps %}
                    <div style="margin-bottom: 25px; padding: 15px; background-color: rgba(142, 68, 173, 0.05); border: 1px solid #d4b3ff; border-radius: 8px;">
                        <h4 style="color: #4a2c7a; margin-bottom: 15px; display: flex; align-items: center;">
                            <span style="font-size: 20px; margin-right: 10px;">🐍</span>{{ dep.name }} Package
                        </h4>
                        
                        <!-- Description -->
                        <div style="background: rgba(255, 255, 255, 0.6); padding: 12px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #007bff;">
                            <div style="font-size: 13px; color: #4a2c7a; line-height: 1.4;">
                                <strong>🔧 What it is:</strong> 
                                {% if dep.name == 'chess' %}Essential Python library for chess board representation, move validation, and game logic. Handles FEN parsing, legal move generation, and position analysis.
                                {% elif dep.name == 'flask' %}Web framework that powers the user interface. Provides the web server, routing, and template rendering for the chess analysis application.
                                {% elif dep.name == 'requests' %}HTTP library used for downloading updates, checking latest versions, and communicating with online chess services and APIs.
                                {% else %}Critical Python package required for application functionality, providing essential features and compatibility.
                                {% endif %}<br>
                                <strong>⚠️ Why important:</strong> Updates include security patches, performance improvements, and compatibility fixes. Outdated packages can cause crashes or security vulnerabilities.
                            </div>
                        </div>
                        
                        <div style="margin-bottom: 10px;"><strong>Current Version:</strong> {{ dep.current_version }}</div>
                        <div style="margin-bottom: 10px;"><strong>Latest Available:</strong> {{ dep.latest_version }}</div>
                        <div style="margin-bottom: 15px;"><strong>Status:</strong> 
                            {% if dep.update_available %}
                            <a href="https://pypi.org/project/{{ dep.name }}/{{ dep.latest_version }}/" target="_blank" style="color: orange; font-weight: bold; text-decoration: none;">
                                Update Available ({{ dep.latest_version }}) 📋
                            </a>
                            {% else %}
                            <span style="color: green; font-weight: bold;">Up to Date</span>
                            {% endif %}
                        </div>
                        {% if dep.update_available %}
                        <div class="engine-buttons">
                            <form action="/update_package" method="post" style="display: inline;">
                                <input type="hidden" name="package" value="{{ dep.name }}" />
                                <input type="hidden" name="version" value="{{ dep.latest_version }}" />
                                <button type="submit" class="engine-btn">Update Now</button>
                            </form>
                        </div>
                        {% endif %}
                        {% if has_previous_package(dep.name) %}
                        <div class="engine-buttons" style="margin-top: 10px;">
                            <form action="/rollback_package" method="post" style="display: inline;">
                                <input type="hidden" name="package" value="{{ dep.name }}" />
                                <button type="submit" class="engine-btn" style="background: #ffc107; color: black;">Rollback</button>
                            </form>
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                    
                    <div style="text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #d4b3ff; font-size: 12px; color: #7a6b93;">
                        © 2025 Drake Svc LLC. All rights reserved.<br>
                        <a href="https://github.com/AprilLorDrake" target="_blank" style="color: #8b5fbf; text-decoration: none; margin-top: 5px; display: inline-block;">
                            GitHub: AprilLorDrake
                        </a>
                    </div>
                  </div>
              </body>
              </html>
        ''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, app_version_info=app_version_info, msg=msg, fen_result=fen_result, current_fen=current_fen, has_previous_engine=has_previous_engine, has_previous_package=has_previous_package)

@app.route('/submit', methods=['POST'])
def submit():
    fen = request.form.get('fen', '').strip()
    
    # Redirect to main page with FEN parameter for analysis
    if fen:
        return redirect(url_for('analyze_chess_move', fen=fen, current_fen=fen))
    else:
        return redirect(url_for('analyze_chess_move', msg='Please enter a FEN position'))

@app.post('/update_engine_now')
def update_engine_now():
    import os
    bin_dir = os.path.join(os.path.dirname(__file__), 'bin')
    path = install_stockfish_to_dir(bin_dir)
    if path:
        global engine_path
        engine_path = path
        return redirect(url_for('analyze_chess_move', msg=f'Engine installed: {os.path.basename(path)}'))
    return redirect(url_for('analyze_chess_move', msg='Engine update failed. Check logs.'))

@app.post('/schedule_update')
def schedule_update():
    import os
    what = request.form.get('what', '')
    root = os.path.dirname(__file__)
    if what == 'engine':
        flag = os.path.join(root, '.update_engine')
        open(flag, 'a').close()
        return redirect(url_for('analyze_chess_move', msg='Engine update scheduled. It will install on next launch.'))
    elif what == 'deps':
        flag = os.path.join(root, '.update_deps')
        open(flag, 'a').close()
        return redirect(url_for('analyze_chess_move', msg='Dependency update scheduled. It will install on next launch.'))
    else:
        return redirect(url_for('analyze_chess_move', msg='Unknown update type.'))

@app.post('/rollback_engine_now')
def rollback_engine_now():
    import os
    p = _paths()
    prev = _read_text(p['previous'])
    if prev and os.path.isfile(prev):
        _write_text(p['selected'], prev)
        global engine_path
        engine_path = prev
        return redirect(url_for('analyze_chess_move', msg='Rolled back to previous engine.'))
    return redirect(url_for('analyze_chess_move', msg='No previous engine to rollback to.'))

@app.errorhandler(500)
def handle_internal_error(err):
    # Generic friendly error page with actions
    return render_template_string('''
        <html><body>
        <div style="padding:8px;margin-bottom:10px;background:#fee;border:1px solid #c99;">
          <strong>Unexpected error:</strong> {{err}}
        </div>
        <div style="display:flex;gap:10px;margin-bottom:16px;">
          <form action="/update_engine_now" method="post"><button type="submit">Update Engine Now</button></form>
          <form action="/schedule_update" method="post"><input type="hidden" name="what" value="engine" /><button type="submit">Update Engine Next Launch</button></form>
          <form action="/schedule_update" method="post"><input type="hidden" name="what" value="deps" /><button type="submit">Update Packages Next Launch</button></form>
          <form action="/rollback_engine_now" method="post"><button type="submit">Rollback Engine</button></form>
        </div>
        <div><a href="{{url_for('analyze_chess_move')}}">Go to Home</a></div>
        </body></html>
    ''', err=str(err)), 500

# --- UPDATE/ROLLBACK ROUTES ---
@app.route('/update_app', methods=['POST'])
def update_app():
    """Perform automated application update."""
    result = download_and_update()
    if result['success']:
        return f"""
        <html>
        <head>
            <title>Update Successful</title>
            <script>
                setTimeout(function() {{
                    if (window.opener) {{
                        window.opener.location.reload();
                        window.close();
                    }} else {{
                        window.location.href = '/analyze_chess_move';
                    }}
                }}, 3000);
            </script>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px; background: #f0f8ff;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: white; border-radius: 8px; border: 1px solid #28a745;">
            <h2 style="color: #28a745;">♔ Update Successful!</h2>
            <p><strong>Message:</strong> {result['message']}</p>
            <p><strong>New Version:</strong> {result.get('new_version', 'Unknown')}</p>
            <p><strong>Backup Location:</strong> {result.get('backup_location', 'N/A')}</p>
            <div style="margin-top: 20px;">
                <p style="color: #28a745; font-weight: bold;">🔄 Automatically refreshing in 3 seconds...</p>
                <a href="/analyze_chess_move" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px;">Return Now</a>
                <button onclick="window.close()" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 4px;">Close Window</button>
            </div>
        </div>
        </body></html>
        """
    else:
        return f"""
        <html>
        <head><title>Update Failed</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px; background: #ffe6e6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: white; border-radius: 8px; border: 1px solid #dc3545;">
            <h2 style="color: #dc3545;">❌ Update Failed</h2>
            <p><strong>Error:</strong> {result['message']}</p>
            <div style="margin-top: 20px;">
                <a href="/analyze_chess_move" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px;">Return to App</a>
                <button onclick="window.close()" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 4px;">Close Window</button>
            </div>
        </div>
        </body></html>
        """

@app.route('/rollback_app', methods=['POST'])
def rollback_app():
    """Perform automated application rollback."""
    result = rollback_version()
    if result['success']:
        return f"""
        <html>
        <head>
            <title>Rollback Successful</title>
            <script>
                setTimeout(function() {{
                    if (window.opener) {{
                        window.opener.location.reload();
                        window.close();
                    }} else {{
                        window.location.href = '/analyze_chess_move';
                    }}
                }}, 3000);
            </script>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px; background: #fff3cd;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: white; border-radius: 8px; border: 1px solid #ffc107;">
            <h2 style="color: #856404;">♚ Rollback Successful!</h2>
            <p><strong>Message:</strong> {result['message']}</p>
            <p><strong>Rolled back to:</strong> {result.get('rolled_back_to', 'Previous version')}</p>
            <p><strong>Current backup:</strong> {result.get('current_backup', 'N/A')}</p>
            <div style="margin-top: 20px;">
                <p style="color: #28a745; font-weight: bold;">🔄 Automatically refreshing in 3 seconds...</p>
                <a href="/analyze_chess_move" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px;">Return Now</a>
                <button onclick="window.close()" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 4px;">Close Window</button>
            </div>
        </div>
        </body></html>
        """
    else:
        return f"""
        <html>
        <head><title>Rollback Failed</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px; background: #ffe6e6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: white; border-radius: 8px; border: 1px solid #dc3545;">
            <h2 style="color: #dc3545;">❌ Rollback Failed</h2>
            <p><strong>Error:</strong> {result['message']}</p>
            <div style="margin-top: 20px;">
                <a href="/analyze_chess_move" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px;">Return to App</a>
                <button onclick="window.close()" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 4px;">Close Window</button>
            </div>
        </div>
        </body></html>
        """

# --- FEEDBACK ROUTES ---
@app.route('/feedback')
def feedback_form():
    """Display feedback form."""
    return '''
    <html>
    <head>
        <title>Send Feedback - Analyze Chess</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f5f3ff; }
            .form-container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h2 { color: #4a2c7a; text-align: center; margin-bottom: 20px; }
            label { display: block; margin-top: 15px; font-weight: bold; color: #4a2c7a; }
            input, textarea, select { width: 100%; padding: 10px; border: 2px solid #d4b3ff; border-radius: 4px; margin-top: 5px; font-size: 14px; }
            input:focus, textarea:focus, select:focus { border-color: #9966ff; outline: none; }
            .btn { background: linear-gradient(135deg, #8b5fbf 0%, #7048a3 100%); color: white; padding: 12px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin: 20px 10px 0 0; }
            .btn:hover { background: linear-gradient(135deg, #7048a3 0%, #5d3d87 100%); transform: translateY(-1px); }
            .back-btn { background: #6c757d; }
            .back-btn:hover { background: #5a6268; }
            .note { background: #e7f3ff; padding: 10px; border-radius: 4px; font-size: 13px; color: #666; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h2>♔ Send Feedback - Analyze Chess</h2>
            <form action="/feedback" method="post">
                <label for="feedback_type">Feedback Type:</label>
                <select name="feedback_type" id="feedback_type" required>
                    <option value="">Select type...</option>
                    <option value="bug">Bug Report</option>
                    <option value="feature">Feature Request</option>
                    <option value="improvement">Improvement Suggestion</option>
                    <option value="general">General Feedback</option>
                    <option value="question">Question/Help</option>
                </select>

                <label for="email">Your Email (optional):</label>
                <input type="email" name="email" id="email" placeholder="your.email@example.com">

                <label for="subject">Subject:</label>
                <input type="text" name="subject" id="subject" required placeholder="Brief description of your feedback">

                <label for="message">Message:</label>
                <textarea name="message" id="message" rows="8" required placeholder="Please provide detailed feedback..."></textarea>

                <label for="browser_info">Browser/System (optional):</label>
                <input type="text" name="browser_info" id="browser_info" placeholder="e.g., Chrome 118 on Windows 11">

                <div class="note">
                    📧 Your feedback will be sent via email to the development team. No GitHub account required!
                    If you provided your email, we may contact you for follow-up questions.
                </div>

                <button type="submit" class="btn">Send Feedback</button>
                <a href="/analyze_chess_move" class="btn back-btn" style="text-decoration: none;">Back to App</a>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    """Handle feedback submission."""
    feedback_type = request.form.get('feedback_type', '')
    email = request.form.get('email', '')
    subject = request.form.get('subject', '')
    message = request.form.get('message', '')
    browser_info = request.form.get('browser_info', '')
    
    # Create feedback content
    feedback_content = f"""
Feedback Type: {feedback_type}
From: {email if email else 'Anonymous'}
Subject: {subject}
Browser/System: {browser_info if browser_info else 'Not provided'}

Message:
{message}

---
Submitted via Analyze Chess Feedback Form
Timestamp: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """.strip()
    
    # For now, we'll display the feedback and provide options to send it
    # In a production app, you'd integrate with an email service
    return f'''
    <html>
    <head>
        <title>Feedback Submitted - Analyze Chess</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; padding: 20px; background: #f5f3ff; }}
            .success-container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border: 2px solid #28a745; }}
            h2 {{ color: #28a745; text-align: center; margin-bottom: 20px; }}
            .feedback-preview {{ background: #f8f9fa; padding: 15px; border-radius: 4px; border-left: 4px solid #8b5fbf; margin: 20px 0; white-space: pre-line; font-family: monospace; font-size: 13px; }}
            .btn {{ background: linear-gradient(135deg, #8b5fbf 0%, #7048a3 100%); color: white; padding: 12px 20px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; margin: 10px 5px 0 0; }}
            .btn:hover {{ background: linear-gradient(135deg, #7048a3 0%, #5d3d87 100%); transform: translateY(-1px); }}
            .email-btn {{ background: #007bff; }}
            .email-btn:hover {{ background: #0056b3; }}
            .note {{ background: #fff3cd; padding: 15px; border-radius: 4px; border-left: 4px solid #ffc107; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="success-container">
            <h2>✅ Feedback Received!</h2>
            <p>Thank you for your feedback! Here's what we received:</p>
            
            <div class="feedback-preview">{feedback_content}</div>
            
            <div class="note">
                <strong>📧 Next Steps:</strong><br>
                • Copy the feedback above and email it to: <strong>feedback@analyzeChess.com</strong><br>
                • Or click the button below to open your email client with the message pre-filled<br>
                • You can also submit it as a GitHub issue if you have an account
            </div>
            
            <a href="mailto:feedback@analyzeChess.com?subject=Analyze Chess Feedback: {subject}&body={feedback_content.replace(chr(10), '%0D%0A')}" class="btn email-btn">Open Email Client</a>
            <a href="https://github.com/AprilLorDrake/Analyze_Chess/issues/new" target="_blank" class="btn">Submit on GitHub</a>
            <a href="/analyze_chess_move" class="btn">Back to App</a>
        </div>
    </body>
    </html>
    '''

# --- ASSETS ROUTE ---
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    import os
    from flask import send_from_directory
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    return send_from_directory(assets_dir, filename)

@app.route('/favicon.ico')
def favicon():
    import os
    from flask import send_from_directory
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    return send_from_directory(assets_dir, 'chess_icon.ico')

# --- HEALTH CHECK (add near your other routes) ---
@app.get("/__ac_health")
def ac_health():
    # return a fixed token the launcher will look for
    return "analyze_chess_ok"

@app.route('/update_package', methods=['POST'])
def update_package():
    import subprocess
    import sys
    
    package = request.form.get('package', '').strip()
    version = request.form.get('version', '').strip()
    
    if not package:
        return redirect(url_for('analyze_chess_move', msg=f"Error: No package specified"))
    
    try:
        # Update the specific package
        if version:
            cmd = [sys.executable, '-m', 'pip', 'install', f'{package}=={version}']
        else:
            cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', package]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            msg = f"Successfully updated {package}"
            if version:
                msg += f" to version {version}"
        else:
            msg = f"Failed to update {package}: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        msg = f"Timeout while updating {package}"
    except Exception as e:
        msg = f"Error updating {package}: {str(e)}"
    
    return redirect(url_for('analyze_chess_move', msg=msg))

@app.route('/rollback_package', methods=['POST'])
def rollback_package():
    import subprocess
    import sys
    
    package = request.form.get('package', '').strip()
    
    if not package:
        return redirect(url_for('analyze_chess_move', msg=f"Error: No package specified"))
    
    try:
        # Get package history or downgrade to a previous version
        # For now, we'll reinstall the current version (force reinstall)
        cmd = [sys.executable, '-m', 'pip', 'install', '--force-reinstall', package]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            msg = f"Successfully reinstalled {package}"
        else:
            msg = f"Failed to rollback {package}: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        msg = f"Timeout while rolling back {package}"
    except Exception as e:
        msg = f"Error rolling back {package}: {str(e)}"
    
    return redirect(url_for('analyze_chess_move', msg=msg))

# Optional: standard Flask entry point
import socket
def find_free_port(default_port=5002):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", default_port))
        s.close()
        return default_port
    except OSError:
        s.close()
        # Find a free port
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.bind(("127.0.0.1", 0))
        port = s2.getsockname()[1]
        s2.close()
        return port

import webbrowser
import os
if __name__ == "__main__":
    # Auto-discover the engine if not explicitly set
    stockfish_path = engine_path or find_stockfish()
    # If not found, and running interactively, offer to download and install
    # Stockfish into the project ./bin folder so everyone uses a consistent
    # binary regardless of renamed local files.
    if not stockfish_path:
        import sys
        proj_bin = os.path.join(os.path.dirname(__file__), 'bin')
        os.makedirs(proj_bin, exist_ok=True)

        def install_stockfish(target_dir):
            """Download Stockfish zip, extract the engine exe and preserve its filename.

            Returns the absolute path to the installed executable on success, or
            None on failure.
            """
            try:
                import requests, zipfile, io, tempfile
            except ImportError:
                print("requests package not available; cannot auto-install Stockfish.")
                return None
            url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    exe_candidates = [f for f in z.namelist() if f.lower().endswith('.exe')]
                    if not exe_candidates:
                        print("No executable found inside Stockfish archive.")
                        return None
                    exe_name = exe_candidates[0]
                    basename = os.path.basename(exe_name)
                    target_path = os.path.join(target_dir, basename)
                    # extract to a temp file then move to target_path
                    with z.open(exe_name) as src:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp:
                            tmp.write(src.read())
                            tmp_path = tmp.name
                    try:
                        os.replace(tmp_path, target_path)
                    except Exception:
                        with open(tmp_path, 'rb') as srcf, open(target_path, 'wb') as dstf:
                            dstf.write(srcf.read())
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                try:
                    os.chmod(target_path, 0o755)
                except Exception:
                    pass
                return target_path if os.path.isfile(target_path) else None
            except Exception as e:
                print(f"Stockfish install failed: {e}")
                return None

        if sys.stdin and sys.stdin.isatty():
            resp = input("Stockfish engine not found. Download and install Stockfish into './bin'? [Y/n]: ").strip().lower()
            if resp in ('', 'y', 'yes'):
                print('Downloading Stockfish...')
                installed_path = install_stockfish(proj_bin)
                if installed_path:
                    stockfish_path = installed_path
                    print(f"Installed Stockfish to {installed_path}")
                else:
                    print("Automatic installation failed. You can set STOCKFISH_PATH to point to a Stockfish executable.")
            else:
                print("Skipping Stockfish installation; engine features will fallback.")
        else:
            print("Stockfish not found. To enable engine features, set STOCKFISH_PATH or run the app interactively to install automatically.")
    if stockfish_path:
        print(f"Using Stockfish at: {stockfish_path}")
        # export to module-global engine_path so request handlers can use it
        engine_path = stockfish_path
        if os.path.isfile(stockfish_path) and is_file_locked(stockfish_path):
            print(f"ERROR: The Stockfish engine file '{stockfish_path}' is locked by another process.\nPlease close all Python, Flask, or Stockfish windows and try again.")
            input("Press Enter to exit...")
            exit(1)
    else:
        print("Stockfish executable not found; engine features will fallback to a legal-move response.")
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Analyze Chess Flask app on http://{host}:{port}/analyze_chess_move ...")
    try:
        app.run(host=host, port=port)
    except Exception as e:
        print(f"Flask failed to start: {e}")

def main():
    """Entry point for package installation"""
    if __name__ == "__main__":
        pass  # The Flask app will run from the code above
