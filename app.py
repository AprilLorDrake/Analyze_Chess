import ctypes
import os
import sys

def is_file_locked(filepath):
    try:
        fh = open(filepath, 'a')
        fh.close()
        return False
    except Exception:
        return True

from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import io
from PIL import Image
import chess
import chess.engine

# Add python-chess-vision to path
_base_dir = os.path.dirname(os.path.abspath(__file__))
_pcv_path = os.path.join(_base_dir, 'python-chess-vision')
if os.path.exists(_pcv_path) and _pcv_path not in sys.path:
    sys.path.insert(0, _pcv_path)

try:
    from python_chess_vision import fen_from_image
except ImportError:
    fen_from_image = None

app = Flask(__name__)

@app.route('/upload_board_image', methods=['POST'])
def upload_board_image():
    """Accepts a PNG chessboard image, returns FEN string."""
    if not fen_from_image:
        return jsonify({'error': 'python-chess-vision not installed'}), 500
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    try:
        img = Image.open(file.stream)
        fen = fen_from_image(img)
        
        # Validate if the FEN looks reasonable (not all empty or all same piece)
        # This is a heuristic to detect if piece recognition failed
        piece_chars = [c for c in fen.split(' ')[0] if c.isalpha()]
        if len(piece_chars) < 2:  # Only 1 or 0 pieces detected
            return jsonify({
                'warning': 'Could not accurately detect pieces in the image. Piece recognition works best with clear, standard chess board images with good contrast.',
                'fen': fen,
                'suggestion': 'For better accuracy, try: (1) Better lighting, (2) Clearer board image, (3) Or enter FEN notation directly above'
            }), 200
        
        return jsonify({'fen': fen})
    except Exception as e:
        return jsonify({'error': f'Image processing error: {str(e)}'}), 500

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

def board_to_html(board, highlight_move=None, flip_board=False):
    """Convert chess board to beautiful HTML/CSS representation."""
    piece_unicode = {
        'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
        'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙'
    }
    
    html = ['<div class="chess-board">']
    
    # Add rank labels on the side
    # If flip_board is True (Black's turn), show 1-8 from top to bottom
    # If flip_board is False (White's turn), show 8-1 from top to bottom
    rank_range = range(8) if flip_board else range(7, -1, -1)
    for rank in rank_range:
        html.append('<div class="board-row">')
        html.append(f'<div class="rank-label">{rank + 1}</div>')
        
        # If flip_board is True, reverse the file order (h-a instead of a-h)
        file_range = range(7, -1, -1) if flip_board else range(8)
        for file in file_range:
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            
            # Determine square color
            square_color = 'light' if (file + rank) % 2 == 0 else 'dark'
            
            # Check if this square should be highlighted
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
    file_labels = 'hgfedcba' if flip_board else 'abcdefgh'
    for file_char in file_labels:
        html.append(f'<div class="file-label">{file_char}</div>')
    html.append('</div>')
    
    html.append('</div>')
    return ''.join(html)

def generate_fallback_recommendation(board, flip_board=False):
    """Generate a simple AI recommendation based on chess principles."""
    try:
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return "No legal moves available", ""
        
        # Simple scoring system for moves
        scored_moves = []
        
        for move in legal_moves:
            score = 0
            
            # Make the move temporarily to evaluate
            board.push(move)
            
            # Basic evaluation criteria:
            # 1. Captures are good
            captured_piece = board.piece_at(move.to_square)
            if captured_piece:
                piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0}
                score += piece_values.get(captured_piece.symbol().lower(), 0) * 10
            
            # 2. Check is good
            if board.is_check():
                score += 5
            
            # 3. Checkmate is best
            if board.is_checkmate():
                score += 1000
                
            # 4. Center control (e4, e5, d4, d5)
            center_squares = [chess.E4, chess.E5, chess.D4, chess.D5]
            if move.to_square in center_squares:
                score += 2
                
            # 5. Avoid putting pieces in danger (simple check)
            if board.is_attacked_by(not board.turn, move.to_square):
                score -= 3
            
            board.pop()  # Undo the move
            scored_moves.append((move, score))
        
        # Sort by score and pick the best
        scored_moves.sort(key=lambda x: x[1], reverse=True)
        best_move = scored_moves[0][0]
        
        # Convert to SAN format (Lichess style)
        return board.san(best_move), board_to_html(board, best_move, flip_board=flip_board)
        
    except Exception as e:
        return f"Analysis failed: {e}", ""

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

def version_greater(v1, v2):
    """Compare two version strings, return True if v1 > v2."""
    def parse_version(v):
        v = v.lstrip('v').split('.')
        return tuple(int(x) for x in v)
    try:
        return parse_version(v1) > parse_version(v2)
    except:
        return False

def get_application_version_info():
    """Get current application version and check for updates from GitHub releases."""
    try:
        import requests
        requests_available = True
    except ImportError:
        requests_available = False
    
    # Current version - read from version.py
    try:
        from version import __version__
        current_version = __version__
    except ImportError:
        current_version = "Unknown"
    
    # Try to get current version from git tag if possible
    try:
        import subprocess
        result = subprocess.run(['git', 'describe', '--tags', '--exact-match'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            current_version = result.stdout.strip()
    except:
        pass  # Fall back to version.py or Unknown
    
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
                # Compare versions: only update if latest > current
                update_available = version_greater(latest_version, current_version)
            else:
                latest_version = "Check failed"
        except Exception:
            latest_version = "Check failed"
    else:
        latest_version = "requests not available"
    
    return {
        'current': current_version,
        'latest': latest_version,
        'update_available': update_available,
        'release_url': f"https://github.com/AprilLorDrake/Analyze_Chess/releases/tag/{latest_version}" if latest_version not in ["Unknown", "Check failed", "requests not available"] else None
    }

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

    # 4) common install locations (32/64-bit Program Files, user directories)
    common = [
        r"C:\Program Files\Stockfish\stockfish.exe",
        r"C:\Program Files (x86)\Stockfish\stockfish.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Stockfish\stockfish.exe"),
        os.path.expanduser(r"~\stockfish\stockfish.exe"),
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
                if entry.lower().endswith('.exe') and 'stockfish' in entry.lower():
                    candidate = os.path.join(proj_bin, entry)
                    if os.path.isfile(candidate):
                        return candidate
    except Exception:
        # ignore permission/listing errors and continue
        pass

    return None

def install_stockfish_to_dir(target_dir: str):
    """Download latest Stockfish zip and extract the engine exe into target_dir.

    Preserves the original filename from the archive. Returns absolute path to
    the installed executable on success, else None.
    """
    import os
    try:
        import requests, zipfile, io, tempfile
    except ImportError:
        print("requests package not available; cannot auto-install Stockfish.")
        return None
    os.makedirs(target_dir, exist_ok=True)
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
            # backup any current engine in bin
            paths = _paths()
            current = find_stockfish()
            if current and os.path.commonpath([os.path.dirname(current), target_dir]) == target_dir:
                # only back up if current is inside target_dir (our managed bin)
                import time, shutil as _sh
                bdir = os.path.join(target_dir, 'backup')
                os.makedirs(bdir, exist_ok=True)
                stamp = time.strftime('%Y%m%d-%H%M%S')
                bname = os.path.basename(current)
                backup_path = os.path.join(bdir, f"{bname}.{stamp}.bak")
                try:
                    _sh.copy2(current, backup_path)
                    _write_text(paths['previous'], backup_path)
                except Exception:
                    pass
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
        # persist selection
        _write_text(paths['selected'], target_path)
        return target_path if os.path.isfile(target_path) else None
    except Exception as e:
        print(f"Stockfish install failed: {e}")
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
    if not engine_path:
        engine_path = find_stockfish()
    current = engine_path
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
            stockfish_score = "N/A"  # Initialize default value
            print(f"DEBUG: engine_path = {engine_path}")
            print(f"DEBUG: engine_path exists = {os.path.isfile(engine_path) if engine_path else False}")
            if not engine_path or not os.path.isfile(engine_path):
                print("DEBUG: Using fallback (no engine)")
                first_move = next(iter(board.legal_moves)) if board.legal_moves else None
                stockfish_move = str(first_move) if first_move else "No legal moves available"
                stockfish_board = board_to_html(board, first_move) if first_move else board_to_html(board)
            else:
                print("DEBUG: Using Stockfish engine")
                try:
                    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
                    # Get best move
                    result = engine.play(board, chess.engine.Limit(time=2.0))
                    
                    # Get evaluation score AFTER getting the move
                    try:
                        info = engine.analyse(board, chess.engine.Limit(time=0.5))
                        print(f"DEBUG: Info keys: {list(info.keys())}")
                        print(f"DEBUG: Has score: {'score' in info}")
                        if 'score' in info:
                            score = info['score']
                            print(f"DEBUG: Score object: {score}")
                            # Use white() to always get score from white's perspective
                            score_val = score.white().score(mate_score=10000)
                            print(f"DEBUG: Score value: {score_val}")
                            if score_val is not None:
                                stockfish_score = f"{score_val / 100:+.2f}"
                                print(f"DEBUG: Formatted score: {stockfish_score}")
                            else:
                                stockfish_score = "Mate"
                        else:
                            print("DEBUG: Score not in info!")
                            stockfish_score = "N/A"
                    except Exception as score_error:
                        print(f"Score error: {score_error}")
                        import traceback
                        traceback.print_exc()
                        stockfish_score = "N/A"
                    
                    try:
                        engine.quit()
                    except Exception:
                        pass
                    
                    # Convert UCI to SAN (Standard Algebraic Notation like Lichess)
                    stockfish_move = board.san(result.move)
                    # Flip board if black to move
                    flip = not board.turn  # board.turn is True for white, False for black
                    stockfish_board = board_to_html(board, result.move, flip_board=flip)
                except Exception as e:
                    print(f"Engine error: {e}")
                    stockfish_move = f"Engine error: {e}"
                    stockfish_board = board_to_html(board)
            # Fallback AI recommendation - simple chess logic
            flip = not board.turn  # Flip if black to move
            fallback_ai, ai_board = generate_fallback_recommendation(board, flip_board=flip)
            
            # Get Stockfish evaluation of AI move if engine available
            ai_score = "N/A"
            if fallback_ai and fallback_ai not in ["No legal moves available", "Analysis failed"] and engine_path and os.path.isfile(engine_path):
                try:
                    # Parse AI move and make it on a copy of the board
                    test_board = board.copy()
                    ai_move = test_board.parse_san(fallback_ai)
                    test_board.push(ai_move)
                    
                    # Evaluate position after AI move
                    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
                    info = engine.analyse(test_board, chess.engine.Limit(time=0.5))
                    if 'score' in info:
                        score = info['score']
                        # Get score from perspective of side that just moved
                        score_val = score.white().score(mate_score=10000)
                        if score_val is not None:
                            ai_score = f"{score_val / 100:+.2f}"
                        else:
                            ai_score = "Mate"
                    engine.quit()
                except Exception as e:
                    print(f"AI score error: {e}")
                    ai_score = "N/A"
            
            fen_result = {
                'stockfish': stockfish_move, 
                'stockfish_board': stockfish_board,
                'stockfish_score': stockfish_score,
                'ai': fallback_ai,
                'ai_board': ai_board,
                'ai_score': ai_score
            }
        except Exception as e:
            fen_result = {
                'stockfish': f"Invalid FEN: {e}", 
                'stockfish_board': "",
                'ai': "-",
                'ai_board': ""
            }
    
    return render_template_string('''
            <html>
            <head>
                <title>Analyze Next Best Chess Move!</title>
                <link rel="icon" type="image/x-icon" href="/favicon.ico">
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
                        padding: 10px; 
                        font-size: 16px; 
                        width: 400px; 
                        border: 2px solid #c299ff; 
                        border-radius: 6px; 
                        background: rgba(255, 255, 255, 0.9);
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
                    .copy-board-btn {
                        background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-size: 0.95em;
                        font-weight: 600;
                        cursor: pointer;
                        margin-top: 12px;
                        transition: all 0.3s ease;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
                        display: block;
                        margin-left: auto;
                        margin-right: auto;
                    }
                    .copy-board-btn:hover {
                        background: linear-gradient(135deg, #5aa3f0 0%, #4a90e2 100%);
                        transform: translateY(-2px);
                        box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4);
                    }
                    .copy-board-btn:active {
                        transform: translateY(0);
                        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
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
                 
                 /* Modal styles for expanded board view */
                 .board-modal {
                     display: none;
                     position: fixed;
                     z-index: 10000;
                     left: 0;
                     top: 0;
                     width: 100%;
                     height: 100%;
                     background-color: rgba(0, 0, 0, 0.85);
                     animation: fadeIn 0.3s;
                 }
                 @keyframes fadeIn {
                     from { opacity: 0; }
                     to { opacity: 1; }
                 }
                 .board-modal-content {
                     position: relative;
                     margin: 3% auto;
                     padding: 30px;
                     width: 90%;
                     max-width: 600px;
                     background: linear-gradient(135deg, #2c3e50 0%, #1a252f 100%);
                     border-radius: 15px;
                     box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
                     animation: slideDown 0.3s;
                 }
                 @keyframes slideDown {
                     from { transform: translateY(-50px); opacity: 0; }
                     to { transform: translateY(0); opacity: 1; }
                 }
                 .board-modal-close {
                     position: absolute;
                     right: 20px;
                     top: 15px;
                     font-size: 32px;
                     font-weight: bold;
                     color: #aaa;
                     cursor: pointer;
                     transition: all 0.2s;
                     line-height: 1;
                 }
                 .board-modal-close:hover {
                     color: #fff;
                     transform: scale(1.2);
                 }
                 .board-modal-title {
                     color: #87ceeb;
                     font-size: 24px;
                     font-weight: bold;
                     margin-bottom: 20px;
                     text-align: center;
                     text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                 }
                 #modalBoardContainer {
                     display: flex;
                     justify-content: center;
                     align-items: center;
                     min-height: 400px;
                     padding: 20px 0;
                 }
                 #modalBoardContainer .chess-board {
                     margin: 0 auto;
                 }
                 .board-modal-buttons {
                     display: flex;
                     justify-content: center;
                     gap: 15px;
                     margin-top: 30px;
                 }
                 .board-modal-btn {
                     padding: 12px 30px;
                     font-size: 16px;
                     font-weight: bold;
                     border: none;
                     border-radius: 8px;
                     cursor: pointer;
                     transition: all 0.3s;
                     box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                 }
                 .board-modal-btn.analyze {
                     background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                     color: white;
                 }
                 .board-modal-btn.analyze:hover {
                     background: linear-gradient(135deg, #218838 0%, #1ea085 100%);
                     transform: translateY(-2px);
                     box-shadow: 0 6px 16px rgba(40, 167, 69, 0.4);
                 }
                 .board-modal-btn.close {
                     background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
                     color: white;
                 }
                 .board-modal-btn.close:hover {
                     background: linear-gradient(135deg, #5a6268 0%, #4e555b 100%);
                     transform: translateY(-2px);
                 }
                </style>
                <script>
                    function loadSampleFEN(fen) {
                        const fenInput = document.getElementById('fen');
                        const submitBtn = document.getElementById('submit-btn');
                        const resetBtn = document.querySelector('.reset-btn');
                        
                        // Set the FEN value
                        fenInput.value = fen;
                        
                        // Reset button states - remove analyzed state
                        fenInput.classList.remove('analyzed');
                        submitBtn.classList.remove('analyzed');
                        submitBtn.disabled = false;
                        submitBtn.title = 'Click to analyze the chess position';
                        resetBtn.classList.remove('active');
                        
                        // Validate to ensure button is enabled
                        validateFENInput();
                    }
                    
                    function showBoardModal(fen, name) {
                        const modal = document.getElementById('boardModal');
                        const title = document.getElementById('modalTitle');
                        const boardContainer = document.getElementById('modalBoardContainer');
                        const analyzeBtn = document.getElementById('modalAnalyzeBtn');
                        
                        title.textContent = name;
                        
                        // Render full-size board
                        boardContainer.innerHTML = renderFullBoard(fen);
                        
                        // Set up analyze button to auto-submit
                        analyzeBtn.onclick = function() {
                            loadSampleFEN(fen);
                            modal.style.display = 'none';
                            // Auto-submit the form
                            document.querySelector('form[action="/submit"]').submit();
                        };
                        
                        modal.style.display = 'block';
                    }
                    
                    function renderFullBoard(fen) {
                        const pieces = {
                            'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
                            'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
                        };
                        
                        const fenParts = fen.split(' ');
                        const position = fenParts[0];
                        const ranks = position.split('/');
                        
                        let html = '<div class="chess-board" style="transform: scale(1.3); margin: 30px auto;">';
                        
                        // Add rank labels and squares
                        ranks.forEach((rank, rankIdx) => {
                            html += '<div class="board-row">';
                            html += `<div class="rank-label">${8 - rankIdx}</div>`;
                            
                            let fileIdx = 0;
                            for (let char of rank) {
                                if (/\d/.test(char)) {
                                    // Empty squares
                                    for (let i = 0; i < parseInt(char); i++) {
                                        const isLight = (rankIdx + fileIdx) % 2 === 0;
                                        const squareClass = isLight ? 'light' : 'dark';
                                        html += `<div class="chess-square ${squareClass}"></div>`;
                                        fileIdx++;
                                    }
                                } else {
                                    // Piece square
                                    const isLight = (rankIdx + fileIdx) % 2 === 0;
                                    const squareClass = isLight ? 'light' : 'dark';
                                    const piece = pieces[char] || '';
                                    const isWhite = char === char.toUpperCase();
                                    const pieceColor = isWhite ? 'white' : 'black';
                                    html += `<div class="chess-square ${squareClass}">`;
                                    html += `<span class="chess-piece ${pieceColor}">${piece}</span>`;
                                    html += `</div>`;
                                    fileIdx++;
                                }
                            }
                            html += '</div>';
                        });
                        
                        // Add file labels
                        html += '<div class="board-row file-labels">';
                        html += '<div class="rank-label"></div>';
                        for (let file of 'abcdefgh') {
                            html += `<div class="file-label">${file}</div>`;
                        }
                        html += '</div>';
                        html += '</div>';
                        
                        return html;
                    }
                    
                    function closeBoardModal() {
                        document.getElementById('boardModal').style.display = 'none';
                    }
                    
                    // Close modal when clicking outside
                    window.onclick = function(event) {
                        const modal = document.getElementById('boardModal');
                        if (event.target === modal) {
                            modal.style.display = 'none';
                        }
                    }
                    
                    // Close modal with Escape key
                    document.addEventListener('keydown', function(event) {
                        if (event.key === 'Escape') {
                            closeBoardModal();
                        }
                    });
                    
                    function toggleOpenings() {
                        const grid = document.getElementById('openings-grid');
                        const toggle = document.getElementById('openings-toggle');
                        
                        if (grid.style.display === 'none') {
                            grid.style.display = 'block';
                            toggle.style.transform = 'rotate(90deg)';
                            // Render all mini boards when expanded
                            document.querySelectorAll('[data-fen]').forEach(el => {
                                renderMiniBoard(el);
                            });
                        } else {
                            grid.style.display = 'none';
                            toggle.style.transform = 'rotate(0deg)';
                        }
                    }
                    
                    function renderMiniBoard(element) {
                        const fen = element.getAttribute('data-fen');
                        if (!fen || element.innerHTML.trim()) return; // Already rendered
                        
                        const pieces = {
                            'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
                            'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
                        };
                        
                        const fenParts = fen.split(' ');
                        const position = fenParts[0];
                        const ranks = position.split('/');
                        
                        let html = '<div style="display: grid; grid-template-columns: repeat(8, 1fr); gap: 1px; background: #999; padding: 2px; border-radius: 4px; width: 120px; height: 120px;">';
                        
                        ranks.forEach((rank, rankIdx) => {
                            let fileIdx = 0;
                            for (let char of rank) {
                                if (/\d/.test(char)) {
                                    // Empty squares
                                    for (let i = 0; i < parseInt(char); i++) {
                                        const bgColor = (rankIdx + fileIdx) % 2 === 0 ? '#f0e6d2' : '#b58863';
                                        html += `<div style="background: ${bgColor}; font-size: 10px; display: flex; align-items: center; justify-content: center; aspect-ratio: 1;"></div>`;
                                        fileIdx++;
                                    }
                                } else {
                                    // Piece
                                    const bgColor = (rankIdx + fileIdx) % 2 === 0 ? '#f0e6d2' : '#b58863';
                                    const piece = pieces[char] || '?';
                                    html += `<div style="background: ${bgColor}; font-size: 10px; display: flex; align-items: center; justify-content: center; aspect-ratio: 1; color: ${char === char.toUpperCase() ? '#fff' : '#000'}; text-shadow: 1px 1px 1px rgba(0,0,0,0.3);">${piece}</div>`;
                                    fileIdx++;
                                }
                            }
                        });
                        
                        html += '</div>';
                        element.innerHTML = html;
                    }
                    
                    function resetForm() {
                        window.location.href = '/';
                    }
                    
                    function validateFENInput() {
                        const fenInput = document.getElementById('fen');
                        const submitBtn = document.getElementById('submit-btn');
                        
                        if (fenInput.value.trim() === '') {
                            submitBtn.disabled = true;
                            submitBtn.title = 'Please enter a FEN position to analyze';
                        } else {
                            submitBtn.disabled = false;
                            submitBtn.title = 'Click to analyze the chess position';
                        }
                    }
                    
                    function setAnalyzedState() {
                        const submitBtn = document.getElementById('submit-btn');
                        const resetBtn = document.querySelector('.reset-btn');
                        
                        // Make analyze button grey and disabled
                        submitBtn.classList.add('analyzed');
                        submitBtn.disabled = true;
                        submitBtn.title = 'Analysis completed';
                        
                        // Make reset button green and active
                        resetBtn.classList.add('active');
                    }
                    
                    function uploadBoardImage() {
                        const fileInput = document.getElementById('board_image');
                        const statusSpan = document.getElementById('upload-status');
                        const fenInput = document.getElementById('fen');
                        if (!fileInput.files || fileInput.files.length === 0) {
                            statusSpan.textContent = 'Please select a PNG image.';
                            return;
                        }
                        const file = fileInput.files[0];
                        statusSpan.textContent = 'Processing image...';
                        const formData = new FormData();
                        formData.append('image', file);
                        fetch('/upload_board_image', {
                            method: 'POST',
                            body: formData
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.fen) {
                                fenInput.value = data.fen;
                                // Force button update with small delay to ensure DOM updates
                                setTimeout(() => {
                                    validateFENInput();
                                }, 50);
                                if (data.warning) {
                                    statusSpan.textContent = data.warning + ' ' + (data.suggestion || '');
                                    statusSpan.style.color = '#ff9800';
                                } else {
                                    statusSpan.textContent = 'FEN extracted and populated.';
                                    statusSpan.style.color = '#4a2c7a';
                                }
                            } else {
                                statusSpan.textContent = 'Error: ' + (data.error || 'Unknown error');
                                statusSpan.style.color = '#d32f2f';
                            }
                        })
                        .catch(err => {
                            statusSpan.textContent = 'Error: ' + err;
                            statusSpan.style.color = '#d32f2f';
                        });
                    }
                    
                    function handleImageDrop(event) {
                        event.preventDefault();
                        event.stopPropagation();
                        const files = event.dataTransfer.files;
                        if (files && files.length > 0) {
                            const file = files[0];
                            if (file.type === 'image/png' || file.type === 'image/jpeg' || file.type === 'image/jpg') {
                                document.getElementById('board_image').files = files;
                                uploadBoardImage();
                            } else {
                                document.getElementById('upload-status').textContent = 'Please drop a PNG or JPG image.';
                            }
                        }
                    }
                    
                    // Handle paste events globally
                    document.addEventListener('paste', function(event) {
                        const items = event.clipboardData.items;
                        for (let i = 0; i < items.length; i++) {
                            if (items[i].type.indexOf('image') !== -1) {
                                event.preventDefault();
                                const blob = items[i].getAsFile();
                                const dt = new DataTransfer();
                                dt.items.add(blob);
                                document.getElementById('board_image').files = dt.files;
                                uploadBoardImage();
                                break;
                            }
                        }
                    });
                    
                    // Function to copy board as image to clipboard
                    function copyBoardAsImage(boardElementId, boardName) {
                        const boardElement = document.getElementById(boardElementId);
                        if (!boardElement) {
                            alert('Board element not found');
                            return;
                        }
                        
                        // Use html2canvas to convert SVG to image
                        if (typeof html2canvas === 'undefined') {
                            // Fallback: Try to copy the SVG directly
                            const svg = boardElement.querySelector('svg');
                            if (svg) {
                                const svgString = new XMLSerializer().serializeToString(svg);
                                const blob = new Blob([svgString], { type: 'image/svg+xml' });
                                navigator.clipboard.write([
                                    new ClipboardItem({ 'image/svg+xml': blob })
                                ]).then(() => {
                                    alert('Board copied to clipboard as SVG!');
                                }).catch(err => {
                                    alert('Could not copy board to clipboard');
                                });
                            } else {
                                alert('Board element not found');
                            }
                            return;
                        }
                        
                        // Use html2canvas if available
                        html2canvas(boardElement, {
                            backgroundColor: '#1a1a2e',
                            scale: 2,
                            useCORS: true,
                            logging: false
                        }).then(canvas => {
                            canvas.toBlob(blob => {
                                navigator.clipboard.write([
                                    new ClipboardItem({ 'image/png': blob })
                                ]).then(() => {
                                    alert(boardName + ' copied to clipboard!');
                                }).catch(err => {
                                    alert('Could not copy board to clipboard: ' + err.message);
                                });
                            });
                        }).catch(err => {
                            alert('Could not generate image: ' + err.message);
                        });
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
                        
                        // Check if we're showing analysis results and set button states accordingly
                        {% if fen_result %}
                        setAnalyzedState();
                        {% endif %}
                    });
                </script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>

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
                    
                    <form action="/submit" method="post" enctype="multipart/form-data">
                    <div style="margin-bottom: 15px;">
                        <label for="fen" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 18px;">Enter FEN Position:</label>
                        <input type="text" name="fen" id="fen" class="fen-input{% if fen_result %} analyzed{% endif %}" placeholder="Enter FEN notation here..." value="{{current_fen}}">
                        <div style="font-size: 11px; color: #6a5d7a; margin-top: 5px; font-style: italic;">
                            FEN (Forsyth-Edwards Notation) describes a chess position: piece placement, turn, castling rights, en passant, and move counts
                        </div>
                        <div style="margin-top: 12px; text-align: center;">
                            <button type="submit" id="submit-btn" class="submit-btn" disabled title="Please enter a FEN position to analyze">Analyze Position</button>
                            <button type="button" class="reset-btn" onclick="resetForm()">Reset</button>
                        </div>
                    </div>
                    <div class="sample-fens">
                        <div style="font-weight: bold; margin-bottom: 8px; color: #4a2c7a; cursor: pointer; display: flex; align-items: center;" onclick="toggleOpenings()">
                            <span id="openings-toggle" style="display: inline-block; margin-right: 8px; transform: rotate(0deg); transition: transform 0.3s;">▶</span>
                            📚 Opening Positions (Click to expand)
                        </div>
                        <div id="openings-grid" style="display: none; margin-top: 12px; margin-bottom: 15px;">
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                                <!-- London System -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/5N2/PPP1PPPP/RN1QKB1R b KQkq - 4 3', 'London System')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">London System</div>
                                    <div data-fen="rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/5N2/PPP1PPPP/RN1QKB1R b KQkq - 4 3" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- Italian Game -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('r1bqkbnr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4', 'Italian Game')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">Italian Game</div>
                                    <div data-fen="r1bqkbnr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- Sicilian Defense -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2', 'Sicilian Defense')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">Sicilian Defense</div>
                                    <div data-fen="rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- French Defense -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2', 'French Defense')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">French Defense</div>
                                    <div data-fen="rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- Queen's Gambit -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2', 'Queen\\'s Gambit')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">Queen's Gambit</div>
                                    <div data-fen="rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- Ruy Lopez -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3', 'Ruy Lopez (Spanish)')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">Ruy Lopez (Spanish)</div>
                                    <div data-fen="r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- Caro-Kann Defense -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2', 'Caro-Kann Defense')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">Caro-Kann Defense</div>
                                    <div data-fen="rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- Scandinavian Defense -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2', 'Scandinavian Defense')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">Scandinavian Defense</div>
                                    <div data-fen="rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- English Opening -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1', 'English Opening')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">English Opening</div>
                                    <div data-fen="rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- Alekhine's Defense -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1', 'Alekhine\\'s Defense')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">Alekhine's Defense</div>
                                    <div data-fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- King's Indian Attack -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1', 'King\\'s Indian Attack')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">King's Indian Attack</div>
                                    <div data-fen="rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1" style="display: flex; justify-content: center;"></div>
                                </div>
                                <!-- Pirc Defense -->
                                <div style="border: 1px solid #d0c5e8; border-radius: 8px; padding: 10px; background: #f9f7fc; cursor: pointer; transition: all 0.2s;" onclick="showBoardModal('rnbqkbnr/ppppp1pp/5p2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2', 'Pirc Defense')" onmouseover="this.style.boxShadow='0 4px 8px rgba(112,72,163,0.2)'" onmouseout="this.style.boxShadow='none'">
                                    <div style="font-size: 12px; font-weight: bold; color: #4a2c7a; margin-bottom: 6px;">Pirc Defense</div>
                                    <div data-fen="rnbqkbnr/ppppp1pp/5p2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2" style="display: flex; justify-content: center;"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>
                </div>

                {% if fen_result %}
                <div class="recommendations-wrapper">
                    <h3 class="recommendations-header">Move Recommendations</h3>
                    
                    <div class="recommendation-section">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div class="recommend-label" style="margin-bottom: 0 !important;">Stockfish Recommendation:</div>
                            <div style="text-align: right;">
                                <div style="font-size: 1.1em; color: #ffd700; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">Rating: {{fen_result.get('stockfish_score', 'N/A')}}</div>
                                <div style="font-size: 0.75em; color: #b8e6b8; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">(+ = White winning, - = Black winning)</div>
                            </div>
                        </div>
                        <div class="recommend-value">{{fen_result['stockfish']}}</div>
                        {% if fen_result['stockfish_board'] %}
                        <div class="board-container" id="stockfish-board">
                            {{fen_result['stockfish_board']|safe}}
                        </div>
                        <button class="copy-board-btn" onclick="copyBoardAsImage('stockfish-board', 'Stockfish Recommendation Board')">📋 Copy Board</button>
                        {% endif %}
                    </div>
                    
                    <div class="recommendation-section">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div class="recommend-label" style="margin-bottom: 0 !important;">AI Recommendation (Built-in Chess Logic):</div>
                            <div style="text-align: right;">
                                <div style="font-size: 1.1em; color: #ffd700; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">Rating: {{fen_result.get('ai_score', 'N/A')}}</div>
                                <div style="font-size: 0.75em; color: #b8e6b8; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">(+ = White winning, - = Black winning)</div>
                            </div>
                        </div>
                        <div class="recommend-value">{{fen_result['ai']}}</div>
                        {% if fen_result['ai_board'] %}
                        <div class="board-container" id="ai-board">
                            {{fen_result['ai_board']|safe}}
                        </div>
                        <button class="copy-board-btn" onclick="copyBoardAsImage('ai-board', 'AI Recommendation Board')">📋 Copy Board</button>
                        <div style="font-size: 12px; color: #b8e6b8; margin-top: 8px; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">
                            Generated using custom chess principles AI (evaluation-based move scoring)
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endif %}

                <div class="about-section">
                    <h3>About</h3>
                    <h4 style="color: #4a2c7a; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #8e44ad; padding-bottom: 10px;">Component Management</h4>
                    
                    <!-- Application Version Section -->
                    <div style="margin-bottom: 25px; padding: 15px; background-color: {% if app_version_info.update_available %}rgba(255, 152, 0, 0.1){% else %}rgba(142, 68, 173, 0.05){% endif %}; border: 1px solid {% if app_version_info.update_available %}#ff9800{% else %}#d4b3ff{% endif %}; border-radius: 8px;">
                        <h4 style="color: #4a2c7a; margin-bottom: 15px; display: flex; align-items: center;">
                            <span style="font-size: 20px; margin-right: 10px;">🚀</span>Chess Analysis Application 
                            <span style="margin-left: 10px; font-size: 12px; color: #666; font-weight: normal;">← This App</span>
                            {% if app_version_info.update_available %}
                            <span style="margin-left: auto; padding: 4px 8px; background: #ff9800; color: white; border-radius: 12px; font-size: 11px; font-weight: bold;">
                                📋 UPDATE AVAILABLE
                            </span>
                            {% endif %}
                        </h4>
                        <div style="margin-bottom: 10px;"><strong>Current Version:</strong> {{ app_version_info.current }}</div>
                        <div style="margin-bottom: 10px;"><strong>Latest Available:</strong> {{ app_version_info.latest }}</div>
                        <div style="margin-bottom: 15px;"><strong>Status:</strong> 
                            <span style="color:{% if app_version_info.update_available %}orange{% else %}green{% endif %};font-weight:bold;">
                                {% if app_version_info.update_available %}Update Available ({{ app_version_info.latest }}){% else %}Up to Date{% endif %}
                            </span>
                        </div>
                        {% if app_version_info.update_available and app_version_info.release_url %}
                        <div class="engine-buttons">
                            <a href="{{ app_version_info.release_url }}" target="_blank" class="engine-btn" style="text-decoration: none; display: inline-block; color: white;">View Update</a>
                        </div>
                        {% endif %}
                    </div>
                    
                    <!-- Stockfish Engine Section -->
                    <div style="margin-bottom: 25px; padding: 15px; background-color: rgba(142, 68, 173, 0.05); border: 1px solid #d4b3ff; border-radius: 8px;">
                        <h4 style="color: #4a2c7a; margin-bottom: 15px; display: flex; align-items: center;">
                            <span style="font-size: 20px; margin-right: 10px;">♚</span>Stockfish Chess Engine
                        </h4>
                        {% if current %}
                            <div style="margin-bottom: 10px;"><strong>Path:</strong> {{current}}</div>
                            <div style="margin-bottom: 10px;"><strong>Current Version:</strong> {{version}}</div>
                            {% if latest_tag %}<div style="margin-bottom: 10px;"><strong>Latest Available:</strong> {{latest_tag}}</div>{% endif %}
                            <div style="margin-bottom: 15px;"><strong>Status:</strong> 
                                <span style="color:{% if stockfish_update_available %}orange{% else %}green{% endif %};font-weight:bold;">
                                    {% if stockfish_update_available %}Update Available ({{latest_tag}}){% else %}Up to Date{% endif %}
                                </span>
                            </div>
                            <div class="engine-buttons">
                                <form action="/update_engine_now" method="post" style="display: inline;">
                                    <button type="submit" class="engine-btn" {% if not stockfish_update_available %}style="opacity: 0.5;" disabled{% endif %}>Update Now</button>
                                </form>
                                <form action="/rollback_engine_now" method="post" style="display: inline;">
                                      <button type="submit" class="engine-btn" {% if not has_previous_engine() %}style="opacity: 0.5;" disabled{% endif %}>Rollback</button>
                                </form>
                            </div>
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
                        <div style="margin-bottom: 10px;"><strong>Current Version:</strong> {{ dep.current_version }}</div>
                        <div style="margin-bottom: 10px;"><strong>Latest Available:</strong> {{ dep.latest_version }}</div>
                        <div style="margin-bottom: 15px;"><strong>Status:</strong> 
                            <span style="color:{% if dep.update_available %}orange{% else %}green{% endif %};font-weight:bold;">
                                {% if dep.update_available %}Update Available ({{ dep.latest_version }}){% else %}Up to Date{% endif %}
                            </span>
                        </div>
                        <div class="engine-buttons">
                            <form action="/update_package" method="post" style="display: inline;">
                                <input type="hidden" name="package" value="{{ dep.name }}" />
                                <input type="hidden" name="version" value="{{ dep.latest_version }}" />
                                <button type="submit" class="engine-btn" {% if not dep.update_available %}style="opacity: 0.5;" disabled{% endif %}>Update Now</button>
                            </form>
                            <form action="/rollback_package" method="post" style="display: inline;">
                                  <input type="hidden" name="package" value="{{ dep.name }}" />
                                  <button type="submit" class="engine-btn" {% if not has_previous_package(dep.name) %}style="opacity: 0.5;" disabled{% endif %}>Rollback</button>
                            </form>
                        </div>
                    </div>
                    {% endfor %}
                    
                    <div style="text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #d4b3ff; font-size: 12px; color: #7a6b93;">
                        © 2025 Drake Svc LLC. All rights reserved.<br>
                        <a href="https://github.com/AprilLorDrake" target="_blank" style="color: #8b5fbf; text-decoration: none; margin-top: 5px; display: inline-block;">
                            GitHub: AprilLorDrake
                        </a>
                    </div>
                  </div>
                  
                  <!-- Board Modal -->
                  <div id="boardModal" class="board-modal">
                      <div class="board-modal-content">
                          <span class="board-modal-close" onclick="closeBoardModal()">&times;</span>
                          <div id="modalTitle" class="board-modal-title"></div>
                          <div id="modalBoardContainer" style="display: flex; justify-content: center;"></div>
                          <div class="board-modal-buttons">
                              <button id="modalAnalyzeBtn" class="board-modal-btn analyze">Analyze This Position</button>
                              <button class="board-modal-btn close" onclick="closeBoardModal()">Close</button>
                          </div>
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
