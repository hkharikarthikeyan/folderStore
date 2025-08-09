import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Hari:Hari91959799@cluster1.vpugu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1")
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "txt", "docx"}
secret_key = os.environ.get('SECRET_KEY', '46775285e3cf9bdc4a9015750927d772aa6582dc63f58308df6a10f08c404c3d')
