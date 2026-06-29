from flask import Flask, render_template, request
import requests
import base64
import time
import os

app = Flask(__name__)

HORDE_API_URL = "https://stablehorde.net/api/v2"
HORDE_API_KEY = "0000000000"

def query_api(image_url, prompt):
    try:
        img_response = requests.get(image_url, timeout=15)
        img_response.raise_for_status()
        img_base64 = base64.b64encode(img_response.content).decode("utf-8")
    except Exception as e:
        return None, f"Image download nahi hui: {str(e)}"

    payload = {
        "prompt": prompt,
        "params": {
            "sampler_name": "k_euler",
            "cfg_scale": 7.5,
            "denoising_strength": 0.7,
            "height": 512,
            "width": 512,
            "steps": 25,
            "n": 1
        },
        "source_image": img_base64,
        "source_processing": "img2img",
        "r2": True,
        "shared": False
    }

    headers = {
        "apikey": HORDE_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        submit_resp = requests.post(
            f"{HORDE_API_URL}/generate/async",
            json=payload,
            headers=headers,
            timeout=30
        )
        if submit_resp.status_code != 202:
            return None, f"Job submit nahi hua: {submit_resp.status_code} - {submit_resp.text}"

        job_id = submit_resp.json().get("id")
        if not job_id:
            return None, "Job ID nahi mila."

    except Exception as e:
        return None, f"Submit request fail: {str(e)}"

    for attempt in range(30):
        time.sleep(6)
        try:
            status_resp = requests.get(
                f"{HORDE_API_URL}/generate/status/{job_id}",
                headers=headers,
                timeout=15
            )
            data = status_resp.json()

            if data.get("done"):
                generations = data.get("generations", [])
                if not generations:
                    return None, "Koi result nahi aaya."

                img_url = generations[0].get("img")
                if not img_url:
                    return None, "Image URL nahi mila result mein."

                img_resp = requests.get(img_url, timeout=15)
                img_resp.raise_for_status()
                img_b64 = base64.b64encode(img_resp.content).decode("utf-8")
                return img_b64, None

            wait_time = data.get("wait_secs", "?")
            print(f"Attempt {attempt+1}: abhi bhi process ho raha hai... ({wait_time}s bachi)")

        except Exception as e:
            print(f"Status check error: {str(e)}")
            continue

    return None, "Timeout ho gaya — server busy hai. Dobara koshish karein."

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        image_url = request.form.get('image_url', '').strip()
        prompt = request.form.get('prompt', '').strip()

        if not image_url or not prompt:
            return render_template('index.html', error="Image URL aur Prompt dono zaroori hain.")

        edited_img_b64, error = query_api(image_url, prompt)

        if error:
            return render_template('index.html', error=error, image_url=image_url, prompt=prompt)

        return render_template('index.html',
                               original_img_url=image_url,
                               edited_img_b64=edited_img_b64,
                               prompt=prompt)

    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
