from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from datetime import datetime
from docx import Document
import os
import config
import shutil

app = Flask(__name__)
app.secret_key = 'config.secret_key'  # Replace this with a secure value
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

client = MongoClient(config.MONGO_URI)
db = client['notes_db']
collection = db['files']
users = db['usernote']  # User collection

# Utility: check allowed file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

# Authentication Decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Home Page (Notes App)
@app.route('/')
@login_required
def index():
    folders = collection.distinct("folder")
    return render_template("index.html", folders=folders, user=session['user'])

# Sign Up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if users.find_one({'username': username}):
            return "Username already exists!"
        hashed_pw = generate_password_hash(password)
        users.insert_one({'username': username, 'email': email, 'password': hashed_pw})
        session['user'] = username
        return redirect('/')
    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            return redirect('/')
        else:
            return "Invalid username or password"
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# Upload File
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    folder_name = request.form['folder_name']
    files = request.files.getlist("files")
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    os.makedirs(folder_path, exist_ok=True)

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(folder_path, filename)
            file.save(file_path)
            collection.insert_one({
                "folder": folder_name,
                "filename": filename,
                "upload_time": datetime.utcnow(),
                "file_type": filename.rsplit('.', 1)[1].lower(),
                "path": file_path
            })

    return redirect(url_for('index'))

# Create Folder
@app.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    folder_name = request.form['folder_name']
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    os.makedirs(folder_path, exist_ok=True)

    if not collection.find_one({"folder": folder_name}):
        collection.insert_one({
            "folder": folder_name,
            "filename": None,
            "upload_time": datetime.utcnow(),
            "file_type": "folder",
            "path": folder_path
        })
    return redirect(url_for('index'))

# Delete File
@app.route('/delete_file/<folder>/<filename>', methods=['POST'])
@login_required
def delete_file(folder, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        collection.delete_one({"folder": folder, "filename": filename})
        return redirect(url_for('view_folder', folder_name=folder))
    return "File not found"

# Delete Folder
@app.route('/delete_folder/<folder>', methods=['POST'])
@login_required
def delete_folder(folder):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        collection.delete_many({"folder": folder})
        return redirect(url_for('index'))
    return "Folder not found"

# View Folder
@app.route('/folder/<folder_name>')
@login_required
def view_folder(folder_name):
    files = list(collection.find({"folder": folder_name}))
    return render_template("folder.html", folder=folder_name, files=files)

# Open File
@app.route('/read/<folder>/<filename>')
@login_required
def read_file(folder, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    ext = filename.rsplit('.', 1)[1].lower()

    if ext == 'txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"<h2>{filename}</h2><pre>{content}</pre><a href='/folder/{folder}'>Back</a>"

    elif ext == 'pdf':
        return f"""
        <h2>{filename}</h2>
        <embed src='/static_view/{folder}/{filename}' width='800px' height='600px' />
        <a href='/folder/{folder}'><button style="{button_style()}">Back</button></a>
        """

    elif ext in ['jpg', 'jpeg', 'png']:
        return f"""
        <h2>{filename}</h2>
        <img src='/static_view/{folder}/{filename}' width='500' />
        <br><a href='/folder/{folder}'><button style="{button_style()}">Back</button></a>
        """

    elif ext in ['doc', 'docx']:
        file_url = url_for('static_view', folder=folder, filename=filename, _external=True)
        return f"""
    <iframe src="https://view.officeapps.live.com/op/embed.aspx?src={file_url}"
            style="width:100%; height:100vh;" frameborder="0"></iframe>
    """

    else:
        return "Unsupported file type"

# Serve PDFs/Images
@app.route('/static_view/<folder>/<filename>')
def static_view(folder, filename):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    return send_from_directory(folder_path, filename)

# Reusable Button Style
def button_style():
    return """
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 10px 20px;
    text-align: center;
    text-decoration: none;
    display: inline-block;
    font-size: 14px;
    margin-top: 10px;
    border-radius: 5px;
    cursor: pointer;
    """

if __name__ == '__main__':
    app.run(debug=True)
