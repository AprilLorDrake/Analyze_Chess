import re

def main():
    # Read the current app.py file
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. First, update the analyze_chess_move function to handle current_fen parameter
    pattern1 = r"(def analyze_chess_move\(\):\s+import os\s+global engine_path\s+# Determine current engine status and ensure variables are defined.*?msg = request\.args\.get\('msg', ''\))"
    replacement1 = r"\1\n    current_fen = request.args.get('current_fen', '')"
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
    
    # 2. Update the template rendering call to include current_fen
    pattern2 = r"(return render_template_string\('''.*?''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, msg=msg, fen_result=fen_result)\)"
    replacement2 = r"return render_template_string(template_html, current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, msg=msg, fen_result=fen_result, current_fen=current_fen)"
    
    # 3. Extract the template and modify it
    template_start = content.find("return render_template_string('''")
    template_end = content.find("''', current=current")
    
    if template_start == -1 or template_end == -1:
        print("Could not find template boundaries")
        return False
    
    # Extract just the template content
    template_content = content[template_start + len("return render_template_string('''"):template_end]
    
    # Modify the template to add our new features
    updated_template = template_content.replace(
        '<input type="text" name="fen" id="fen" class="fen-input" placeholder="Enter FEN notation here...">',
        '<input type="text" name="fen" id="fen" class="fen-input{% if fen_result %} analyzed{% endif %}" placeholder="Enter FEN notation here..." value="{{current_fen}}">'
    )
    
    # Add the sample FEN buttons and reset functionality
    form_replacement = '''                        <div class="sample-fens">
                            <div style="font-weight: bold; margin-bottom: 8px; color: #4a2c7a;">Sample Positions:</div>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')">Starting Position</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4')">Scholar's Mate Setup</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2')">Queen's Gambit</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('6k1/5ppp/8/8/8/2K5/5PPP/8 w - - 0 1')">Endgame Position</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('r3k2r/ppp2ppp/2n1bn2/2bpp3/2P5/2N1PN2/PPBP1PPP/R1BQKR2 w Qkq - 0 8')">Tactical Position</button>
                        </div>
                        
                        <button type="submit" class="submit-btn">Analyze Position</button>
                        <button type="button" class="reset-btn" onclick="resetForm()">Reset</button>'''
    
    updated_template = updated_template.replace(
        '<button type="submit" class="submit-btn">Analyze Position</button>',
        form_replacement
    )
    
    # Add CSS for the new elements
    css_additions = '''                    .fen-input.analyzed { background-color: #f0f8ff; color: #666; }
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
                    }'''
    
    updated_template = updated_template.replace(
        '.submit-btn:hover { ',
        css_additions + '\n                    .submit-btn:hover { '
    )
    
    # Add JavaScript for the new functionality
    js_addition = '''                <script>
                    function loadSampleFEN(fen) {
                        document.getElementById('fen').value = fen;
                    }
                    function resetForm() {
                        window.location.href = '/';
                    }
                </script>'''
    
    updated_template = updated_template.replace(
        '</head>',
        js_addition + '\n            </head>'
    )
    
    # Replace the template in the main content
    new_content = content[:template_start] + f"template_html = '''{updated_template}'''\n    " + replacement2 + content[template_end + len("''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, msg=msg, fen_result=fen_result)"):]
    
    # Update the submit function to preserve FEN
    pattern3 = r"(def submit\(\):.*?if fen:\s+return redirect\(url_for\('analyze_chess_move', fen=fen\)\))"
    replacement3 = r"def submit():\n    fen = request.form.get('fen', '').strip()\n    \n    # Redirect to main page with FEN parameter for analysis\n    if fen:\n        return redirect(url_for('analyze_chess_move', fen=fen, current_fen=fen))"
    new_content = re.sub(pattern3, replacement3, new_content, flags=re.DOTALL)
    
    # Write the updated file
    with open('app.py.updated', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Updated app.py.updated created successfully!")
    return True

if __name__ == "__main__":
    main()