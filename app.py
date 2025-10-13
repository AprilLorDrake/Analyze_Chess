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

def board_to_html(board, highlight_move=None):
    """Convert chess board to beautiful HTML/CSS representation."""
    piece_unicode = {
        'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
        'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙'
    }
    
    html = ['<div class="chess-board">']
    
    # Add rank labels on the side
    for rank in range(7, -1, -1):  # 8 to 1
        html.append('<div class="board-row">')
        html.append(f'<div class="rank-label">{rank + 1}</div>')
        
        for file in range(8):  # a to h
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
    for file_char in 'abcdefgh':
        html.append(f'<div class="file-label">{file_char}</div>')
    html.append('</div>')
    
    html.append('</div>')
    return ''.join(html)

def generate_fallback_recommendation(board):
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
        
        return f"{best_move}", board_to_html(board, best_move)
        
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
    current = engine_path or find_stockfish()
    version = get_engine_version(current) if current else 'not installed'
    latest_tag = get_latest_stockfish_tag()
    latest_num = _extract_numeric_version(latest_tag or '')
    curr_num = _extract_numeric_version(version)
    stockfish_update_available = bool(latest_num and curr_num and latest_num != curr_num)
    
    # Get Python dependencies information
    python_deps = get_python_dependencies_info()
    
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
            # Fallback AI recommendation - simple chess logic
            fallback_ai, ai_board = generate_fallback_recommendation(board)
            fen_result = {
                'stockfish': stockfish_move, 
                'stockfish_board': stockfish_board,
                'ai': fallback_ai,
                'ai_board': ai_board
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
                    });
                </script>

            </head>
            <body>
                <div class="header">
                    <img src="/assets/chess_icon.png" alt="Chess Icon" style="height:64px;vertical-align:middle;margin-right:12px;">
                    <span style="font-size:2em;font-weight:bold;vertical-align:middle;">Analyze Next Best Chess Move!</span>
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
                            <input type="text" name="fen" id="fen" class="fen-input{% if fen_result %} analyzed{% endif %}" placeholder="Enter FEN notation here..." value="{{current_fen}}">
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
                        
                        <button type="submit" id="submit-btn" class="submit-btn" disabled title="Please enter a FEN position to analyze">Analyze Position</button>
                        <button type="button" class="reset-btn" onclick="resetForm()">Reset</button>
                    </form>
                </div>

                {% if fen_result %}
                <div class="recommendations-wrapper">
                    <h3 class="recommendations-header">Move Recommendations</h3>
                    
                    <div class="recommendation-section">
                        <div class="recommend-label">Stockfish Recommendation:</div>
                        <div class="recommend-value">{{fen_result['stockfish']}}</div>
                        {% if fen_result['stockfish_board'] %}
                        <div class="board-container">
                            {{fen_result['stockfish_board']|safe}}
                        </div>
                        {% endif %}
                    </div>
                    
                    <div class="recommendation-section">
                        <div class="recommend-label">AI Recommendation (Built-in Chess Logic Engine):</div>
                        <div class="recommend-value">{{fen_result['ai']}}</div>
                        {% if fen_result['ai_board'] %}
                        <div class="board-container">
                            {{fen_result['ai_board']|safe}}
                        </div>
                        {% endif %}
                        <div style="font-size: 12px; color: #b8e6b8; margin-top: 8px; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">
                            Generated using custom chess principles AI (evaluation-based move scoring)
                        </div>
                    </div>
                </div>
                {% endif %}

                <div class="about-section">
                    <h3>About</h3>
                    <h4 style="color: #4a2c7a; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #8e44ad; padding-bottom: 10px;">Component Management</h4>
                    
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
              </body>
              </html>
        ''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, msg=msg, fen_result=fen_result, current_fen=current_fen, has_previous_engine=has_previous_engine, has_previous_package=has_previous_package)

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
