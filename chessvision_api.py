import base64
import requests
import time
import random
import io
from config import MIN_RAND_TIME, MAX_RAND_TIME, API_TIMEOUT


def send_image_to_chessvision(image):
    """
    Send PIL Image to Chessvision API with random delay.

    Args:
        image: PIL Image object

    Returns:
        tuple: (fen, turn) or (None, None)
    """
    try:
        # Random delay before API call
        delay = random.uniform(MIN_RAND_TIME, MAX_RAND_TIME)
        print(f"⏳ Waiting {delay:.1f}s before API call...")
        time.sleep(delay)

        # Convert PIL Image to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        url = "http://app.chessvision.ai/predict"
        payload = {
            "board_orientation": "predict",
            "cropped": True,
            "current_player": "white",
            "image": f"data:image/png;base64,{b64_image}",
            "predict_turn": True
        }
        headers = {"Content-Type": "application/json"}

        print("🌐 Calling Chessvision API...")
        response = requests.post(url, json=payload, headers=headers, timeout=API_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            fen = data.get("result")
            turn = data.get("turn")
            print(f"✅ API Success - FEN: {fen[:20]}..." if fen else "❌ No FEN returned")
            return fen, turn
        else:
            print(f"❌ Chessvision API failed: {response.status_code}")
            return None, None

    except requests.exceptions.Timeout:
        print(f"⏰ API request timed out after {API_TIMEOUT}s")
        return None, None
    except Exception as e:
        print(f"❌ Error calling Chessvision API: {e}")
        return None, None