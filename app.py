from flask import Flask, render_template, request, jsonify
import base64
import os
import uuid
import threading
from gradio_client import Client, handle_file

app = Flask(__name__)

HF_TOKEN = os.environ.get("HF_TOKEN_1", "").strip() or None

jobs = {}

def run_edit(job_id, image_url, prompt):
    try:
        client = Client("timbrooks/instruct-pix2pix", token=HF_TOKEN, verbose=False)
        result = client.predict(
            handle_file(image_url),
            prompt,
            20,
            "Randomize Seed",
            1371,
            "Fix CFG",
            7.5,
            2.5,
            api_name="/generate"
        )
        edited_path = result[3]
        with open(edited_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        jobs[job_id] = {"done": True, "image": img_b64}
    except Exception as e:
        jobs[job_id] = {"done": True, "error": str(e)}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    image_url = request.form.get("image_url", "").strip()
    prompt = request.form.get("prompt", "").strip()

    if not image_url or not prompt:
        return jsonify({"error": "Image URL aur Prompt dono zaroori hain."}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"done": False}
    threading.Thread(target=run_edit, args=(job_id, image_url, prompt), daemon=True).start()
    return jsonify({"job_id": job_id})

@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job nahi mila."}), 404
    return jsonify(job)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
