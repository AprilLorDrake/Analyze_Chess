# Read the current file
with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add input type selection before the FEN input
old_form_section = """                    <form action="/submit" method="post">
                        <div style="margin-bottom: 15px;">
                            <label for="fen" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 18px;">Enter FEN Position:</label>
                            <input type="text" name="fen" id="fen" class="fen-input{% if fen_result %} analyzed{% endif %}" placeholder="Enter FEN notation here..." value="{{current_fen}}">"""

new_form_section = """                    <form action="/submit" method="post">
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 18px;">Input Type:</label>
                            <div style="margin-bottom: 10px;">
                                <input type="radio" id="input_fen" name="input_type" value="fen" checked onchange="toggleInputType()">
                                <label for="input_fen" style="margin-right: 15px; font-weight: normal;">FEN Position</label>
                                <input type="radio" id="input_pgn" name="input_type" value="pgn" onchange="toggleInputType()">
                                <label for="input_pgn" style="font-weight: normal;">PGN Game</label>
                            </div>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label for="fen" id="input_label" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 18px;">Enter FEN Position:</label>
                            <input type="text" name="fen" id="fen" class="fen-input{% if fen_result %} analyzed{% endif %}" placeholder="Enter FEN notation here..." value="{{current_fen}}">"""

content = content.replace(old_form_section, new_form_section)

# Save the modified content
with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Step 1 completed: Added input type selection")
