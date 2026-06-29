from flask import Flask, render_template, request
import requests
import base64
import time
import os

app = Flask(__name__)

# Tokens environment variables se read honge
HF_TOKENS = [
    t.strip() for t in [
        os.environ.get("HF_TOKEN_1", ""),
        os.environ.get("HF_TOKEN_2", "")
    ] if t.strip()
]

# Hugging Face Model URL (naya router endpoint)
API_URL = "https://router.huggingface.co/hf-inference/models/timbrooks/instruct-pix2pix"

current_token_index = 0

def get_next_token():
    global current_token_index
    token = HF_TOKENS[current_token_index]
    current_token_index = (current_token_index + 1) % len(HF_TOKENS)
    return token

def query_api(image_url, prompt):
    # Image ko URL se download karein
    try:
        img_response = requests.get(image_url, stream=True)
        img_response.raise_for_status()
        img_bytes = img_response.content
    except Exception as e:
        return None, f"Image download nahi hui: {str(e)}"

    # Image ko Base64 mein convert karein taake API ko bhej sakein
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    # API Payload
    payload = {
        "inputs": {
            "image": img_base64,
            "text": prompt
        }
    }

    headers = {}

    # API ko call lagayein (Retry logic ke sath)
    max_retries = 6
    for attempt in range(max_retries):
        token = get_next_token()
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)

            # Agar model load ho raha hai toh 503 aata hai, thori der ruk kar retry karein
            if response.status_code == 503:
                print(f"Model load ho raha hai... 5 second wait karein. (Attempt {attempt+1})")
                time.sleep(5)
                continue

            # Agar rate limit (429) ho toh dusra token try karein
            if response.status_code == 429:
                print(f"Token {token} rate limit par hai, dusra try kar rahe hain...")
                continue

            # Agar successful ho gaya
            if response.status_code == 200:
                # HF API direct image bytes return karti hai
                edited_img_bytes = response.content
                edited_img_b64 = base64.b64encode(edited_img_bytes).decode("utf-8")
                return edited_img_b64, None
            else:
                return None, f"API Error: {response.status_code} - {response.text}"

        except Exception as e:
            return None, f"Request fail hui: {str(e)}"

    return None, "Server busy hai ya tokens khatam ho gaye hain. Thori baad koshish karein."

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        image_url = request.form.get('image_url')
        prompt = request.form.get('prompt')

        if not image_url or not prompt:
            return render_template('index.html', error="Image URL aur Prompt dono zaroori hain.")

        # API ko call karein
        edited_img_b64, error = query_api(image_url, prompt)

        if error:
            return render_template('index.html', error=error, image_url=image_url, prompt=prompt)

        # Original aur Edited image dono webpage par bhejein
        return render_template('index.html', original_img_url=image_url, edited_img_b64=edited_img_b64, prompt=prompt)

    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
