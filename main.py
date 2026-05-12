from fileinput import filename

from flask import Flask, render_template, request, redirect, jsonify
from pypdf import PdfReader
from werkzeug.utils import secure_filename
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import hashlib

load_dotenv()
app = Flask(__name__)



UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("cache", exist_ok=True)

client = OpenAI(api_key=os.getenv("API_KEY"))

def analyze_resume(text):
    prompt = f"""You are a resume analyzer expert. Analyze this resume and return JSON EXACTLY in this format:
{{
  "spelling": {{"score": 100, "issues": ""}},
  "grammar": {{"score": 100, "issues": ""}},
  "clarity": {{"score": 100}},
  "relevance": {{"score": 100}},
  "tone": {{"score": 100, "description": ""}},
  "suggestions": []
}}
Resume: {text}"""
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "developer",
                "content": "You are a professional Resume Analyzer"
            },
            {
                "role": "user",
                "content": f"{prompt}"
            }
        ]
    )
    return response.output_text

def pdf_reader(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4069), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "resume" not in request.files:
        return"No Fil Uploaded"
    file = request.files["resume"]
    if file.filename == "":
        return "No Selected file"
    if not file.filename.endswith("pdf"):
        return "Only PDFs Files are allowed"
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    # Generate the unique hash for the file and saving it's address
    file_hash = get_file_hash(file_path)
    cache_path = os.path.join("cache", f"{file_hash}.json")

    if os.path.exists(cache_path):
        print("It exists in the caches")
        with open(cache_path, "r") as f:
            data = json.load(f)
    else:
        print("Using AI")
        pdf_text = pdf_reader(file_path)
        print(pdf_text)
        ai_response = analyze_resume(pdf_text)
        data = json.loads(ai_response)
        print(data)
        print(data["spelling"])
        with open(cache_path, "w") as f:
            json.dump(data, f)
    return render_template("index.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)
