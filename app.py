from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from datetime import datetime
from docx import Document
import os
import config
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

client = MongoClient(config.MONGO_URI)
db = client['notes_db']
collection = db['files']

# Utility: allowed file check
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    folders = collection.distinct("folder")
    return render_template("index.html", folders=folders)

@app.route('/upload', methods=['POST'])
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

@app.route('/create_folder', methods=['POST'])
def create_folder():
    folder_name = request.form['folder_name']
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Add folder to DB only if no files exist
    if not collection.find_one({"folder": folder_name}):
        collection.insert_one({
            "folder": folder_name,
            "filename": None,
            "upload_time": datetime.utcnow(),
            "file_type": "folder",
            "path": folder_path
        })
    return redirect(url_for('index'))

@app.route('/delete_file/<folder>/<filename>', methods=['POST'])
def delete_file(folder, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        collection.delete_one({"folder": folder, "filename": filename})
        return redirect(url_for('view_folder', folder_name=folder))
    else:
        return "File not found"
@app.route('/delete_folder/<folder>', methods=['POST'])
def delete_folder(folder):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)

    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        collection.delete_many({"folder": folder})
        return redirect(url_for('index'))
    else:
        return "Folder not found"


@app.route('/folder/<folder_name>')
def view_folder(folder_name):
    files = list(collection.find({"folder": folder_name}))
    return render_template("folder.html", folder=folder_name, files=files)

# ✅ New Route: Read/Open File (instead of download)
@app.route('/read/<folder>/<filename>')
def read_file(folder, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    ext = filename.rsplit('.', 1)[1].lower()

    if ext in ['txt']:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"<h2>{filename}</h2><pre>{content}</pre><a href='/folder/{folder}'>Back</a>"

    elif ext in ['pdf']:
        return f"""
        <h2>{filename}</h2>
        <embed src='/static_view/{folder}/{filename}' width='800px' height='600px' />
        <a href='/folder/{folder}'>
        <button style="
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
        ">
            Back
        </button>
    </a>
        """

    elif ext in ['jpg', 'jpeg', 'png']:
        return f"""
    <h2>{filename}</h2>
    <img src='/static_view/{folder}/{filename}' width='500' />
    <br>
    <a href='/folder/{folder}'>
        <button style="
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
        ">
            Back
        </button>
    </a>
    """

    elif ext in ['docx']:
        doc = Document(file_path)
        text = '\n'.join([para.text for para in doc.paragraphs])
        return f"<h2>{filename}</h2><pre>{text}</pre><a href='/folder/{folder}'>Back</a>"

    else:
        return "File type not supported for reading."

# ✅ Helper route to serve PDF/image files inline
@app.route('/static_view/<folder>/<filename>')
def static_view(folder, filename):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    return send_from_directory(folder_path, filename)

if __name__ == '__main__':
    app.run(debug=True)
