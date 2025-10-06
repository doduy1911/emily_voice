
import requests
import os
import hashlib
import logging
import time

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VBEE_API_URL = "https://vbee.vn/api/v1/tts"
VBEE_API_TOKEN = os.getenv("VBEE_API_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NTMxNzExMTB9.I4ZpO9Y2cHBA9XIE9P7k7rYzS7aTD3ZA3bjWUIyEPEw")
VBEE_APP_ID = "a9cd5352-2329-4350-b689-d85574e988ba"
CALLBACK_URL = "https://mydomain/callback"

# CACHE_DIR = "/rasa/cache"
CACHE_DIR = "/home/bytehome/emily_voice/rasa/cache"

# Danh sách các câu trả lời phổ biến từ domain.yml
RESPONSE_TEXTS = [
    "Xin chào! Tôi có thể giúp bạn bật/tắt đèn, chỉnh sáng, đổi màu, hoặc điều khiển quạt trần.",
    "Bạn muốn điều khiển thiết bị nào? (ví dụ: đèn trần, quạt trần)",
    "Vui lòng cung cấp độ sáng từ 0-100",
    "Thiết bị đang không cắm nguồn điện, hoặc lỗi, hãy kiểm tra lại thiết bị",
    "Vui lòng cung cấp màu (ví dụ: vàng, đỏ hoặc #FF0000)",
    "Vui lòng cung cấp tốc độ quạt từ 1 đến 6",
    "Vui lòng cung cấp thời gian hẹn giờ (ví dụ: 2 tiếng)",
    "Goodbye",
    "Lỗi đăng nhập hệ thống",
    "Lỗi khi tìm nhà",
    "Không tìm thấy phòng",
    "Có 3 phòng: phòng khách, phòng bếp, phòng ngủ",
    "Có 5 thiết bị trong phòng khách: quạt trần, điều hòa, Đèn trần to, công tắc 4 hạt, đèn trần",
    "Đã đổi màu đèn trần thành vàng",
    "Đã đổi màu đèn trần thành đỏ",
    "Đã đổi màu đèn trần thành xanh",
    "Đã đổi màu đèn trần thành tím",
    "Đã chỉnh tốc độ quạt trần thành mức 3",
    "Đã chỉnh tốc độ quạt trần thành mức 2",
    "Bạn tên là gì?",
    "Vui lòng cho tôi biết tên của bạn.",
    "Xin chào Khánh, Tôi là trợ lý ảo, tên tôi là Emily, tôi ở đây là để giúp đỡ bạn, tôi có thể hỗ trợ điều khiển các thiết bị điện tử, tôi có thể tìm kiếm thông tin và kể tên các món ăn, đồ uống đang có tại cửa hàng, giá. Ngoài ra tôi có thể làm sách nói, tư vấn trò chuyện như một người bạn những vấn đề tế nhị, dẫn đường cho bạn, và tôi cũng có thể mang đồ ăn giúp bạn nữa. Vậy tôi có thể giúp gì được cho bạn? Hãy cứ nói nhé",
    "Xin chào Long, Tôi là trợ lý ảo, tên tôi là Emily, tôi ở đây là để giúp đỡ bạn, tôi có thể hỗ trợ điều khiển các thiết bị điện tử, tôi có thể tìm kiếm thông tin và kể tên các món ăn, đồ uống đang có tại cửa hàng, giá. Ngoài ra tôi có thể làm sách nói, tư vấn trò chuyện như một người bạn những vấn đề tế nhị, dẫn đường cho bạn, và tôi cũng có thể mang đồ ăn giúp bạn nữa. Vậy tôi có thể giúp gì được cho bạn? Hãy cứ nói nhé",
    "Xin chào Trang, Tôi là trợ lý ảo, tên tôi là Emily, tôi ở đây là để giúp đỡ bạn, tôi có thể hỗ trợ điều khiển các thiết bị điện tử, tôi có thể tìm kiếm thông tin và kể tên các món ăn, đồ uống đang có tại cửa hàng, giá. Ngoài ra tôi có thể làm sách nói, tư vấn trò chuyện như một người bạn những vấn đề tế nhị, dẫn đường cho bạn, và tôi cũng có thể mang đồ ăn giúp bạn nữa. Vậy tôi có thể giúp gì được cho bạn? Hãy cứ nói nhé",
    "Xin chào Ngọc Anh, Tôi là trợ lý ảo, tên tôi là Emily, tôi ở đây là để giúp đỡ bạn, tôi có thể hỗ trợ điều khiển các thiết bị điện tử, tôi có thể tìm kiếm thông tin và kể tên các món ăn, đồ uống đang có tại cửa hàng, giá. Ngoài ra tôi có thể làm sách nói, tư vấn trò chuyện như một người bạn những vấn đề tế nhị, dẫn đường cho bạn, và tôi cũng có thể mang đồ ăn giúp bạn nữa. Vậy tôi có thể giúp gì được cho bạn? Hãy cứ nói nhé"
]

def get_cache_file_path(text: str) -> str:
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{text_hash}.mp3")

def generate_audio(text: str) -> bool:
    cache_file = get_cache_file_path(text)
    if os.path.exists(cache_file):
        logger.info(f"Audio for '{text}' already exists in cache")
        return True

    try:
        logger.info(f"Generating audio for: {text}")
        payload = {
            "app_id": VBEE_APP_ID,
            "callbackUrl": CALLBACK_URL,
            "input_text": text,
            "voice_code": "hn_female_hermer_stor_48k-fhg",
            "audio_type": "mp3",
            "bitrate": 128,
            "speed_rate": "1.0"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VBEE_API_TOKEN}"
        }
        response = requests.post(VBEE_API_URL, json=payload, headers=headers, timeout=15)
        if response.status_code == 200 and response.json().get("status") == 1:
            request_id = response.json()["result"]["request_id"]
            max_attempts = 15
            attempt = 0
            while attempt < max_attempts:
                status_response = requests.get(f"{VBEE_API_URL}/{request_id}", headers=headers, timeout=15)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get("status") == 1 and status_data["result"]["status"] in ["SUCCESS", "DONE"]:
                        audio_url = status_data["result"].get("audio_link") or status_data["result"].get("audio_url")
                        audio_response = requests.get(audio_url, timeout=15)
                        if audio_response.status_code == 200:
                            with open(cache_file, 'wb') as f:
                                f.write(audio_response.content)
                            logger.info(f"Saved audio to cache: {cache_file}")
                            return True
                        else:
                            logger.error(f"Failed to download audio: {audio_response.status_code}")
                            return False
                    elif status_data["result"]["status"] == "IN_PROGRESS":
                        time.sleep(1)
                        attempt += 1
                    else:
                        logger.error(f"TTS failed: {status_data.get('result')}")
                        return False
                else:
                    logger.error(f"Status check failed: {status_response.status_code}")
                    return False
            logger.error("Max attempts reached")
            return False
        else:
            logger.error(f"TTS API failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        return False

if __name__ == "__main__":
    for text in RESPONSE_TEXTS:
        generate_audio(text)
