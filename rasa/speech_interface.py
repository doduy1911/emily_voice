import speech_recognition as sr
import requests
import json
import logging
import time
import pygame
import threading

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL của Rasa REST API
RASA_API_URL = "http://localhost:5005/webhooks/rest/webhook"

# Khóa để đồng bộ hóa phát âm thanh và lắng nghe
audio_lock = threading.Lock()


def recognize_speech():
    """Nhận diện giọng nói và chuyển thành văn bản"""
    if audio_lock.locked():
        logger.info("Âm thanh đang phát, bỏ qua lắng nghe...")
        return None

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        logger.info("Đang lắng nghe... Nói gì đó (nhấn Ctrl+C để dừng)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            logger.info("Đang xử lý giọng nói...")
            text = recognizer.recognize_google(audio, language="vi-VN")
            logger.info(f"Đã nhận: {text}")
            return text
        except sr.WaitTimeoutError:
            logger.info("Không nhận được giọng nói trong thời gian chờ")
            return None
        except sr.UnknownValueError:
            logger.info("Không thể nhận diện giọng nói")
            return None
        except sr.RequestError as e:
            logger.error(f"Lỗi khi gọi API Google Speech: {str(e)}")
            return None


def send_to_rasa(text):
    """Gửi văn bản đến Rasa API và nhận phản hồi"""
    if not text:
        return "Lỗi: Không có văn bản đầu vào"
    try:
        payload = {"sender": "user", "message": text}
        response = requests.post(RASA_API_URL, json=payload, timeout=30)  # Tăng timeout lên 30s
        logger.info(f"Rasa response status: {response.status_code}, Response: {response.text}")
        if response.status_code == 200:
            response_data = response.json()
            if response_data and isinstance(response_data, list) and len(response_data) > 0:
                return response_data[0].get("text", "Không có phản hồi từ bot")
            else:
                logger.error(f"Rasa API returned empty response: {response.text}")
                return "Lỗi: Phản hồi từ bot rỗng"
        else:
            logger.error(f"Rasa API failed: {response.status_code} - {response.text}")
            return f"Lỗi: Mã trạng thái {response.status_code}"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Rasa API: {str(e)}")
        return "Lỗi khi xử lý yêu cầu"


def wait_for_audio_completion():
    """Chờ cho đến khi âm thanh phát xong"""
    if audio_lock.locked():
        logger.info("Đang chờ âm thanh phát xong...")
        while audio_lock.locked():
            time.sleep(0.1)
    time.sleep(1.0)  # Buffer 1 giây để tránh tiếng vang
    logger.info("Âm thanh đã phát xong, sẵn sàng lắng nghe")


def main():
    """Hàm chính để chạy giao diện giọng nói"""
    while True:
        try:
            # Chờ cho đến khi âm thanh hiện tại (nếu có) phát xong
            wait_for_audio_completion()

            # Nhận diện giọng nói
            text = recognize_speech()
            if text:
                print(f"Your input -> {text}")
                # Gửi văn bản đến Rasa và chờ phản hồi
                response = send_to_rasa(text)
                print(f"Bot response -> {response}")
                # Chờ âm thanh phát xong trước khi tiếp tục
                wait_for_audio_completion()
        except KeyboardInterrupt:
            logger.info("Stopping speech interface")
            break


if __name__ == "__main__":
    main()