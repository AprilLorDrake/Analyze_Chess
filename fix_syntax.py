#!/usr/bin/env python3
# Quick fix for the missing closing parenthesis

def main():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the missing closing parenthesis
    content = content.replace(
        "''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, msg=msg, fen_result=fen_result, current_fen=current_fen",
        "''', current=current, version=version, latest_tag=latest_tag, stockfish_update_available=stockfish_update_available, python_deps=python_deps, msg=msg, fen_result=fen_result, current_fen=current_fen)"
    )
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed syntax error - added missing closing parenthesis")

if __name__ == "__main__":
    main()