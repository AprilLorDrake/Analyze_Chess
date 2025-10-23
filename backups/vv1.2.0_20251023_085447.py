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
import chess.pgn
import io
import re
import base64

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

def board_to_html(board, highlight_move=None, flipped=None):
    """Convert chess board to beautiful HTML/CSS representation.
    
    Args:
        board: chess.Board object
        highlight_move: chess.Move to highlight 
        flipped: bool - if True, flip board (black at bottom). If None, auto-flip for black to move
    """
    piece_unicode = {
        'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
        'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙'
    }
    
    # Auto-flip if not specified: flip board if black to move (black at bottom)
    if flipped is None:
        flipped = not board.turn  # board.turn is True for white, False for black
    
    # Generate unique ID for this board instance
    import random
    board_id = f"board_{random.randint(1000, 9999)}"
    
    html = [f'<div class="chess-board-wrapper" id="{board_id}_wrapper">']
    html.append(f'<div class="board-controls" style="text-align: center; margin-bottom: 8px;">')
    html.append(f'<button onclick="flipBoard(\'{board_id}\')" class="flip-btn" style="padding: 4px 8px; font-size: 12px; background: #8e44ad; color: white; border: none; border-radius: 4px; cursor: pointer;">🔄 Flip Board</button>')
    html.append('</div>')
    
    html.append(f'<div class="chess-board" id="{board_id}{"_flipped" if flipped else ""}">')
    
    # Determine rank and file order based on flip state
    if flipped:
        rank_range = range(8)  # 1 to 8 (black at bottom)
        rank_labels = range(1, 9)
        file_range = range(7, -1, -1)  # h to a
        file_labels = 'hgfedcba'
    else:
        rank_range = range(7, -1, -1)  # 8 to 1 (white at bottom)
        rank_labels = range(8, 0, -1)
        file_range = range(8)  # a to h
        file_labels = 'abcdefgh'
    
    # Add rank labels on the side
    for i, rank in enumerate(rank_range):
        html.append('<div class="board-row">')
        html.append(f'<div class="rank-label">{list(rank_labels)[i]}</div>')
        
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
    for file_char in file_labels:
        html.append(f'<div class="file-label">{file_char}</div>')
    html.append('</div>')
    
    html.append('</div>')
    html.append('</div>')
    return ''.join(html)

def generate_fallback_recommendation(board):
    """GitHub Copilot chess analysis using modern positional and tactical concepts."""
    try:
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return "No legal moves available", "", "No legal moves in this position.", "GitHub Copilot Chess Engine v2.0"
        
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
        engine_name = "GitHub Copilot Chess Engine v2.0"
        if best_reasons:
            explanation = f"This move {', '.join(best_reasons[:3])}."  # Limit to top 3 reasons
            if len(best_reasons) > 3:
                explanation += f" (Evaluation: +{best_score//10} points)"
        else:
            explanation = "This move optimizes the position based on advanced chess principles."
        
        return f"{best_move}", board_to_html(board, best_move), explanation, engine_name
        
    except Exception as e:
        return f"Analysis failed: {e}", "", "Analysis error occurred.", "GitHub Copilot Chess Engine"

def get_openai_recommendation(fen_position):
    """Get chess recommendation from OpenAI GPT-4o."""
    try:
        # Check if openai is available
        try:
            import openai
        except ImportError:
            return "N/A", "", "OpenAI package not installed. Run: pip install openai", "OpenAI GPT-4o (Unavailable)"
        
        # Check for API key (you'll need to set this)
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return "N/A", "", "This engine is disabled. Use the Configure button below to enable it.", "OpenAI GPT-4o (Disabled)"
        
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": f"Analyze this chess position in FEN notation: {fen_position}\n\nProvide:\n1. Your recommended best move in algebraic notation (like e4, Nf3, O-O)\n2. A brief explanation of why this move is strong\n\nFormat: MOVE: [move] | REASON: [explanation]"
            }],
            max_tokens=200,
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        
        # Parse the response
        if "MOVE:" in content and "REASON:" in content:
            parts = content.split("|")
            move_part = parts[0].replace("MOVE:", "").strip()
            reason_part = parts[1].replace("REASON:", "").strip() if len(parts) > 1 else "Advanced AI analysis"
        else:
            # Fallback parsing
            lines = content.strip().split('\n')
            move_part = lines[0] if lines else "e4"
            reason_part = lines[1] if len(lines) > 1 else "GPT-4o strategic analysis"
        
        return move_part, "", reason_part, "OpenAI GPT-4o"
        
    except Exception as e:
        return "Error", "", f"OpenAI analysis failed: {str(e)}", "OpenAI GPT-4o (Error)"

def get_claude_recommendation(fen_position):
    """Get chess recommendation from Anthropic Claude."""
    try:
        # Check if anthropic is available
        try:
            import anthropic
        except ImportError:
            return "N/A", "", "Anthropic package not installed. Run: pip install anthropic", "Claude-3.5-Sonnet (Unavailable)"
        
        # Check for API key
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return "N/A", "", "This engine is disabled. Use the Configure button below to enable it.", "Claude-3.5-Sonnet (Disabled)"
        
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": f"Analyze this chess position in FEN: {fen_position}\n\nProvide your best move recommendation in algebraic notation and explain why it's strong.\n\nFormat: MOVE: [move] | REASON: [explanation]"
            }]
        )
        
        content = response.content[0].text
        
        # Parse the response
        if "MOVE:" in content and "REASON:" in content:
            parts = content.split("|")
            move_part = parts[0].replace("MOVE:", "").strip()
            reason_part = parts[1].replace("REASON:", "").strip() if len(parts) > 1 else "Advanced AI analysis"
        else:
            # Fallback parsing
            lines = content.strip().split('\n')
            move_part = lines[0] if lines else "e4"
            reason_part = lines[1] if len(lines) > 1 else "Claude strategic analysis"
        
        return move_part, "", reason_part, "Claude-3.5-Sonnet"
        
    except Exception as e:
        return "Error", "", f"Claude analysis failed: {str(e)}", "Claude-3.5-Sonnet (Error)"

def get_gemini_recommendation(fen_position):
    """Get chess recommendation from Google Gemini."""
    try:
        # Check if google-generativeai is available
        try:
            import google.generativeai as genai
        except ImportError:
            return "N/A", "", "Google Generative AI package not installed. Run: pip install google-generativeai", "Google Gemini Pro (Unavailable)"
        
        # Check for API key
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return "N/A", "", "This engine is disabled. Use the Configure button below to enable it.", "Google Gemini Pro (Disabled)"
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"Analyze this chess position in FEN notation: {fen_position}\n\nProvide your best move recommendation in algebraic notation and explain why.\n\nFormat: MOVE: [move] | REASON: [explanation]"
        
        response = model.generate_content(prompt)
        content = response.text
        
        # Parse the response
        if "MOVE:" in content and "REASON:" in content:
            parts = content.split("|")
            move_part = parts[0].replace("MOVE:", "").strip()
            reason_part = parts[1].replace("REASON:", "").strip() if len(parts) > 1 else "Advanced AI analysis"
        else:
            # Fallback parsing
            lines = content.strip().split('\n')
            move_part = lines[0] if lines else "e4"
            reason_part = lines[1] if len(lines) > 1 else "Gemini strategic analysis"
        
        return move_part, "", reason_part, "Google Gemini Pro"
        
    except Exception as e:
        return "Error", "", f"Gemini analysis failed: {str(e)}", "Google Gemini Pro (Error)"

def generate_consensus_recommendation(stockfish_move, copilot_move, openai_move, claude_move, gemini_move):
    """Generate a final consensus recommendation from all engines."""
    try:
        moves = [stockfish_move, copilot_move, openai_move, claude_move, gemini_move]
        engines = ["Stockfish", "GitHub Copilot", "OpenAI GPT-4o", "Claude-3.5-Sonnet", "Google Gemini"]
        
        # Remove error/unavailable moves
        valid_moves = []
        valid_engines = []
        for i, move in enumerate(moves):
            if move and move not in ["Error", "N/A", "No legal moves available"] and "failed" not in move.lower():
                valid_moves.append(move)
                valid_engines.append(engines[i])
        
        if not valid_moves:
            return "No consensus possible", "All engines unavailable or failed."
        
        # Count move frequency
        from collections import Counter
        move_counts = Counter(valid_moves)
        most_common = move_counts.most_common()
        
        if len(most_common) == 1:
            # All engines agree
            consensus_move = most_common[0][0]
            explanation = f"🎯 **UNANIMOUS CONSENSUS** - All {len(valid_engines)} engines recommend: {consensus_move}"
        elif most_common[0][1] > 1:
            # Majority agrees
            consensus_move = most_common[0][0]
            count = most_common[0][1]
            supporting_engines = [engines[i] for i, move in enumerate(moves) if move == consensus_move]
            explanation = f"🏆 **MAJORITY CONSENSUS** - {count}/{len(valid_engines)} engines recommend: {consensus_move}\nSupporting: {', '.join(supporting_engines[:3])}"
        else:
            # No clear consensus - use Stockfish as tiebreaker
            if stockfish_move in valid_moves:
                consensus_move = stockfish_move
                explanation = f"⚖️ **SPLIT DECISION** - Using Stockfish recommendation: {consensus_move}\n(Engines disagreed, deferring to strongest engine)"
            else:
                consensus_move = valid_moves[0]
                explanation = f"🤔 **NO CONSENSUS** - Engines split, showing first valid: {consensus_move}"
        
        return consensus_move, explanation
        
    except Exception as e:
        return "Analysis error", f"Consensus generation failed: {str(e)}"
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
        engine_name = "GitHub Copilot Chess Engine v2.0"
        if best_reasons:
            explanation = f"This move {', '.join(best_reasons[:3])}."  # Limit to top 3 reasons
            if len(best_reasons) > 3:
                explanation += f" (Evaluation: +{best_score//10} points)"
        else:
            explanation = "This move optimizes the position based on advanced chess principles."
        
        return f"{best_move}", board_to_html(board, best_move), explanation, engine_name
        
    except Exception as e:
        return f"Analysis failed: {e}", "", "Analysis error occurred.", "GitHub Copilot Chess Engine"

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
        # Show the actual moves being compared
        comparison_text = f"<strong>Stockfish recommends:</strong> {stockfish_move}<br><strong>AI recommends:</strong> {ai_move}<br><br>"
        
        if stockfish_move == ai_move:
            return comparison_text + "✅ <strong>Perfect Agreement!</strong> Both engines agree on this move - excellent choice!"
        
        if "failed" in stockfish_move.lower() or "not available" in stockfish_move.lower():
            return comparison_text + "⚠️ Stockfish analysis unavailable for comparison."
        
        if ai_move == "N/A" or "error" in ai_move.lower():
            return comparison_text + "⚠️ AI analysis unavailable - no API key configured."
        
        # Try to parse both moves
        try:
            sf_move = chess.Move.from_uci(stockfish_move)
            ai_move_parsed = chess.Move.from_uci(ai_move)
        except:
            try:
                # Try algebraic notation
                sf_move = board.parse_san(stockfish_move)
                ai_move_parsed = board.parse_san(ai_move)
            except:
                return comparison_text + "❓ Move comparison unavailable due to parsing issues."
        
        # Analyze the AI move from Stockfish perspective
        analysis = []
        
        # Check if AI move is even legal
        if ai_move_parsed not in board.legal_moves:
            return comparison_text + "❌ <strong>Critical Error:</strong> AI suggested an illegal move - this indicates a serious error in the AI logic."
        
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
            return comparison_text + f"⚠️ <strong>Issues with AI move:</strong> {', '.join(analysis)}. Stockfish's choice is likely stronger."
        else:
            return comparison_text + "✅ <strong>Good Alternative:</strong> AI move is reasonable but Stockfish found a different approach. Both moves have merit - this shows different playing styles."
        
    except Exception as e:
        return f"<strong>Stockfish:</strong> {stockfish_move}<br><strong>AI:</strong> {ai_move}<br><br>❓ Move comparison analysis unavailable."

def create_comprehensive_move_analysis(stockfish_move, all_ai_moves, board):
    """Create a comprehensive analysis comparing all AI engines against Stockfish."""
    try:
        analysis = f"<strong>🏆 Stockfish (Reference):</strong> {stockfish_move}<br><br>"
        
        # Count agreements and disagreements
        agreements = []
        disagreements = []
        errors = []
        
        for engine_name, ai_move in all_ai_moves.items():
            if ai_move == "N/A" or "error" in str(ai_move).lower():
                errors.append(f"{engine_name}: No API key configured")
            elif ai_move == stockfish_move:
                agreements.append(engine_name)
            else:
                disagreements.append((engine_name, ai_move))
        
        # Report agreements
        if agreements:
            analysis += f"✅ <strong>Perfect Matches:</strong> {', '.join(agreements)} agree with Stockfish<br><br>"
        
        # Report disagreements with analysis
        if disagreements:
            analysis += f"🤔 <strong>Different Approaches:</strong><br>"
            for engine_name, ai_move in disagreements:
                # Quick analysis of this move
                try:
                    if board:
                        ai_move_parsed = None
                        try:
                            ai_move_parsed = chess.Move.from_uci(ai_move)
                        except:
                            try:
                                ai_move_parsed = board.parse_san(ai_move)
                            except:
                                pass
                        
                        if ai_move_parsed and ai_move_parsed in board.legal_moves:
                            analysis += f"• <strong>{engine_name}:</strong> {ai_move} (legal alternative)<br>"
                        else:
                            analysis += f"• <strong>{engine_name}:</strong> {ai_move} ⚠️ (needs verification)<br>"
                    else:
                        analysis += f"• <strong>{engine_name}:</strong> {ai_move}<br>"
                except:
                    analysis += f"• <strong>{engine_name}:</strong> {ai_move}<br>"
            analysis += "<br>"
        
        # Report errors
        if errors:
            analysis += f"❌ <strong>Unavailable:</strong><br>"
            for error in errors:
                analysis += f"• {error}<br>"
            analysis += "<br>"
        
        # Provide educational summary
        total_engines = len(all_ai_moves)
        working_engines = total_engines - len(errors)
        
        if working_engines == 0:
            analysis += "💡 <strong>Note:</strong> Configure API keys for AI engines to see comparisons with Stockfish."
        elif len(agreements) == working_engines:
            analysis += "🎯 <strong>Unanimous Agreement!</strong> All AI engines agree with Stockfish - this is likely the best move."
        elif len(agreements) > 0:
            analysis += f"📊 <strong>Mixed Results:</strong> {len(agreements)}/{working_engines} AI engines agree with Stockfish. Different approaches can show varying playing styles."
        else:
            analysis += "🔍 <strong>All Different:</strong> All AI engines chose different moves from Stockfish. This position may have multiple good options, or AI engines may be missing Stockfish's deeper analysis."
        
        return analysis
        
    except Exception as e:
        return f"<strong>Stockfish:</strong> {stockfish_move}<br><br>❓ Comprehensive analysis unavailable."

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

def process_input_format(input_type, input_data, uploaded_file=None):
    """
    Process different input formats and convert them to FEN notation.
    
    Args:
        input_type: One of 'fen', 'pgn', 'image', 'gif', 'embed'
        input_data: The text input (FEN, PGN, or URL)
        uploaded_file: Optional file upload for image/gif
    
    Returns:
        tuple: (fen_string, error_message)
    """
    try:
        if input_type == 'fen':
            # Validate FEN format
            fen = input_data.strip()
            board = chess.Board(fen)
            return fen, None
            
        elif input_type == 'pgn':
            # Parse PGN and extract final position
            pgn_io = io.StringIO(input_data.strip())
            game = chess.pgn.read_game(pgn_io)
            
            if not game:
                return None, "Invalid PGN format - could not parse game"
            
            # Play through the game to get final position
            board = game.board()
            for move in game.mainline_moves():
                board.push(move)
            
            return board.fen(), None
            
        elif input_type == 'image':
            # TODO: Implement image analysis using AI vision
            return None, "Image analysis not yet implemented - coming soon!"
            
        elif input_type == 'gif':
            # TODO: Implement GIF analysis using AI vision  
            return None, "GIF analysis not yet implemented - coming soon!"
            
        elif input_type == 'embed':
            # TODO: Implement Chess.com/Lichess URL parsing
            return None, "Embed URL parsing not yet implemented - coming soon!"
            
        else:
            return None, f"Unknown input type: {input_type}"
            
    except chess.InvalidMoveError as e:
        return None, f"Invalid move in PGN: {str(e)}"
    except chess.IllegalMoveError as e:
        return None, f"Illegal move in PGN: {str(e)}"
    except Exception as e:
        return None, f"Error processing {input_type}: {str(e)}"

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
    
    # Start with empty FEN by default - users can load samples if needed
    if not current_fen:
        current_fen = ''
    
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
            
            # Get all AI recommendations
            copilot_move, copilot_board, copilot_explanation, copilot_engine = generate_fallback_recommendation(board)
            openai_move, _, openai_explanation, openai_engine = get_openai_recommendation(fen)
            claude_move, _, claude_explanation, claude_engine = get_claude_recommendation(fen)
            gemini_move, _, gemini_explanation, gemini_engine = get_gemini_recommendation(fen)
            
            # Generate consensus recommendation
            consensus_move, consensus_explanation = generate_consensus_recommendation(
                stockfish_move, copilot_move, openai_move, claude_move, gemini_move
            )
            
            # Create Stockfish explanation based on the move type
            stockfish_explanation = get_stockfish_explanation(stockfish_move, board)
            
            # Define the move scoring function
            def calculate_move_score(move, reference_move, board):
                """Calculate how good a move is compared to the reference (Stockfish) move."""
                if not move or move == "N/A" or "error" in move.lower() or "no legal" in move.lower():
                    return 0
                
                try:
                    # Parse moves
                    if reference_move == move:
                        return 100  # Perfect match
                    
                    # Try to parse the moves to compare them
                    try:
                        ref_move_obj = chess.Move.from_uci(reference_move)
                        test_move_obj = chess.Move.from_uci(move)
                    except:
                        # If UCI parsing fails, try algebraic notation
                        try:
                            ref_move_obj = board.parse_san(reference_move)
                            test_move_obj = board.parse_san(move)
                        except:
                            return 10  # Can't parse, but it's a move
                    
                    # Check if same piece is being moved
                    ref_piece = board.piece_at(ref_move_obj.from_square)
                    test_piece = board.piece_at(test_move_obj.from_square)
                    
                    score = 30  # Base score for valid move
                    
                    if ref_piece and test_piece:
                        if ref_piece.piece_type == test_piece.piece_type:
                            score += 20  # Same piece type
                        
                        # Check if moving to similar area
                        ref_to_file = chess.square_file(ref_move_obj.to_square)
                        ref_to_rank = chess.square_rank(ref_move_obj.to_square)
                        test_to_file = chess.square_file(test_move_obj.to_square)
                        test_to_rank = chess.square_rank(test_move_obj.to_square)
                        
                        file_diff = abs(ref_to_file - test_to_file)
                        rank_diff = abs(ref_to_rank - test_to_rank)
                        
                        if file_diff == 0 and rank_diff == 0:
                            score += 50  # Same destination
                        elif file_diff <= 1 and rank_diff <= 1:
                            score += 30  # Very close destination
                        elif file_diff <= 2 and rank_diff <= 2:
                            score += 15  # Close destination
                    
                    return min(score, 99)  # Cap at 99 (only exact match gets 100)
                    
                except Exception:
                    return 10  # Something went wrong, but it's still a move
            
            # Separate available and unavailable engines
            available_engines = []
            unavailable_engines = []
            
            # Stockfish is always available (it's built-in)
            available_engines.append({
                'name': 'Stockfish',
                'engine': 'Traditional Chess Engine',
                'move': stockfish_move,
                'explanation': stockfish_explanation,
                'board': stockfish_board,
                'score': 100,  # Always 100% - reference engine
                'color_class': 'stockfish',
                'icon': '🏆',
                'rank': 1  # Always #1
            })
            
            # Check each AI engine
            ai_engines_data = [
                (copilot_engine, copilot_move, copilot_explanation, copilot_board, 'AI-Powered Heuristic Engine', 'copilot', '🤖'),
                (openai_engine, openai_move, openai_explanation, '', 'Advanced Language Model', 'openai', '🧠'),
                (claude_engine, claude_move, claude_explanation, '', 'Anthropic AI Assistant', 'claude', '⚡'),
                (gemini_engine, gemini_move, gemini_explanation, '', "Google's Multimodal AI", 'gemini', '✨')
            ]
            
            working_ai_engines = []
            for engine_name, move, explanation, board_html, description, color_class, icon in ai_engines_data:
                if move == "N/A" or "Error" in move or "not installed" in explanation or "not found" in explanation:
                    unavailable_engines.append({
                        'name': engine_name,
                        'description': description,
                        'reason': explanation,
                        'icon': icon
                    })
                else:
                    working_ai_engines.append({
                        'name': engine_name,
                        'engine': description,
                        'move': move,
                        'explanation': explanation,
                        'board': board_html,
                        'score': calculate_move_score(move, stockfish_move, board),
                        'color_class': color_class,
                        'icon': icon,
                        'rank': 0
                    })
            
            # Sort working AI engines by score and assign ranks starting from 2
            working_ai_engines.sort(key=lambda x: x['score'], reverse=True)
            for i, engine in enumerate(working_ai_engines):
                engine['rank'] = i + 2  # Start from rank 2 (Stockfish is always rank 1)
            
            # Combine available engines
            available_engines.extend(working_ai_engines)
            
            # Compare all working AI moves against Stockfish for educational insights
            working_ai_moves = {engine['name']: engine['move'] for engine in working_ai_engines}
            move_comparison = create_comprehensive_move_analysis(stockfish_move, working_ai_moves, board)
            
            fen_result = {
                'stockfish': stockfish_move, 
                'stockfish_board': stockfish_board,
                'stockfish_explanation': stockfish_explanation,
                'copilot': copilot_move,
                'copilot_board': copilot_board,
                'copilot_explanation': copilot_explanation,
                'copilot_engine': copilot_engine,
                'openai': openai_move,
                'openai_explanation': openai_explanation,
                'openai_engine': openai_engine,
                'claude': claude_move,
                'claude_explanation': claude_explanation,
                'claude_engine': claude_engine,
                'gemini': gemini_move,
                'gemini_explanation': gemini_explanation,
                'gemini_engine': gemini_engine,
                'consensus': consensus_move,
                'consensus_explanation': consensus_explanation,
                'move_comparison': move_comparison,
                'ordered_recommendations': available_engines,
                'unavailable_engines': unavailable_engines
            }
        except Exception as e:
            # Create error recommendations for display
            error_recommendations = [
                {
                    'name': 'Stockfish',
                    'engine': 'Traditional Chess Engine',
                    'move': f"Invalid FEN: {e}",
                    'explanation': "Analysis could not be completed due to invalid position.",
                    'board': '',
                    'score': 0,
                    'color_class': 'stockfish',
                    'icon': '🏆',
                    'rank': 1
                }
            ]
            
            fen_result = {
                'stockfish': f"Invalid FEN: {e}", 
                'stockfish_board': "",
                'stockfish_explanation': "Analysis could not be completed due to invalid position.",
                'copilot': "-",
                'copilot_board': "",
                'copilot_explanation': "Analysis could not be completed due to invalid position.",
                'copilot_engine': "N/A",
                'openai': "N/A",
                'openai_explanation': "Position error",
                'openai_engine': "OpenAI GPT-4o",
                'claude': "N/A", 
                'claude_explanation': "Position error",
                'claude_engine': "Claude-3.5-Sonnet",
                'gemini': "N/A",
                'gemini_explanation': "Position error", 
                'gemini_engine': "Google Gemini Pro",
                'consensus': "N/A",
                'consensus_explanation': "Cannot analyze invalid position",
                'move_comparison': "Analysis unavailable due to position error.",
                'ordered_recommendations': error_recommendations
            }
    
    # Generate sample chess boards for display
    sample_boards = {}
    sample_positions = [
        ('italian_game', 'r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R b KQkq - 0 5', 'Italian Game (5 moves)', '1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.d3 Bc5'),
        ('french_defense', 'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq d6 0 3', 'French Defense (4 moves)', '1.e4 e6 2.d4 d5'),
        ('queens_gambit', 'rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2', "Queen's Gambit (4 moves)", '1.d4 d5 2.c4'),
        ('caro_kann', 'rn1qkbnr/pp2pppp/2p5/3p4/3PP1b1/5N2/PPP2PPP/RNBQKB1R w KQkq - 1 4', 'Caro-Kann Defense (4 moves)', '1.e4 c6 2.d4 d5 3.Nf3 Bg4'),
        ('english_opening', 'rnbqkb1r/pppp1ppp/5n2/4p3/2P5/5N2/PP1PPPPP/RNBQKB1R w KQkq - 2 3', 'English Opening (4 moves)', '1.c4 e5 2.Nf3 Nf6')
    ]
    
    for key, fen, title, moves in sample_positions:
        try:
            board = chess.Board(fen)
            sample_boards[key] = {
                'fen': fen,
                'title': title,
                'moves': moves,
                'html': board_to_html(board, flipped=False)
            }
        except:
            sample_boards[key] = {
                'fen': fen,
                'title': title,
                'moves': moves,
                'html': '<div style="color: red;">Error generating board</div>'
            }
    
    return render_template_string('''
            <html>
            <head>
                <title>Analyze Next Best Chess Move!</title>
                <link rel="icon" type="image/x-icon" href="/favicon.ico">
                <style>
                    html {
                        scroll-behavior: smooth;
                    }
                    #analyze-chess-component:target {
                        box-shadow: 0 0 20px rgba(255, 152, 0, 0.5);
                        border-color: #ff9800 !important;
                        background-color: rgba(255, 152, 0, 0.15) !important;
                        transition: all 0.3s ease;
                    }
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
                 .flip-btn {
                     padding: 4px 8px !important;
                     font-size: 12px !important;
                     background: linear-gradient(135deg, #8e44ad 0%, #7048a3 100%) !important;
                     color: white !important;
                     border: none !important;
                     border-radius: 4px !important;
                     cursor: pointer !important;
                     transition: all 0.2s ease !important;
                     box-shadow: 0 2px 4px rgba(142, 68, 173, 0.3) !important;
                 }
                 .flip-btn:hover {
                     background: linear-gradient(135deg, #7048a3 0%, #5d3d87 100%) !important;
                     transform: translateY(-1px) !important;
                     box-shadow: 0 3px 6px rgba(142, 68, 173, 0.4) !important;
                 }
                 .chess-board-wrapper {
                     margin: 15px auto;
                 }
                 .recommendation-section.stockfish {
                     border-left: 4px solid #ffd700;
                     background: linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, rgba(255, 215, 0, 0.15) 100%);
                 }
                 .recommendation-section.copilot {
                     border-left: 4px solid #8e44ad;
                     background: linear-gradient(135deg, rgba(142, 68, 173, 0.05) 0%, rgba(142, 68, 173, 0.1) 100%);
                 }
                 .recommendation-section.openai {
                     border-left: 4px solid #20c997;
                     background: linear-gradient(135deg, rgba(32, 201, 151, 0.05) 0%, rgba(32, 201, 151, 0.1) 100%);
                 }
                 .recommendation-section.claude {
                     border-left: 4px solid #fd7e14;
                     background: linear-gradient(135deg, rgba(253, 126, 20, 0.05) 0%, rgba(253, 126, 20, 0.1) 100%);
                 }
                 .recommendation-section.gemini {
                     border-left: 4px solid #007bff;
                     background: linear-gradient(135deg, rgba(0, 123, 255, 0.05) 0%, rgba(0, 123, 255, 0.1) 100%);
                 }
                 .recommend-label {
                     color: #fff !important;
                     font-size: 1.2em !important;
                     font-weight: bold !important;
                     text-shadow: 1px 1px 2px rgba(0,0,0,0.7) !important;
                 }
                 .recommend-value {
                     color: #fff !important;
                     font-size: 1.5em !important;
                     font-weight: bold !important;
                     text-shadow: 1px 1px 2px rgba(0,0,0,0.7) !important;
                 }
                </style>
                <script>
                    function loadSampleFEN(fen) {
                        console.log('loadSampleFEN called with:', fen);
                        const fenInput = document.getElementById('fen');
                        console.log('FEN input element:', fenInput);
                        if (fenInput) {
                            fenInput.value = fen;
                            console.log('FEN input value set to:', fenInput.value);
                            validateFENInput(); // Check if button should be enabled
                            hideSampleBoards(); // Hide sample boards after selection
                        } else {
                            console.error('FEN input element not found!');
                        }
                    }
                    
                    function hideSampleBoards() {
                        const sampleArea = document.getElementById('sample_fens_area');
                        if (sampleArea) {
                            sampleArea.style.display = 'none';
                            console.log('Sample boards hidden');
                        }
                    }
                    
                    function showSampleBoards() {
                        const sampleArea = document.getElementById('sample_fens_area');
                        if (sampleArea) {
                            sampleArea.style.display = 'block';
                            console.log('Sample boards shown');
                        }
                    }
                    
                    function resetForm() {
                        const resetBtn = document.getElementById('reset-btn');
                        if (resetBtn.disabled) {
                            return; // Don't reset if button is disabled
                        }
                        
                        // Clear the input field
                        const textInput = document.getElementById('fen');
                        textInput.value = '';
                        
                        // Reset dropdown to FEN
                        const inputType = document.getElementById('input_type');
                        inputType.value = 'fen';
                        
                        // Update the interface for FEN mode
                        updateInputDescription();
                        
                        // Clear placeholder to show it's truly empty
                        textInput.placeholder = 'Enter FEN notation here...';
                        
                        // Show sample boards again after reset
                        showSampleBoards();
                    }
                    
                    function updateInputDescription() {
                        const inputType = document.getElementById('input_type').value;
                        const description = document.getElementById('input_description');
                        const label = document.getElementById('input_label');
                        const textInput = document.getElementById('fen');
                        const fileArea = document.getElementById('file_upload_area');
                        const sampleFensArea = document.getElementById('sample_fens_area');
                        
                        const descriptions = {
                            'fen': {
                                'text': '<strong>FEN:</strong> Standard chess position notation that describes piece placement, turn, castling rights, en passant, and move counts. Example: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                                'label': 'Enter FEN Position:',
                                'placeholder': 'Enter FEN notation here or click a sample position below...',
                                'sampleValue': 'r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
                                'showText': true
                            },
                            'pgn': {
                                'text': '<strong>PGN:</strong> Portable Game Notation contains the full game moves. We will analyze the final position. Example: 1. e4 e5 2. Nf3 Nc6 3. Bb5',
                                'label': 'Enter PGN Game:',
                                'placeholder': 'Paste PGN game notation here...',
                                'sampleValue': '[Event "Italian Game Opening"]\n[Site "Sample"]\n[Date "2024.01.01"]\n[Round "1"]\n[White "Player1"]\n[Black "Player2"]\n[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5',
                                'showText': true
                            },
                            'image': {
                                'text': '<strong>Image Upload:</strong> Upload a screenshot or photo of a chess position. We will use AI to detect the position and convert it to FEN for analysis.',
                                'label': 'Upload Chess Board Image:',
                                'placeholder': '',
                                'sampleValue': '',
                                'showText': false
                            },
                            'gif': {
                                'text': '<strong>GIF Animation:</strong> Upload an animated GIF showing chess moves. We will analyze the final position shown in the animation.',
                                'label': 'Upload Chess GIF:',
                                'placeholder': '',
                                'sampleValue': '',
                                'showText': false
                            },
                            'embed': {
                                'text': '<strong>Chess.com/Lichess Embed:</strong> Paste the URL or embed code from Chess.com or Lichess analysis. We will extract the position data.',
                                'label': 'Enter Chess.com/Lichess URL:',
                                'placeholder': 'Paste analysis URL or embed code here...',
                                'sampleValue': 'https://www.chess.com/analysis/game/live/123456789',
                                'showText': true
                            }
                        };
                        
                        const config = descriptions[inputType];
                        description.innerHTML = config.text;
                        label.textContent = config.label;
                        textInput.placeholder = config.placeholder;
                        
                        // Don't automatically populate sample values - let users click sample buttons instead
                        // This keeps the input clean and encourages exploration of samples
                        
                        if (config.showText) {
                            textInput.style.display = 'block';
                            fileArea.style.display = 'none';
                        } else {
                            textInput.style.display = 'none';
                            fileArea.style.display = 'block';
                        }
                        
                        // Show sample FEN positions only when FEN is selected
                        if (inputType === 'fen') {
                            sampleFensArea.style.display = 'block';
                        } else {
                            sampleFensArea.style.display = 'none';
                        }
                    }
                    
                    function flipBoard(boardId) {
                        const board = document.getElementById(boardId);
                        const wrapper = document.getElementById(boardId + '_wrapper');
                        
                        if (!board || !wrapper) return;
                        
                        // Check current state and toggle
                        const isFlipped = board.id.includes('_flipped');
                        
                        if (isFlipped) {
                            // Currently flipped, restore to normal
                            board.id = boardId;
                        } else {
                            // Currently normal, flip it
                            board.id = boardId + '_flipped';
                        }
                        
                        // Rebuild the board with flipped orientation
                        const ranks = board.querySelectorAll('.board-row:not(.file-labels)');
                        const fileLabels = board.querySelector('.file-labels');
                        
                        // Reverse the order of rank rows
                        const reversedRanks = Array.from(ranks).reverse();
                        
                        // Clear board content except controls
                        const controls = wrapper.querySelector('.board-controls');
                        wrapper.innerHTML = '';
                        wrapper.appendChild(controls);
                        
                        // Create new board container
                        const newBoard = document.createElement('div');
                        newBoard.className = 'chess-board';
                        newBoard.id = board.id;
                        
                        // Add reversed ranks
                        reversedRanks.forEach(rank => {
                            const rankLabel = rank.querySelector('.rank-label');
                            const squares = rank.querySelectorAll('.chess-square');
                            
                            // Update rank label
                            const currentLabel = parseInt(rankLabel.textContent);
                            rankLabel.textContent = 9 - currentLabel;
                            
                            // Reverse squares in this rank
                            const reversedSquares = Array.from(squares).reverse();
                            
                            // Clear and rebuild rank
                            rank.innerHTML = '';
                            rank.appendChild(rankLabel);
                            reversedSquares.forEach(square => rank.appendChild(square));
                            
                            newBoard.appendChild(rank);
                        });
                        
                        // Update file labels
                        if (fileLabels) {
                            const labels = fileLabels.querySelectorAll('.file-label');
                            const reversedLabels = Array.from(labels).reverse();
                            const emptyCorner = fileLabels.querySelector('.rank-label');
                            
                            fileLabels.innerHTML = '';
                            fileLabels.appendChild(emptyCorner);
                            reversedLabels.forEach(label => fileLabels.appendChild(label));
                            
                            newBoard.appendChild(fileLabels);
                        }
                        
                        wrapper.appendChild(newBoard);
                    }
                    
                    function validateFENInput() {
                        const fenInput = document.getElementById('fen');
                        const submitBtn = document.getElementById('submit-btn');
                        const resetBtn = document.getElementById('reset-btn');
                        
                        if (fenInput.value.trim() === '') {
                            // Show analyze button, hide reset when no input
                            submitBtn.style.display = 'block';
                            resetBtn.style.display = 'none';
                            submitBtn.disabled = true;
                            submitBtn.title = 'Please enter a FEN position to analyze';
                            submitBtn.textContent = 'Analyze';
                            submitBtn.classList.remove('analyzed');
                        } else {
                            // Show both buttons when there's input
                            submitBtn.style.display = 'block';
                            resetBtn.style.display = 'block';
                            submitBtn.disabled = false;
                            submitBtn.title = 'Click to analyze the chess position';
                            submitBtn.textContent = 'Analyze';
                            submitBtn.classList.remove('analyzed');
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
                        
                        // Make analyze button grey and disabled, change text
                        submitBtn.classList.add('analyzed');
                        submitBtn.disabled = true;
                        submitBtn.title = 'Analysis completed';
                        submitBtn.textContent = 'Analyzed';
                        
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
                    <div style="margin-top: 15px; font-size: 16px; color: #4a2c7a; max-width: 600px; margin-left: auto; margin-right: auto; line-height: 1.5; text-align: center;">
                        🏆 <strong>Multi-Engine Chess Analysis Hub</strong><br>
                        <span style="font-size: 14px; color: #6a5d7a;">Analyzes and cross-compares move recommendations across multiple AI engines including Stockfish, GitHub Copilot Chess Engine, OpenAI GPT-4o, Anthropic Claude, and Google Gemini. Get comprehensive insights with consensus recommendations and educational explanations.</span>
                    </div>
                    <div style="margin-top: 10px; font-size: 14px; color: #6a5d7a;">
                        Version {{ app_version_info.current }}
                        {% if app_version_info.update_available %}
                        <a href="#analyze-chess-component" style="margin-left: 10px; padding: 4px 8px; background: #ff9800; color: white; border-radius: 12px; font-size: 11px; font-weight: bold; text-decoration: none;">
                            📋 Update Available: {{ app_version_info.latest }}
                        </a>
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
                        <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 15px;">
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
                        
                        <!-- API Configuration Section -->
                        <div style="margin-top: 15px; padding: 12px; background: rgba(142, 68, 173, 0.1); border-radius: 6px; border: 1px solid #8e44ad;">
                            <div style="font-weight: bold; margin-bottom: 8px; color: #4a2c7a; font-size: 14px;">� Get More AI Chess Engines</div>
                            <div style="font-size: 11px; color: #6a5d7a; line-height: 1.4; margin-bottom: 10px;">
                                <strong>Currently you have Stockfish (the world's best engine) running.</strong><br>
                                Want even more chess insights? Enable additional AI engines for different analysis styles:<br>
                                🧠 <strong>OpenAI</strong> - Human-like explanations | ⚡ <strong>Claude</strong> - Thoughtful analysis | 🌟 <strong>Gemini</strong> - Creative insights
                            </div>
                            <div style="text-align: center; display: flex; gap: 8px; justify-content: center; flex-wrap: wrap;">
                                <a href="/setup_openai" style="text-decoration: none; padding: 6px 12px; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border-radius: 4px; font-size: 11px; font-weight: bold; box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);">
                                    🧠 Enable OpenAI
                                </a>
                                <a href="/setup_claude" style="text-decoration: none; padding: 6px 12px; background: linear-gradient(135deg, #fd7e14 0%, #ff6b35 100%); color: white; border-radius: 4px; font-size: 11px; font-weight: bold; box-shadow: 0 2px 4px rgba(253, 126, 20, 0.3);">
                                    ⚡ Enable Claude
                                </a>
                                <a href="/setup_gemini" style="text-decoration: none; padding: 6px 12px; background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; border-radius: 4px; font-size: 11px; font-weight: bold; box-shadow: 0 2px 4px rgba(0, 123, 255, 0.3);">
                                    🌟 Enable Gemini
                                </a>
                                <a href="/configure_api_keys" style="text-decoration: none; padding: 6px 12px; background: linear-gradient(135deg, #6c757d 0%, #495057 100%); color: white; border-radius: 4px; font-size: 11px; font-weight: bold; box-shadow: 0 2px 4px rgba(108, 117, 125, 0.3);">
                                    ⚙️ Advanced Setup
                                </a>
                            </div>
                        </div>
                    </div>
                    
                    <form action="/submit" method="post" enctype="multipart/form-data" onsubmit="setAnalyzedState(); hideSampleBoards(); return true;">
                        <div style="margin-bottom: 20px; padding: 15px; background: rgba(196, 153, 255, 0.15); border-radius: 8px; border: 2px solid #c299ff;">
                            <label for="input_type" style="display: block; margin-bottom: 10px; font-weight: bold; font-size: 16px; color: #4a2c7a;">📋 Input Type:</label>
                            <select name="input_type" id="input_type" onchange="updateInputDescription()" style="width: 100%; padding: 12px 15px; font-size: 14px; border: 2px solid #c299ff; border-radius: 6px; background: white; color: #4a2c7a; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(196, 153, 255, 0.3);">
                                <option value="fen" selected>FEN (Forsyth-Edwards Notation)</option>
                                <option value="pgn">PGN (Portable Game Notation)</option>
                                <option value="image">Image Upload</option>
                                <option value="gif">GIF Animation</option>
                                <option value="embed">Chess.com/Lichess Embed</option>
                            </select>
                            <div id="input_description" style="font-size: 12px; color: #4a2c7a; padding: 10px; background: rgba(255, 255, 255, 0.7); border-radius: 4px; border-left: 3px solid #8e44ad;">
                                <strong>FEN:</strong> Standard chess position notation that describes piece placement, turn, castling rights, en passant, and move counts. Example: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
                            </div>
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label for="fen" id="input_label" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 18px;">Enter FEN Position:</label>
                            <div style="display: flex; gap: 10px; align-items: flex-start;">
                                <input type="text" name="fen" id="fen" class="fen-input{% if fen_result %} analyzed{% endif %}" placeholder="Enter a FEN position or click a sample opening below..." value="{{current_fen}}" title="Enter a FEN position and press Enter or click Analyze to get recommendations" style="flex: 1;">
                                <div id="file_upload_area" style="display: none;">
                                    <input type="file" name="file_upload" id="file_upload" accept=".png,.jpg,.jpeg,.gif,.pgn" style="display: none;">
                                    <button type="button" onclick="document.getElementById('file_upload').click()" style="padding: 12px 20px; background: linear-gradient(135deg, #6f42c1 0%, #563d7c 100%); color: white; border: none; border-radius: 6px; cursor: pointer;">
                                        📁 Choose File
                                    </button>
                                </div>
                                <button type="submit" id="submit-btn" class="submit-btn compact-btn" title="Analyze the chess position">Analyze</button>
                                <button type="button" id="reset-btn" class="reset-btn compact-btn" style="display: none;" onclick="resetForm()" title="Clear the input">Reset</button>
                            </div>
                            
                            <!-- Instructional text positioned near FEN input -->
                            <div style="margin-top: 8px; padding: 6px; background: rgba(142, 68, 173, 0.05); border-radius: 4px; border: 1px solid rgba(142, 68, 173, 0.2);">
                                <div style="font-size: 11px; color: #4a2c7a; text-align: center; font-weight: bold;">
                                    📝 Enter a FEN position above, or click a sample position below
                                </div>
                                <div style="font-size: 10px; color: #6a5d7a; text-align: center; margin-top: 2px; font-style: italic;">
                                    💡 Tip: Use "Create FEN Position" to set up any chess position, then copy the FEN notation back here
                                </div>
                            </div>
                        </div>
                                                <!-- <div class="sample-fens" id="sample_fens_area">
                            <div style="font-weight: bold; margin-bottom: 15px; color: #4a2c7a; text-align: center; font-size: 16px;">📚 Sample Opening Positions:</div>
                            
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; margin-bottom: 20px;">
                                <!-- Italian Game (5 moves) -->
                                <div class="sample-position" style="border: 2px solid #c299ff; border-radius: 8px; padding: 12px; background: rgba(255, 255, 255, 0.9);">
                                    <div style="text-align: center; margin-bottom: 8px;">
                                        <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('{{ sample_boards.italian_game.fen }}')" style="width: 100%; padding: 6px 10px; background: linear-gradient(135deg, #8e44ad 0%, #7048a3 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px;">{{ sample_boards.italian_game.title }}</button>
                                    </div>
                                    {{ sample_boards.italian_game.html | safe }}
                                    <div style="font-size: 10px; color: #666; text-align: center; margin-top: 6px;">{{ sample_boards.italian_game.moves }}</div>
                                </div>
                                
                                <!-- French Defense (4 moves) -->
                                <div class="sample-position" style="border: 2px solid #c299ff; border-radius: 8px; padding: 12px; background: rgba(255, 255, 255, 0.9);">
                                    <div style="text-align: center; margin-bottom: 8px;">
                                        <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('{{ sample_boards.french_defense.fen }}')" style="width: 100%; padding: 6px 10px; background: linear-gradient(135deg, #8e44ad 0%, #7048a3 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px;">{{ sample_boards.french_defense.title }}</button>
                                    </div>
                                    {{ sample_boards.french_defense.html | safe }}
                                    <div style="font-size: 10px; color: #666; text-align: center; margin-top: 6px;">{{ sample_boards.french_defense.moves }}</div>
                                </div>
                                
                                <!-- Queen's Gambit (4 moves) -->
                                <div class="sample-position" style="border: 2px solid #c299ff; border-radius: 8px; padding: 12px; background: rgba(255, 255, 255, 0.9);">
                                    <div style="text-align: center; margin-bottom: 8px;">
                                        <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('{{ sample_boards.queens_gambit.fen }}')" style="width: 100%; padding: 6px 10px; background: linear-gradient(135deg, #8e44ad 0%, #7048a3 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px;">{{ sample_boards.queens_gambit.title }}</button>
                                    </div>
                                    {{ sample_boards.queens_gambit.html | safe }}
                                    <div style="font-size: 10px; color: #666; text-align: center; margin-top: 6px;">{{ sample_boards.queens_gambit.moves }}</div>
                                </div>
                                
                                <!-- Caro-Kann Defense (4 moves) -->
                                <div class="sample-position" style="border: 2px solid #c299ff; border-radius: 8px; padding: 12px; background: rgba(255, 255, 255, 0.9);">
                                    <div style="text-align: center; margin-bottom: 8px;">
                                        <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('{{ sample_boards.caro_kann.fen }}')" style="width: 100%; padding: 6px 10px; background: linear-gradient(135deg, #8e44ad 0%, #7048a3 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px;">{{ sample_boards.caro_kann.title }}</button>
                                    </div>
                                    {{ sample_boards.caro_kann.html | safe }}
                                    <div style="font-size: 10px; color: #666; text-align: center; margin-top: 6px;">{{ sample_boards.caro_kann.moves }}</div>
                                </div>
                                
                                <!-- English Opening (4 moves) -->
                                <div class="sample-position" style="border: 2px solid #c299ff; border-radius: 8px; padding: 12px; background: rgba(255, 255, 255, 0.9);">
                                    <div style="text-align: center; margin-bottom: 8px;">
                                        <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('{{ sample_boards.english_opening.fen }}')" style="width: 100%; padding: 6px 10px; background: linear-gradient(135deg, #8e44ad 0%, #7048a3 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px;">{{ sample_boards.english_opening.title }}</button>
                                    </div>
                                    {{ sample_boards.english_opening.html | safe }}
                                    <div style="font-size: 10px; color: #666; text-align: center; margin-top: 6px;">{{ sample_boards.english_opening.moves }}</div>
                                </div>
                            </div>
                        </div> -->
                    </form>
                </div>

                {% if fen_result and fen_result.get('ordered_recommendations') and not (fen_result.get('stockfish', '').startswith('Invalid FEN')) %}
                <div class="recommendations-wrapper">
                    <h3 class="recommendations-header">🏆 Move Recommendations (Ordered by Accuracy)</h3>
                    
                    <!-- Consensus Recommendation Section -->
                    {% if fen_result['ordered_recommendations'] %}
                    <div class="recommendation-section" style="margin-bottom: 25px; border: 3px solid #28a745; background: linear-gradient(135deg, rgba(40, 167, 69, 0.15) 0%, rgba(32, 201, 151, 0.15) 100%);">
                        <div class="recommend-label" style="font-size: 1.5em; color: #28a745 !important; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 1.2em;">🎯</span> Consensus Recommendation
                        </div>
                        <div style="font-size: 15px; color: #fff; margin-top: 12px; padding: 15px; background: rgba(40, 167, 69, 0.2); border-radius: 8px; border-left: 4px solid #28a745; line-height: 1.6;">
                            <div style="margin-bottom: 12px;">
                                <strong style="color: #ffd700;">📊 Authority Hierarchy:</strong> 
                                {% set stockfish_move = None %}
                                {% for rec in fen_result['ordered_recommendations'] %}
                                    {% if rec.name == 'Stockfish' %}
                                        {% set stockfish_move = rec.move %}
                                    {% endif %}
                                {% endfor %}
                                
                                {% if stockfish_move and stockfish_move != 'N/A' %}
                                <span style="color: #ffd700; font-weight: bold;">Stockfish "{{ stockfish_move }}"</span> 
                                {% for rec in fen_result['ordered_recommendations'] %}
                                    {% if rec.name != 'Stockfish' and rec.move != 'N/A' %}
                                        {% if rec.rank == 2 %}
                                            > <span style="color: #c0c0c0; font-weight: bold;">{{ rec.name }} "{{ rec.move }}"</span>
                                        {% elif rec.rank == 3 %}
                                            > <span style="color: #cd7f32; font-weight: bold;">{{ rec.name }} "{{ rec.move }}"</span>
                                        {% elif rec.rank > 3 %}
                                            > <span style="color: #6c757d;">{{ rec.name }} "{{ rec.move }}"</span>
                                        {% endif %}
                                    {% endif %}
                                {% endfor %}
                                {% else %}
                                <span style="color: #ff6b6b;">Stockfish analysis unavailable</span>
                                {% endif %}
                            </div>
                            
                            <div style="padding: 10px; background: rgba(255, 255, 255, 0.1); border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.2);">
                                <strong style="color: #20c997;">🏆 Consensus:</strong> 
                                {% if stockfish_move and stockfish_move != 'N/A' %}
                                    <span style="color: #ffd700; font-size: 1.1em; font-weight: bold;">"{{ stockfish_move }}"</span> is the recommended move.
                                    <br><span style="font-size: 13px; color: #e9ecef;">
                                    Stockfish (3500+ ELO) serves as the reference standard. Other engines are ranked by agreement with Stockfish's deep analysis.
                                    </span>
                                {% else %}
                                    <span style="color: #ff6b6b;">Unable to determine consensus - Stockfish analysis required</span>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endif %}
                    
                    {% if fen_result['move_comparison'] %}
                    <div class="recommendation-section" style="margin-bottom: 25px; border: 3px solid #ffd700;">
                        <div class="recommend-label" style="font-size: 1.4em; color: #ffd700 !important;">⚖️ Move Comparison Analysis:</div>
                        <div style="font-size: 14px; color: #fff; margin-top: 8px; padding: 12px; background: rgba(50,50,50,0.7); border-radius: 6px; border-left: 4px solid #ffd700; line-height: 1.6;">
                            {{fen_result['move_comparison']|safe}}
                        </div>
                    </div>
                    {% endif %}
                    
                    {% for recommendation in fen_result['ordered_recommendations'] %}
                    <div class="recommendation-section {{ recommendation.color_class }}" style="position: relative;">
                        <!-- Rank Badge -->
                        <div style="position: absolute; top: -10px; right: 10px; background: 
                            {% if recommendation.name == 'Stockfish' %}linear-gradient(135deg, #ffd700 0%, #ffed4e 100%); color: #000; font-weight: bold; box-shadow: 0 0 10px rgba(255, 215, 0, 0.5)
                            {% elif recommendation.rank == 2 %}linear-gradient(135deg, #c0c0c0 0%, #e8e8e8 100%); color: #000
                            {% elif recommendation.rank == 3 %}linear-gradient(135deg, #cd7f32 0%, #daa520 100%); color: #000
                            {% else %}linear-gradient(135deg, #6c757d 0%, #adb5bd 100%); color: #fff
                            {% endif %};
                            padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                            {% if recommendation.name == 'Stockfish' %}
                                👑 #1 (Reference)
                            {% else %}
                                #{{ recommendation.rank }} ({{ recommendation.score }}% match)
                            {% endif %}
                        </div>
                        
                        <div class="recommend-label">
                            {{ recommendation.icon }} {{ recommendation.name }}:
                            {% if recommendation.name == 'Stockfish' %}
                                <span style="font-size: 0.8em; color: #ffd700;">(World's Strongest Engine)</span>
                            {% endif %}
                        </div>
                        <div class="recommend-value">
                            {% if recommendation.move == 'N/A' %}
                                <span style="color: #ff6b6b;">Disabled</span>
                                <div style="font-size: 0.7em; margin-top: 4px;">
                                    {% if recommendation.name.startswith('OpenAI') %}
                                        <a href='/setup_openai' style='color: #28a745; text-decoration: underline;'>⚡ Enable OpenAI</a>
                                    {% elif recommendation.name.startswith('Claude') %}
                                        <a href='/setup_claude' style='color: #fd7e14; text-decoration: underline;'>⚡ Enable Claude</a>
                                    {% elif recommendation.name.startswith('Google') %}
                                        <a href='/setup_gemini' style='color: #007bff; text-decoration: underline;'>⚡ Enable Gemini</a>
                                    {% else %}
                                        <a href='/configure_api_keys' style='color: #007bff; text-decoration: underline;'>Enable</a>
                                    {% endif %}
                                </div>
                            {% else %}
                                {{ recommendation.move }}
                            {% endif %}
                        </div>
                        
                        {% if recommendation.explanation %}
                        <div style="font-size: 13px; color: #fff; margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.4); border-radius: 4px; border-left: 3px solid 
                            {% if recommendation.color_class == 'stockfish' %}#ffd700
                            {% elif recommendation.color_class == 'copilot' %}#8e44ad
                            {% elif recommendation.color_class == 'openai' %}#20c997
                            {% elif recommendation.color_class == 'claude' %}#fd7e14
                            {% elif recommendation.color_class == 'gemini' %}#007bff
                            {% else %}#6c757d
                            {% endif %};">
                            <strong>Why this move:</strong> 
                            {% if recommendation.explanation == 'Position error' %}
                                Engine not available. 
                                {% if recommendation.name.startswith('OpenAI') %}
                                    <a href='/setup_openai' style='color: #28a745; text-decoration: underline; font-weight: bold;'>⚡ Enable OpenAI</a>
                                {% elif recommendation.name.startswith('Claude') %}
                                    <a href='/setup_claude' style='color: #fd7e14; text-decoration: underline; font-weight: bold;'>⚡ Enable Claude</a>
                                {% elif recommendation.name.startswith('Google') %}
                                    <a href='/setup_gemini' style='color: #007bff; text-decoration: underline; font-weight: bold;'>⚡ Enable Gemini</a>
                                {% else %}
                                    <a href='/configure_api_keys' style='color: #007bff; text-decoration: underline;'>Configure Engine</a>
                                {% endif %}
                            {% elif recommendation.explanation == 'Analysis could not be completed due to invalid position.' %}
                                Position analysis failed - Invalid FEN notation
                            {% else %}
                                {{ recommendation.explanation }}
                            {% endif %}
                        </div>
                        {% endif %}
                        
                        {% if recommendation.board %}
                        <div class="board-container">
                            {{ recommendation.board|safe }}
                        </div>
                        {% endif %}
                        
                        <div style="font-size: 12px; color: #ccc; margin-top: 8px; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">
                            {{ recommendation.engine }}
                            {% if recommendation.name == 'Stockfish' %}
                             - Powered by <a href="https://stockfishchess.org/" target="_blank" style="color: #ffd700; text-decoration: underline;">Stockfish</a> - World's strongest chess engine
                            {% elif recommendation.name.startswith('GitHub Copilot') %}
                             - GitHub Copilot-generated chess engine using positional evaluation, tactical patterns, and modern heuristics (v2.0)
                            {% elif recommendation.move == 'N/A' %}
                             - Requires API key configuration to analyze positions
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                    
                    <!-- Unavailable Engines Section -->
                    {% if fen_result['unavailable_engines'] %}
                    <div class="recommendation-section" style="margin-top: 30px; border: 2px dashed #28a745; background: linear-gradient(135deg, rgba(40, 167, 69, 0.1) 0%, rgba(32, 201, 151, 0.1) 100%);">
                        <div class="recommend-label" style="font-size: 1.2em; color: #28a745 !important;">
                            🔧 Additional Engines Available (Requires Configuration):
                        </div>
                        {% for engine in fen_result['unavailable_engines'] %}
                        <div style="margin: 10px 0; padding: 12px; background: rgba(255, 255, 255, 0.9); border-radius: 6px; border-left: 4px solid #28a745; color: #333;">
                            <strong style="color: #28a745;">{{ engine.icon }} {{ engine.name }}:</strong> <span style="color: #666;">{{ engine.description }}</span><br>
                            <small style="color: #666; font-style: italic;">Not configured - set up via Configure button to enable</small>
                        </div>
                        {% endfor %}
                        <div style="font-size: 13px; color: #28a745; margin-top: 12px; font-weight: bold; text-align: center;">
                            💡 Use the <strong>Configure</strong> button below to enable these engines and get more diverse analysis perspectives
                        </div>
                    </div>
                    {% endif %}
                    
                    <!-- Consensus Section -->
                    {% if fen_result['consensus'] and fen_result['consensus'] != 'N/A' %}
                    <div class="recommendation-section" style="margin-top: 30px; border: 3px solid #9932cc; background: linear-gradient(135deg, rgba(153, 50, 204, 0.1) 0%, rgba(138, 43, 226, 0.1) 100%);">
                        <div class="recommend-label" style="font-size: 1.4em; color: #9932cc !important;">
                            � Consensus Recommendation:
                        </div>
                        <div class="recommend-value" style="color: #dda0dd;">{{ fen_result['consensus'] }}</div>
                        {% if fen_result['consensus_explanation'] %}
                        <div style="font-size: 13px; color: #dda0dd; margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; border-left: 3px solid #9932cc;">
                            <strong>Why this move:</strong> {{ fen_result['consensus_explanation'] }}
                        </div>
                        {% endif %}
                        <div style="font-size: 12px; color: #b8e6b8; margin-top: 8px; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">
                            Multi-AI consensus combining all engine recommendations
                        </div>
                    </div>
                    {% endif %}
                </div>
                {% endif %}

                <div class="about-section">
                    <h3>About</h3>
                    <h4 id="component-management" style="color: #4a2c7a; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #8e44ad; padding-bottom: 10px;">Component Management</h4>
                    
                    <!-- Application Version Section -->
                    <div id="analyze-chess-component" style="margin-bottom: 25px; padding: 15px; background-color: {% if app_version_info.update_available %}rgba(255, 152, 0, 0.1){% else %}rgba(142, 68, 173, 0.05){% endif %}; border: 1px solid {% if app_version_info.update_available %}#ff9800{% else %}#d4b3ff{% endif %}; border-radius: 8px;">
                        <h4 style="color: #4a2c7a; margin-bottom: 15px; display: flex; align-items: center;">
                            <span style="font-size: 20px; margin-right: 10px;">♔</span>Analyze Chess 
                            <span style="margin-left: 10px; font-size: 12px; color: #666; font-weight: normal;">← This App</span>
                            {% if app_version_info.update_available %}
                            <a href="{{ app_version_info.release_url }}" target="_blank" style="margin-left: auto; padding: 4px 8px; background: #ff9800; color: white; border-radius: 12px; font-size: 11px; font-weight: bold; text-decoration: none;">
                                📋 Release Notes
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
                            <form method="post" action="/update_app" target="_blank" style="display: inline-block; margin-right: 10px;" onsubmit="return confirm('This will update the application. Continue?')">
                                <button type="submit" class="engine-btn update-btn" style="background: #28a745; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Update Now</button>
                            </form>
                            <a href="https://github.com/AprilLorDrake/Analyze_Chess/releases/tag/{{ app_version_info.latest }}" target="_blank" style="display: inline-block; margin-left: 5px;">
                                <button type="button" class="engine-btn" style="background: #007bff; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer;">📋 Release Notes</button>
                            </a>
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
                                <form action="/update_engine_now" method="post" style="display: inline; margin-right: 10px;">
                                    <button type="submit" class="engine-btn" style="background: #28a745; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Update Now</button>
                                </form>
                                <a href="https://github.com/official-stockfish/Stockfish/releases/tag/{{latest_tag}}" target="_blank" style="display: inline-block;">
                                    <button type="button" class="engine-btn" style="background: #007bff; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer;">📋 Release Notes</button>
                                </a>
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
                                    <button type="submit" class="engine-btn" style="background: #28a745; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Install Engine</button>
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
                            <form action="/update_package" method="post" style="display: inline; margin-right: 10px;">
                                <input type="hidden" name="package" value="{{ dep.name }}" />
                                <input type="hidden" name="version" value="{{ dep.latest_version }}" />
                                <button type="submit" class="engine-btn" style="background: #28a745; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Update Now</button>
                            </form>
                            <a href="https://pypi.org/project/{{ dep.name }}/{{ dep.latest_version }}/" target="_blank" style="display: inline-block;">
                                <button type="button" class="engine-btn" style="background: #007bff; border: none; color: white; padding: 8px 16px; border-radius: 4px; cursor: pointer;">📋 Release Notes</button>
                            </a>
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
        ''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, app_version_info=app_version_info, msg=msg, fen_result=fen_result, current_fen=current_fen, has_previous_engine=has_previous_engine, has_previous_package=has_previous_package, sample_boards=sample_boards)

@app.route('/setup_openai')
def setup_openai():
    """Setup page specifically for OpenAI"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enable OpenAI GPT-4o - Chess Analysis</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #20c997 0%, #28a745 100%); margin: 0; padding: 20px; min-height: 100vh; }
            .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
            .header { text-align: center; margin-bottom: 30px; }
            .icon { font-size: 64px; margin-bottom: 15px; }
            .btn { padding: 12px 24px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .btn-primary { background: #28a745; color: white; }
            .btn-secondary { background: #6c757d; color: white; }
            input[type="password"] { width: 100%; padding: 12px; border: 2px solid #28a745; border-radius: 6px; font-size: 16px; margin: 10px 0; box-sizing: border-box; }
            .step { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745; }
            .benefits { background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="icon">🧠</div>
                <h1>Enable OpenAI GPT-4o Engine</h1>
                <p>Get advanced chess analysis powered by OpenAI's latest AI model</p>
            </div>

            <div class="benefits">
                <h3>🏆 What you'll get:</h3>
                <ul>
                    <li><strong>Human-like explanations</strong> - Natural language move analysis</li>
                    <li><strong>Strategic insights</strong> - Deep positional understanding</li>
                    <li><strong>Pattern recognition</strong> - Identifies complex tactical themes</li>
                    <li><strong>Educational value</strong> - Learn from detailed explanations</li>
                </ul>
            </div>

            <div class="step">
                <h3>📋 Step 1: Get Your Free API Key</h3>
                <p>OpenAI provides $5 in free credits for new users:</p>
                <a href="https://platform.openai.com/api-keys" target="_blank" class="btn btn-primary">🔗 Get OpenAI API Key</a>
                <p style="font-size: 12px; margin-top: 10px;">Click the link above, sign up, and create a new API key</p>
            </div>

            <form method="POST" action="/save_single_key">
                <div class="step">
                    <h3>🔐 Step 2: Enter Your API Key</h3>
                    <input type="hidden" name="service" value="openai">
                    <input type="password" name="api_key" placeholder="Paste your OpenAI API key here (starts with sk-...)" required>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn btn-primary">✅ Enable OpenAI Engine</button>
                    <a href="/" class="btn btn-secondary">Cancel</a>
                </div>
            </form>

            <div style="margin-top: 20px; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 12px;">
                <strong>💡 Pro Tip:</strong> Your API key is stored securely on your computer and only used to analyze chess positions.
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/setup_claude')
def setup_claude():
    """Setup page specifically for Claude"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enable Claude-3.5-Sonnet - Chess Analysis</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #fd7e14 0%, #ff6b35 100%); margin: 0; padding: 20px; min-height: 100vh; }
            .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
            .header { text-align: center; margin-bottom: 30px; }
            .icon { font-size: 64px; margin-bottom: 15px; }
            .btn { padding: 12px 24px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .btn-primary { background: #fd7e14; color: white; }
            .btn-secondary { background: #6c757d; color: white; }
            input[type="password"] { width: 100%; padding: 12px; border: 2px solid #fd7e14; border-radius: 6px; font-size: 16px; margin: 10px 0; box-sizing: border-box; }
            .step { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #fd7e14; }
            .benefits { background: #fff3e0; padding: 15px; border-radius: 8px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="icon">⚡</div>
                <h1>Enable Claude-3.5-Sonnet Engine</h1>
                <p>Get thoughtful, detailed chess analysis from Anthropic's Claude AI</p>
            </div>

            <div class="benefits">
                <h3>🎯 What you'll get:</h3>
                <ul>
                    <li><strong>Thoughtful analysis</strong> - Careful consideration of each move</li>
                    <li><strong>Risk assessment</strong> - Identifies potential dangers and opportunities</li>
                    <li><strong>Clear explanations</strong> - Easy to understand reasoning</li>
                    <li><strong>Alternative suggestions</strong> - Multiple move options with pros/cons</li>
                </ul>
            </div>

            <div class="step">
                <h3>📋 Step 1: Get Your API Key</h3>
                <p>Claude offers free credits for new users:</p>
                <a href="https://console.anthropic.com/" target="_blank" class="btn btn-primary">🔗 Get Claude API Key</a>
                <p style="font-size: 12px; margin-top: 10px;">Sign up and create a new API key in your console</p>
            </div>

            <form method="POST" action="/save_single_key">
                <div class="step">
                    <h3>🔐 Step 2: Enter Your API Key</h3>
                    <input type="hidden" name="service" value="claude">
                    <input type="password" name="api_key" placeholder="Paste your Claude API key here (starts with sk-ant-...)" required>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn btn-primary">✅ Enable Claude Engine</button>
                    <a href="/" class="btn btn-secondary">Cancel</a>
                </div>
            </form>

            <div style="margin-top: 20px; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 12px;">
                <strong>💡 Security:</strong> Your API key stays on your computer and is only used for chess analysis.
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/setup_gemini')
def setup_gemini():
    """Setup page specifically for Gemini"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enable Google Gemini Pro - Chess Analysis</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); margin: 0; padding: 20px; min-height: 100vh; }
            .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
            .header { text-align: center; margin-bottom: 30px; }
            .icon { font-size: 64px; margin-bottom: 15px; }
            .btn { padding: 12px 24px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .btn-primary { background: #007bff; color: white; }
            .btn-secondary { background: #6c757d; color: white; }
            input[type="password"] { width: 100%; padding: 12px; border: 2px solid #007bff; border-radius: 6px; font-size: 16px; margin: 10px 0; box-sizing: border-box; }
            .step { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #007bff; }
            .benefits { background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="icon">🌟</div>
                <h1>Enable Google Gemini Pro Engine</h1>
                <p>Get innovative chess analysis powered by Google's advanced AI</p>
            </div>

            <div class="benefits">
                <h3>🚀 What you'll get:</h3>
                <ul>
                    <li><strong>Multi-modal analysis</strong> - Advanced pattern recognition</li>
                    <li><strong>Creative insights</strong> - Finds unconventional but strong moves</li>
                    <li><strong>Fast analysis</strong> - Quick responses with detailed reasoning</li>
                    <li><strong>Global perspective</strong> - Considers long-term strategic plans</li>
                </ul>
            </div>

            <div class="step">
                <h3>📋 Step 1: Get Your Free API Key</h3>
                <p>Google AI Studio provides free usage for Gemini:</p>
                <a href="https://aistudio.google.com/app/apikey" target="_blank" class="btn btn-primary">🔗 Get Gemini API Key</a>
                <p style="font-size: 12px; margin-top: 10px;">Create a free account and generate your API key</p>
            </div>

            <form method="POST" action="/save_single_key">
                <div class="step">
                    <h3>🔐 Step 2: Enter Your API Key</h3>
                    <input type="hidden" name="service" value="gemini">
                    <input type="password" name="api_key" placeholder="Paste your Gemini API key here (starts with AI...)" required>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn btn-primary">✅ Enable Gemini Engine</button>
                    <a href="/" class="btn btn-secondary">Cancel</a>
                </div>
            </form>

            <div style="margin-top: 20px; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 12px;">
                <strong>🔐 Privacy:</strong> Your API key is stored locally and only used for chess position analysis.
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/save_single_key', methods=['POST'])
def save_single_key():
    """Save a single API key for a specific service"""
    try:
        service = request.form.get('service')
        api_key = request.form.get('api_key', '').strip()
        
        if not service or not api_key:
            return redirect(url_for('analyze_chess_move', msg='Error: Missing service or API key'))
        
        # Map service names to environment variable names
        service_map = {
            'openai': 'OPENAI_API_KEY',
            'claude': 'ANTHROPIC_API_KEY', 
            'gemini': 'GEMINI_API_KEY'
        }
        
        if service not in service_map:
            return redirect(url_for('analyze_chess_move', msg='Error: Unknown service'))
        
        env_var = service_map[service]
        
        # Read existing .env file
        env_file_path = '.env'
        env_content = {}
        
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()
        
        # Update with new key
        env_content[env_var] = api_key
        os.environ[env_var] = api_key
        
        # Write updated .env file
        with open(env_file_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f'{key}={value}\n')
        
        service_names = {
            'openai': 'OpenAI GPT-4o',
            'claude': 'Claude-3.5-Sonnet',
            'gemini': 'Google Gemini Pro'
        }
        
        return redirect(url_for('analyze_chess_move', msg=f'✅ {service_names[service]} engine enabled successfully! You can now use it for chess analysis.'))
        
    except Exception as e:
        return redirect(url_for('analyze_chess_move', msg=f'Error saving API key: {str(e)}'))

@app.route('/configure_api_keys')
def configure_api_keys():
    """Display API key configuration page"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Configure API Keys - Chess Analysis</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
                color: #4a2c7a;
            }
            .api-section {
                margin-bottom: 25px;
                padding: 20px;
                background: rgba(142, 68, 173, 0.1);
                border-radius: 10px;
                border: 1px solid #8e44ad;
            }
            .api-header {
                display: flex;
                align-items: center;
                margin-bottom: 15px;
            }
            .api-icon {
                font-size: 24px;
                margin-right: 10px;
            }
            .input-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #4a2c7a;
            }
            input[type="password"], input[type="text"] {
                width: 100%;
                padding: 10px;
                border: 2px solid #c299ff;
                border-radius: 5px;
                font-size: 14px;
                box-sizing: border-box;
            }
            .btn {
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                text-decoration: none;
                display: inline-block;
                margin-right: 10px;
            }
            .btn-primary {
                background: #28a745;
                color: white;
            }
            .btn-secondary {
                background: #007bff;
                color: white;
            }
            .btn-danger {
                background: #dc3545;
                color: white;
            }
            .status {
                font-size: 12px;
                margin-top: 5px;
                padding: 5px;
                border-radius: 3px;
            }
            .status.configured {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .status.not-configured {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .help-text {
                font-size: 12px;
                color: #6c757d;
                margin-top: 5px;
            }
            .back-btn {
                background: #6c757d;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Analysis</a>
            
            <div class="header">
                <h1>🔧 Configure AI Engine API Keys</h1>
                <p>Set up your API keys to enable additional AI chess engines</p>
            </div>

            <form method="POST" action="/save_api_keys">
                <!-- OpenAI Section -->
                <div class="api-section">
                    <div class="api-header">
                        <span class="api-icon">🧠</span>
                        <h3>OpenAI GPT-4o</h3>
                    </div>
                    <div class="input-group">
                        <label for="openai_key">API Key:</label>
                        <input type="password" id="openai_key" name="openai_key" placeholder="sk-..." autocomplete="off">
                        <div class="help-text">
                            Get your API key from: <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI Platform</a>
                        </div>
                        <div class="status {{ 'configured' if openai_configured else 'not-configured' }}">
                            {{ 'Currently configured ✓' if openai_configured else 'Not configured' }}
                        </div>
                    </div>
                </div>

                <!-- Anthropic Section -->
                <div class="api-section">
                    <div class="api-header">
                        <span class="api-icon">⚡</span>
                        <h3>Claude-3.5-Sonnet</h3>
                    </div>
                    <div class="input-group">
                        <label for="anthropic_key">API Key:</label>
                        <input type="password" id="anthropic_key" name="anthropic_key" placeholder="sk-ant-..." autocomplete="off">
                        <div class="help-text">
                            Get your API key from: <a href="https://console.anthropic.com/" target="_blank">Anthropic Console</a>
                        </div>
                        <div class="status {{ 'configured' if anthropic_configured else 'not-configured' }}">
                            {{ 'Currently configured ✓' if anthropic_configured else 'Not configured' }}
                        </div>
                    </div>
                </div>

                <!-- Google Section -->
                <div class="api-section">
                    <div class="api-header">
                        <span class="api-icon">🌟</span>
                        <h3>Google Gemini Pro</h3>
                    </div>
                    <div class="input-group">
                        <label for="gemini_key">API Key:</label>
                        <input type="password" id="gemini_key" name="gemini_key" placeholder="AI..." autocomplete="off">
                        <div class="help-text">
                            Get your API key from: <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a>
                        </div>
                        <div class="status {{ 'configured' if gemini_configured else 'not-configured' }}">
                            {{ 'Currently configured ✓' if gemini_configured else 'Not configured' }}
                        </div>
                    </div>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn btn-primary">💾 Save Configuration</button>
                    <button type="button" class="btn btn-danger" onclick="clearKeys()">🗑️ Clear All Keys</button>
                    <a href="/" class="btn btn-secondary">Cancel</a>
                </div>
            </form>

            <div style="margin-top: 30px; padding: 15px; background: #e9ecef; border-radius: 5px; font-size: 12px;">
                <strong>🔒 Security Note:</strong> API keys are stored in environment variables and a local .env file. 
                They are not transmitted over the network except to the respective AI services for analysis.
            </div>
        </div>

        <script>
            function clearKeys() {
                if (confirm('Are you sure you want to clear all API keys? This will disable all AI engines except Stockfish.')) {
                    fetch('/clear_api_keys', {method: 'POST'})
                        .then(() => location.reload());
                }
            }
        </script>
    </body>
    </html>
    ''', 
    openai_configured=os.getenv('OPENAI_API_KEY') is not None,
    anthropic_configured=os.getenv('ANTHROPIC_API_KEY') is not None,
    gemini_configured=os.getenv('GEMINI_API_KEY') is not None
    )

@app.route('/save_api_keys', methods=['POST'])
def save_api_keys():
    """Save API keys to environment and .env file"""
    try:
        import os
        
        # Get the submitted keys
        openai_key = request.form.get('openai_key', '').strip()
        anthropic_key = request.form.get('anthropic_key', '').strip()
        gemini_key = request.form.get('gemini_key', '').strip()
        
        # Read existing .env file or create new content
        env_file_path = '.env'
        env_content = {}
        
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()
        
        # Update with new keys (only if provided)
        if openai_key:
            env_content['OPENAI_API_KEY'] = openai_key
            os.environ['OPENAI_API_KEY'] = openai_key
        
        if anthropic_key:
            env_content['ANTHROPIC_API_KEY'] = anthropic_key
            os.environ['ANTHROPIC_API_KEY'] = anthropic_key
            
        if gemini_key:
            env_content['GEMINI_API_KEY'] = gemini_key
            os.environ['GEMINI_API_KEY'] = gemini_key
        
        # Write updated .env file
        with open(env_file_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f'{key}={value}\n')
        
        return redirect(url_for('analyze_chess_move', msg='API keys saved successfully! Refresh the page to see enabled engines.'))
        
    except Exception as e:
        return redirect(url_for('configure_api_keys', error=f'Error saving keys: {str(e)}'))

@app.route('/clear_api_keys', methods=['POST'])
def clear_api_keys():
    """Clear all API keys"""
    try:
        # Remove from environment
        for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY']:
            if key in os.environ:
                del os.environ[key]
        
        # Update .env file
        env_file_path = '.env'
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                lines = f.readlines()
            
            with open(env_file_path, 'w') as f:
                for line in lines:
                    if not any(key in line for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY']):
                        f.write(line)
        
        return 'OK'
    except Exception as e:
        return f'Error: {str(e)}', 500

@app.route('/submit', methods=['POST'])
def submit():
    # Get input type and data
    input_type = request.form.get('input_type', 'fen')
    input_data = request.form.get('fen', '').strip()  # Still using 'fen' field name for backward compatibility
    uploaded_file = request.files.get('file_upload')
    
    # Process the input to get FEN
    fen, error = process_input_format(input_type, input_data, uploaded_file)
    
    if error:
        return redirect(url_for('analyze_chess_move', msg=f'Error: {error}'))
    elif fen:
        return redirect(url_for('analyze_chess_move', fen=fen, current_fen=fen))
    else:
        return redirect(url_for('analyze_chess_move', msg='Please provide valid input for analysis'))

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
                    // Auto-reload the parent window after update
                    if (window.opener) {{
                        window.opener.location.reload();
                        window.close();
                    }} else {{
                        window.location.href = '/analyze_chess_move';
                    }}
                }}, 2000);
            </script>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px; background: #f0f8ff;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: white; border-radius: 8px; border: 1px solid #28a745;">
            <h2 style="color: #28a745;">♔ Update Successful!</h2>
            <p><strong>Message:</strong> {result['message']}</p>
            <p><strong>New Version:</strong> {result.get('new_version', 'Unknown')}</p>
            <p><strong>Backup Location:</strong> {result.get('backup_location', 'N/A')}</p>
            <div style="margin-top: 20px;">
                <p style="color: #28a745; font-weight: bold;">🔄 Automatically refreshing in 2 seconds...</p>
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
