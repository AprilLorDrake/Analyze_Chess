# Read the current file
with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 2. Enhance board_to_html function with flip capability and larger, warmer boards
old_board_function = """def board_to_html(board, highlight_move=None):
    \"\"\"Convert chess board to beautiful HTML/CSS representation.\"\"\"
    html = ["<div class=\"chess-board\">"]
    
    for rank in range(7, -1, -1):  # 8 to 1
        html.append("<div class=\"board-row\">")
        for file in range(8):  # a to h
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            
            # Determine square color
            is_light = (rank + file) % 2 == 1
            square_class = "light" if is_light else "dark"
            
            # Check if this square should be highlighted
            is_highlighted = False
            if highlight_move:
                is_highlighted = square == highlight_move.from_square or square == highlight_move.to_square
            
            # Build square HTML
            square_html = f"<div class=\"square {square_class}\""
            if is_highlighted:
                square_html += " style=\"background-color: #90EE90 !important;\""
            square_html += ">"
            
            # Add piece if present
            if piece:
                piece_symbol = piece.unicode_symbol()
                square_html += f"<span class=\"piece\">{piece_symbol}</span>"
            
            square_html += "</div>"
            html.append(square_html)
        
        html.append("</div>")
    
    html.append("</div>")
    return "\\n".join(html)"""

new_board_function = """def board_to_html(board, highlight_move=None, flip_board=False):
    \"\"\"Convert chess board to beautiful HTML/CSS representation with enhanced styling.\"\"\"
    html = ["<div class=\"chess-board\">"]
    
    # Determine rank order based on flip_board
    rank_range = range(8) if flip_board else range(7, -1, -1)
    
    for rank in rank_range:
        html.append("<div class=\"board-row\">")
        # Determine file order based on flip_board  
        file_range = range(7, -1, -1) if flip_board else range(8)
        
        for file in file_range:
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            
            # Determine square color with warmer tones
            is_light = (rank + file) % 2 == 1
            square_class = "light" if is_light else "dark"
            
            # Check if this square should be highlighted
            is_highlighted = False
            if highlight_move:
                is_highlighted = square == highlight_move.from_square or square == highlight_move.to_square
            
            # Build square HTML
            square_html = f"<div class=\"square {square_class}\""
            if is_highlighted:
                square_html += " style=\"background-color: #90EE90 !important;\""
            square_html += ">"
            
            # Add piece if present
            if piece:
                piece_symbol = piece.unicode_symbol()
                square_html += f"<span class=\"piece\">{piece_symbol}</span>"
            
            square_html += "</div>"
            html.append(square_html)
        
        html.append("</div>")
    
    html.append("</div>")
    return "\\n".join(html)"""

content = content.replace(old_board_function, new_board_function)

# Save the modified content
with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Step 2 completed: Enhanced board_to_html with flip capability")
