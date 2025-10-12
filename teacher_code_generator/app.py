from flask import jsonify
import os
import json
import time
from flask import Flask, render_template_string, request, redirect, url_for, session
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this!

TEACHERS_HTML = os.path.join(os.path.dirname(__file__), 'Teachers.html')
GITHUB_TOKEN = 'YOUR_GITHUB_TOKEN'  # Replace with your GitHub token
GITHUB_REPO = 'yourgithubusername/teacher-codes'  # Replace with your repo
GITHUB_FILE = 'codes.json'

# Parse Teachers.html for credentials
def load_teachers():
    with open(TEACHERS_HTML, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        table = soup.find('table')
        teachers = {}
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) == 2:
                tid = cols[0].text.strip()
                pwd = cols[1].text.strip()
                teachers[tid] = pwd
        return teachers

def generate_code(host, duration=3600):
    return f'{host}:{int(time.time())}:{duration}'

def push_code_to_github(code, host, duration):
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}'
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        import base64
        codes = json.loads(base64.b64decode(content['content']).decode('utf-8'))
        sha = content['sha']
    else:
        codes = []
        sha = None
    codes.append({'code': code, 'host': host, 'duration': duration})
    import base64
    data = {
        'message': 'Add new teacher code',
        'content': base64.b64encode(json.dumps(codes).encode('utf-8')).decode('utf-8'),
        'branch': 'main'
    }
    if sha:
        data['sha'] = sha
    r = requests.put(url, headers=headers, data=json.dumps(data))
    return r.status_code == 201 or r.status_code == 200

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tid = request.form['tid']
        pwd = request.form['pwd']
        teachers = load_teachers()
        if tid in teachers and teachers[tid] == pwd:
            session['teacher'] = tid
            return redirect(url_for('generate'))
        else:
            return 'Invalid credentials', 401
    return render_template_string('''
        <form method="post">
            Teacher ID: <input name="tid"><br>
            Password: <input name="pwd" type="password"><br>
            <input type="submit" value="Login">
        </form>
    ''')

@app.route('/generate', methods=['GET', 'POST'])
@app.route('/api/generate', methods=['POST'])
def generate():
    if 'teacher' not in session:
        return redirect(url_for('login'))
    code = None
    if request.method == 'POST':
        host = request.form['host']
        duration = int(request.form.get('duration', 3600))
        code = generate_code(host, duration)
        push_code_to_github(code, host, duration)
    return render_template_string('''
        <form method="post">
            Host: <input name="host"><br>
            Duration (seconds): <input name="duration" value="3600"><br>
            <input type="submit" value="Generate Code">
        </form>
        {% if code %}
        <p>Generated Code: <b>{{ code }}</b></p>
        {% endif %}
    ''', code=code)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
