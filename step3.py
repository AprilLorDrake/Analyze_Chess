# Read the current file
with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 3. Create enhanced sample positions with template boards and next moves
import chess

def generate_sample_boards():
    """Generate sample board positions with analysis for template display."""
    sample_positions = [
        {
            "name": "Starting Position", 
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "next_moves": ["e2e4", "d2d4", "g1f3", "c2c4"]
        },
        {
            "name": "Scholar''s Mate Setup", 
            "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4",
            "next_moves": ["d1h5", "c4f7", "f3g5"]
        },
        {
            "name": "Queen''s Gambit", 
            "fen": "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2",
            "next_moves": ["d5c4", "g8f6", "e7e6"]
        },
        {
            "name": "King''s Indian Defense", 
            "fen": "rnbqkb1r/pppppp1p/5np1/8/2PP4/2N5/PP2PPPP/R1BQKBNR b KQkq - 3 3",
            "next_moves": ["f8g7", "d7d6", "c7c5"]
        },
        {
            "name": "Sicilian Dragon", 
            "fen": "rnbqkb1r/pp2pppp/3p1n2/2p5/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 0 5",
            "next_moves": ["g2g3", "f1e2", "c1e3"]
        }
    ]
    return sample_positions

# Generate sample board HTML for display
def create_template_boards_section():
    positions = generate_sample_boards()
    html_parts = []
    
    html_parts.append("""                        <div class="sample-fens">
                            <div style="font-weight: bold; margin-bottom: 12px; color: #4a2c7a; font-size: 16px;">Template Positions:</div>
                            <div style="margin-bottom: 15px; color: #666; font-size: 12px; font-style: italic;">
                                Click any position to analyze it. Boards show the position with next move at bottom.
                            </div>""")
    
    for i, pos in enumerate(positions):
        board = chess.Board(pos["fen"])
        # Determine if white or black to move and flip accordingly
        flip_board = board.turn == chess.BLACK
        board_html = board_to_html(board, flip_board=flip_board)
        
        next_move_text = f"Next: {pos[''next_moves''][0] if pos[''next_moves''] else ''N/A''}"
        
        html_parts.append(f"""                            <div style="display: inline-block; margin: 8px; vertical-align: top; text-align: center;">
                                <button type="button" class="sample-fen-btn" onclick="loadSampleFEN(''{pos[''fen'']}'')">
                                    {pos[''name'']}
                                </button>
                                <div style="margin-top: 5px; font-size: 10px; color: #888;">
                                    {next_move_text}
                                </div>
                                <div style="margin-top: 8px; transform: scale(0.7); transform-origin: center;">
                                    {board_html}
                                </div>
                            </div>""")
    
    html_parts.append("""                        </div>""")
    
    return "\\n".join(html_parts)

# Replace the simple sample positions with enhanced template boards
old_sample_section = """                        <div class="sample-fens">
                            <div style="font-weight: bold; margin-bottom: 8px; color: #4a2c7a;">Sample Positions:</div>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN(''rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'')">Starting Position</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN(''r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4'')">Scholar''s Mate Setup</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN(''rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2'')">Queen''s Gambit</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN(''6k1/5ppp/8/8/8/2K5/5PPP/8 w - - 0 1'')">Endgame Position</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN(''r3k2r/ppp2ppp/2n1bn2/2bpp3/2P5/2N1PN2/PPBP1PPP/R1BQKR2 w Qkq - 0 8'')">Tactical Position</button>
                        </div>"""

# This is a placeholder - we need to generate this dynamically in the route
new_sample_section = """                        <!-- Template boards will be generated dynamically -->
                        {{ sample_boards_html | safe }}"""

content = content.replace(old_sample_section, new_sample_section)

# Save the modified content
with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Step 3 completed: Enhanced sample positions setup")
