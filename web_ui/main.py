from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'session_id' not in session:
        session['session_id'] = ''
    session_id = session['session_id']
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('index.html', session_id=session_id)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
