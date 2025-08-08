import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Hari:Hari91959799@cluster1.vpugu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1")
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "txt", "docx"}
