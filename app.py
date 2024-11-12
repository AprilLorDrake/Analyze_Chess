from flask import Flask, request, render_template_string
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string('''
        <form action="/submit" method="post">
            FEN: <input type="text" name="fen"><br>
            <input type="submit" value="Submit">
        </form>
    ''')

@app.route('/submit', methods=['POST'])
def submit():
    fen = request.form['fen']
    with open('analyze_chess.py', 'r') as file:
        script = file.read()

    # Replace the FEN line in the script
    script = script.replace(
        'fen = "foo"',
        f'fen = "{fen}"'
    )

    with open('analyze_chess_temp.py', 'w') as file:
        file.write(script)

    # Run the modified script and capture the output
    result = subprocess.run(['python', 'analyze_chess_temp.py'], capture_output=True, text=True)

    return f"Best move: {result.stdout}"

if __name__ == '__main__':
    app.run(debug=True)
