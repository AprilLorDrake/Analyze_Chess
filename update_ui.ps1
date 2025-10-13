# PowerShell script to update app.py with UI improvements

# Read the current file
$content = Get-Content "app.py" -Raw

# 1. Add current_fen parameter to analyze_chess_move function
$content = $content -replace "(msg = request\.args\.get\('msg', ''\))","`$1`n    current_fen = request.args.get('current_fen', '')"

# 2. Update the input field to preserve value and add analyzed class
$content = $content -replace 'class="fen-input" placeholder="Enter FEN notation here\.\.\.">', 'class="fen-input{% if fen_result %} analyzed{% endif %}" placeholder="Enter FEN notation here..." value="{{current_fen}}">'

# 3. Add sample FEN buttons - find the button line and replace it
$buttonReplacement = @"
                        <div class="sample-fens">
                            <div style="font-weight: bold; margin-bottom: 8px; color: #4a2c7a;">Sample Positions:</div>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')">Starting Position</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4')">Scholar's Mate Setup</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2')">Queen's Gambit</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('6k1/5ppp/8/8/8/2K5/5PPP/8 w - - 0 1')">Endgame Position</button>
                            <button type="button" class="sample-fen-btn" onclick="loadSampleFEN('r3k2r/ppp2ppp/2n1bn2/2bpp3/2P5/2N1PN2/PPBP1PPP/R1BQKR2 w Qkq - 0 8')">Tactical Position</button>
                        </div>
                        
                        <button type="submit" class="submit-btn">Analyze Position</button>
                        <button type="button" class="reset-btn" onclick="resetForm()">Reset</button>
"@

$content = $content -replace '<button type="submit" class="submit-btn">Analyze Position</button>', $buttonReplacement

# 4. Add CSS for new elements - find the submit-btn hover style and add our CSS before it
$cssAdditions = @"
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
"@

$content = $content -replace '(\s+\.submit-btn:hover \{)', "$cssAdditions`n`$1"

# 5. Add JavaScript - find </head> and add script before it
$jsAddition = @"
                <script>
                    function loadSampleFEN(fen) {
                        document.getElementById('fen').value = fen;
                    }
                    function resetForm() {
                        window.location.href = '/';
                    }
                </script>
"@

$content = $content -replace '(\s+</head>)', "$jsAddition`n`$1"

# 6. Update the template rendering to include current_fen
$content = $content -replace "(''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, msg=msg, fen_result=fen_result)\)", "''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, msg=msg, fen_result=fen_result, current_fen=current_fen)"

# 7. Update submit function to preserve FEN
$content = $content -replace "(return redirect\(url_for\('analyze_chess_move', fen=fen\)\))", "return redirect(url_for('analyze_chess_move', fen=fen, current_fen=fen))"

# Write the updated content
$content | Out-File "app.py.new" -Encoding UTF8

Write-Host "Created app.py.new with UI improvements!"