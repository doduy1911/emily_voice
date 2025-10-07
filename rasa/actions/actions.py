from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
import logging
import os
import socket
import hashlib
import time
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from google import genai


from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Thiết lập logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# file_handler = logging.FileHandler("f"{BASE_DIR}/rasa_debug.log")
file_handler = logging.FileHandler(f"{BASE_DIR}/rasa_debug.log")

file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())
load_dotenv()  
# print("[DEBUG] VBEE_API_URL =", os.getenv("USERADMIN"))
# print("[DEBUG] VBEE_API_URL =", os.getenv("PASSWORD"))
# print("[DEBUG] VBEE_API_URL =", os.getenv("VBEE_APP_ID"))
# print("[DEBUG] VBEE_API_URL =", os.getenv("VBEE_API_TOKEN"))





BACKEND_URL = os.getenv("BACKEND_URL")
VBEE_API_URL = os.getenv("VBEE_API_URL")
VBEE_API_TOKEN = os.getenv("VBEE_API_TOKEN")
VBEE_APP_ID = os.getenv("VBEE_APP_ID")
CALLBACK_URL = os.getenv("CALLBACK_URL")
USERNAME = os.getenv("USERADMIN")
PASSWORD = os.getenv("PASSWORD")
CACHE_DIR = f"{BASE_DIR}/rasa/cache"
AUDIO_SERVER_PORT = 8486
AUDIO_BASE_URL = f""
API_GEMINI = "AIzaSyA_3VNqz-NyWbxZZgh1fB3lZMQy8pnktZU"

# Khởi động server HTTP để phục vụ file âm thanh từ cache
class CacheFileHandler(SimpleHTTPRequestHandler):
    def do_HEAD(self):
        logger.info(f"Received HEAD request for path: {self.path}")
        if self.path.startswith("/audio/"):
            file_name = self.path[len("/audio/"):]
        else:
            file_name = self.path.lstrip("/")
        logger.info(f"Stripped file name: {file_name}")

        if not file_name or not file_name.endswith(".mp3"):
            logger.error(f"Invalid file name: {file_name}")
            self.send_error(404, "File not found")
            return
        file_path = os.path.abspath(os.path.join(CACHE_DIR, file_name))
        logger.info(f"Resolved file path: {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            self.send_error(404, "File not found")
            return
        if not os.access(file_path, os.R_OK):
            logger.error(f"File not readable: {file_path}")
            self.send_error(403, "File not readable")
            return
        logger.info(f"Preparing to serve HEAD for file: {file_path}")
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", os.path.getsize(file_path))
        self.end_headers()

    def do_GET(self):
        logger.info(f"Received GET request for path: {self.path}")
        if self.path.startswith("/audio/"):
            file_name = self.path[len("/audio/"):]
        else:
            file_name = self.path.lstrip("/")
        logger.info(f"Stripped file name: {file_name}")

        if not file_name or not file_name.endswith(".mp3"):
            logger.error(f"Invalid file name: {file_name}")
            self.send_error(404, "File not found")
            return

        file_path = os.path.abspath(os.path.join(CACHE_DIR, file_name))
        logger.info(f"Resolved file path: {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            self.send_error(404, "File not found")
            return
        if not os.access(file_path, os.R_OK):
            logger.error(f"File not readable: {file_path}")
            self.send_error(403, "File not readable")
            return
        logger.info(f"Serving file: {file_path}")
        try:
            return SimpleHTTPRequestHandler.do_GET(self)
        except Exception as e:
            logger.error(f"Error serving file: {str(e)}")
            self.send_error(500, f"Error serving file: {str(e)}")

def start_audio_server():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    os.chdir(CACHE_DIR)
    handler = SimpleHTTPRequestHandler
    server = ThreadingHTTPServer(("0.0.0.0", AUDIO_SERVER_PORT), handler)
    logger.info(f"Serving {CACHE_DIR} at port {AUDIO_SERVER_PORT}")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://{os.popen('hostname -I').read().strip().split()[0]}:{AUDIO_SERVER_PORT}"
        
def ask_gemini(prompt: str) -> str:
    if not API_GEMINI:
        return "Chưa cấu hình khóa API cho Gemini."

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_GEMINI}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": f"Trả lời ngắn gọn, chỉ 1–2 câu: {prompt}"
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 512,   # đủ lớn để model không nghẽn
            "temperature": 0.4        # hạ nhiệt, cho câu gọn gàng hơn
        }
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        data = res.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text")
        )
        return text or "Gemini không trả về nội dung hợp lệ."
    except Exception as e:
        return f"Lỗi khi gọi Gemini: {e}"






# Chạy server HTTP khi khởi động
try:
    start_audio_server()
except Exception as e:
    logger.error(f"Failed to start audio server: {str(e)}")
    raise

COLOR_MAP = {
    "xanh": "#00FF00",
    "đỏ": "#FF0000",
    "tím": "#D900FF",
    "vàng": "#F6FF00",
    "trắng": "#FFFFFF",
    "cam": "#FFD000",
    "xanh da trời": "#0015FF",
    "xanh lá cây": "#00FF03"
}

class DeviceController:
    """Lớp chứa các hàm chung cho điều khiển thiết bị và giọng nói"""

    @staticmethod
    def _get_token(dispatcher: CollectingDispatcher) -> str:
        try:
            logger.info("Attempting to login...")
            response = requests.post(
                f"{BACKEND_URL}/api/auth/login",
                json={"username": USERNAME, "password": PASSWORD},
                timeout=15
            )
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    logger.info("Login successful")
                    return token
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                dispatcher.utter_message(text="Lỗi đăng nhập hệ thống")
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                dispatcher.utter_message(text="Lỗi đăng nhập hệ thống")
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            dispatcher.utter_message(text="Lỗi kết nối hệ thống")
        return None

    @staticmethod
    def _get_house(dispatcher: CollectingDispatcher, token: str) -> str:
        try:
            logger.info("Fetching house info...")
            response = requests.get(
                f"{BACKEND_URL}/api/tenant/assets?pageSize=100&page=0&textSearch=HOUSE",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            if response.status_code == 200:
                houses = response.json().get("data", [])
                if houses:
                    house_id = houses[0].get("id", {}).get("id")
                    logger.info(f"Found house: {house_id}")
                    return house_id
                logger.error("No house found")
                dispatcher.utter_message(text="Không tìm thấy nhà")
            else:
                logger.error(f"House fetch failed: {response.status_code} - {response.text}")
                dispatcher.utter_message(text="Lỗi khi tìm nhà")
        except Exception as e:
            logger.error(f"House fetch error: {str(e)}")
            dispatcher.utter_message(text="Lỗi khi tìm nhà")
        return None

    @staticmethod
    def _get_room(dispatcher: CollectingDispatcher, token: str, house_id: str, room_name: str = "phòng khách") -> str:
        try:
            logger.info(f"Fetching room ID for room {room_name} in house {house_id}...")
            response = requests.get(
                f"{BACKEND_URL}/api/relations/info?fromId={house_id}&fromType=ASSET",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            if response.status_code == 200:
                rooms = response.json()
                logger.info(f"Raw rooms response: {rooms}")
                for room in rooms:
                    current_room_name = room.get("toName") or room.get("to", {}).get("toName")
                    if current_room_name:
                        normalized_room_name = current_room_name.lower().replace(" ", "")
                        normalized_input_name = room_name.lower().replace(" ", "")
                        if normalized_room_name == normalized_input_name and room.get("to", {}).get("entityType") == "ASSET":
                            room_id = room.get("to", {}).get("id")
                            logger.info(f"Found room ID: {room_id} for room {room_name}")
                            return room_id
                logger.error(f"No room found with name {room_name}")
                dispatcher.utter_message(text=f"Không tìm thấy phòng {room_name}")
            else:
                logger.error(f"Room fetch failed: {response.status_code} - {response.text}")
                dispatcher.utter_message(text=f"Không tìm thấy phòng {room_name}")
        except Exception as e:
            logger.error(f"Room ID fetch error: {str(e)}")
            dispatcher.utter_message(text=f"Không tìm thấy phòng {room_name}")
        return None

    @staticmethod
    def _get_rooms(dispatcher: CollectingDispatcher, token: str, house_id: str) -> List[str]:
        try:
            logger.info(f"Fetching rooms for house {house_id}...")
            response = requests.get(
                f"{BACKEND_URL}/api/relations/info?fromId={house_id}&fromType=ASSET",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            if response.status_code == 200:
                rooms = response.json()
                room_list = [
                    room.get("toName") or room.get("to", {}).get("toName", "Unknown")
                    for room in rooms
                    if (room.get("toName") or room.get("to", {}).get("toName")) and room.get("to", {}).get("entityType") == "ASSET"
                ]
                logger.info(f"Found rooms: {room_list}")
                return room_list
            logger.error(f"Room fetch failed: {response.status_code} - {response.text}")
            dispatcher.utter_message(text="Lỗi khi tìm nhà")
            return []
        except Exception as e:
            logger.error(f"Room fetch error: {str(e)}")
            dispatcher.utter_message(text="Lỗi khi tìm nhà")
            return []

    @staticmethod
    def _get_device_id(dispatcher: CollectingDispatcher, token: str, room_id: str, device_name: str) -> str:
        if not device_name:
            logger.error("Device name is None")
            dispatcher.utter_message(text="Vui lòng chỉ định thiết bị cần điều khiển (ví dụ: đèn trần nhỏ, quạt trần)")
            return None
        try:
            logger.info(f"Fetching device ID for device {device_name} in room {room_id}...")
            response = requests.get(
                f"{BACKEND_URL}/api/relations/info?fromId={room_id}&fromType=ASSET",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            if response.status_code == 200:
                devices = response.json()
                logger.info(f"Raw devices response: {devices}")
                for device in devices:
                    current_device_name = device.get("toName") or device.get("to", {}).get("toName")
                    if current_device_name:
                        normalized_device_name = current_device_name.lower().replace(" ", "")
                        normalized_input_name = device_name.lower().replace(" ", "")
                        if normalized_device_name == normalized_input_name and device.get("to", {}).get("entityType") == "DEVICE":
                            device_id = device.get("to", {}).get("id")
                            logger.info(f"Found device ID: {device_id} for device {device_name}")
                            return device_id
                logger.error(f"No device found with name {device_name}")
                dispatcher.utter_message(text="Vui lòng chỉ định thiết bị cần điều khiển (ví dụ: đèn trần nhỏ, quạt trần)")
            else:
                logger.error(f"Device fetch failed: {response.status_code} - {response.text}")
                dispatcher.utter_message(text="Vui lòng chỉ định thiết bị cần điều khiển (ví dụ: đèn trần nhỏ, quạt trần)")
        except Exception as e:
            logger.error(f"Device ID fetch error: {str(e)}")
            dispatcher.utter_message(text="Vui lòng chỉ định thiết bị cần điều khiển (ví dụ: đèn trần nhỏ, quạt trần)")
        return None

    @staticmethod
    def _get_devices_in_room(dispatcher: CollectingDispatcher, token: str, room_id: str) -> List[str]:
        try:
            logger.info(f"Fetching devices for room {room_id}...")
            response = requests.get(
                f"{BACKEND_URL}/api/relations/info?fromId={room_id}&fromType=ASSET",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            if response.status_code == 200:
                devices = response.json()
                device_list = [
                    device.get("toName") or device.get("to", {}).get("toName", "Unknown")
                    for device in devices
                    if (device.get("toName") or device.get("to", {}).get("toName")) and device.get("to", {}).get("entityType") == "DEVICE"
                ]
                logger.info(f"Found devices: {device_list}")
                return device_list
            logger.error(f"Device fetch failed: {response.status_code} - {response.text}")
            dispatcher.utter_message(text="Lỗi khi tìm thiết bị")
            return []
        except Exception as e:
            logger.error(f"Device fetch error: {str(e)}")
            dispatcher.utter_message(text="Lỗi khi tìm thiết bị")
            return []

    @staticmethod
    def _get_cache_file_path(text: str) -> str:
        """Tạo tên file cache từ văn bản đầu vào"""
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return os.path.join(CACHE_DIR, f"{text_hash}.mp3")

    @staticmethod
    def text_to_speech(dispatcher: CollectingDispatcher, text: str) -> str:
        """Chuyển văn bản thành giọng nói, lưu vào cache và trả về URL"""
        logger.info(f"[TTS] AUDIO_BASE_URL = {AUDIO_BASE_URL}")
        logger.info(f"[TTS] Input text = {text}")

        if not text:
            logger.error("No text provided for TTS")
            return None

        cache_file = DeviceController._get_cache_file_path(text)
        cache_filename = os.path.basename(cache_file)
        # audio_url = f"{AUDIO_BASE_URL}/{cache_filename}"
        audio_url = f"{cache_filename}"

        logger.info(f"[TTS] Cache file: {cache_file}")
        logger.info(f"[TTS] Audio URL to return: {audio_url}")

        if os.path.exists(cache_file):
            logger.info(f"Returning cached audio URL for text: {text}")
            return audio_url

        try:
            logger.info(f"Calling Vbee TTS API with text: {text}")
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
            logger.info(f"[TTS] Vbee POST status: {response.status_code}")
            logger.info(f"[TTS] Vbee POST response: {response.text[:500]}")

            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == 1:
                    request_id = response_data["result"]["request_id"]
                    logger.info(f"[TTS] Got request_id: {request_id}")
                    max_attempts = 20
                    attempt = 0
                    logger.info(f"[TTS] Start polling VBEE for status...")

                    while attempt < max_attempts:
                        time.sleep(1)
                        status_response = requests.get(
                            f"{VBEE_API_URL}/{request_id}",
                            headers=headers,
                            timeout=15
                        )
                        logger.info(f"[TTS] Poll attempt {attempt + 1}/{max_attempts}: {status_response.status_code}")

                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            result = status_data.get("result", {})
                            state = result.get("status")

                            if state in ["SUCCESS", "DONE"]:
                                audio_url_vbee = result.get("audio_link") or result.get("audio_url")
                                if not audio_url_vbee:
                                    logger.error(f"[TTS] No audio URL found in result: {result}")
                                    return None

                                # Tải file audio về cache
                                audio_response = requests.get(audio_url_vbee, timeout=15)
                                if audio_response.status_code == 200:
                                    with open(cache_file, 'wb') as f:
                                        f.write(audio_response.content)
                                    logger.info(f"[TTS] Saved cached audio: {cache_file}")
                                    return audio_url
                                else:
                                    logger.error(f"[TTS] Failed to download audio ({audio_response.status_code})")
                                    return None

                            elif state == "IN_PROGRESS":
                                attempt += 1
                                continue
                            else:
                                logger.error(f"[TTS] Unexpected VBEE state: {state}")
                                return None
                        else:
                            logger.error(f"[TTS] Failed to poll VBEE status ({status_response.status_code})")
                            return None

                    logger.error("[TTS] Timeout: max attempts reached without success")
                    return None

                else:
                    logger.error(f"[TTS] API returned error status: {response_data}")
                    return None
            else:
                logger.error(f"[TTS] Vbee API failed with status: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"[TTS] Exception: {e}")
            import traceback; traceback.print_exc()
            dispatcher.utter_message(text="Lỗi khi chuyển văn bản thành giọng nói")
            return None

    @classmethod
    def control_device(cls, dispatcher: CollectingDispatcher, tracker: Tracker, action_type: str, payload: Dict, success_response: str, error_response: str, action_verb: str = None) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device")
        token = tracker.get_slot("token")
        house = tracker.get_slot("house")
        room = tracker.get_slot("room") or "phòng khách"
        device_id = tracker.get_slot("device_id")

        if not device:
            response_text = "Vui lòng chỉ định thiết bị cần điều khiển (ví dụ: đèn trần nhỏ, quạt trần)"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return [SlotSet("device", None)]

        if not token:
            token = cls._get_token(dispatcher)
            if not token:
                response_text = "Lỗi đăng nhập hệ thống"
                audio_url = cls.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return [SlotSet("device", None)]

        if not house:
            house = cls._get_house(dispatcher, token)
            if not house:
                response_text = "Lỗi khi tìm nhà"
                audio_url = cls.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return [SlotSet("device", None)]

        room_id = cls._get_room(dispatcher, token, house, room_name=room)
        if not room_id:
            response_text = f"Không tìm thấy phòng {room}"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return [SlotSet("device", None), SlotSet("house", None), SlotSet("room", None)]

        if not device_id:
            device_id = cls._get_device_id(dispatcher, token, room_id, device)
            if not device_id:
                response_text = f"Không tìm thấy thiết bị {device}"
                audio_url = cls.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return [SlotSet("device", None), SlotSet("house", None), SlotSet("room", None)]

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{BACKEND_URL}/api/rpc/oneway/{device_id}",
                json=payload,
                headers=headers,
                timeout=15
            )
            format_params = {"action": action_verb or "thực hiện", "device_name": device}
            format_params.update({k: v for k, v in tracker.slots.items() if k not in ["device", "action"]})
            if response.status_code == 200:
                response_text = success_response.format(**format_params)
                audio_url = cls.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            else:
                if response.status_code == 504:
                    response_text = "Thiết bị đang không cắm nguồn điện, hoặc lỗi, hãy kiểm tra lại thiết bị"
                else:
                    response_text = error_response.format(device_name=device, error_code=response.status_code)
                audio_url = cls.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})

            reset_slots = [SlotSet("device", None)]
            if action_type == "brightness":
                reset_slots.append(SlotSet("brightness", None))
            elif action_type == "fan_speed":
                reset_slots.append(SlotSet("fan_speed", None))
            elif action_type == "tv_channel":
                reset_slots.append(SlotSet("tv_channel", None))
            elif action_type == "tv_volume":
                reset_slots.append(SlotSet("tv_volume", None))
            elif action_type == "ac_temperature":
                reset_slots.append(SlotSet("ac_temperature", None))
            elif action_type == "ac_mode":
                reset_slots.append(SlotSet("ac_mode", None))
            elif action_type == "timer":
                reset_slots.append(SlotSet("timer", None))
            elif action_type == "color":
                reset_slots.append(SlotSet("color", None))

            return reset_slots + [SlotSet("house", None), SlotSet("room", None), SlotSet("device_id", None), SlotSet("token", token)]
        except Exception as e:
            logger.error(f"Control error: {str(e)}")
            response_text = error_response.format(device_name=device, error_code="unknown")
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return [SlotSet("device", None), SlotSet("house", None), SlotSet("room", None), SlotSet("device_id", None), SlotSet("token", None)]

    @classmethod
    def check_rooms(cls, dispatcher: CollectingDispatcher, tracker: Tracker) -> List[Dict[Text, Any]]:
        token = tracker.get_slot("token") or cls._get_token(dispatcher)
        if not token:
            response_text = "Lỗi đăng nhập hệ thống"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        house_id = tracker.get_slot("house") or cls._get_house(dispatcher, token)
        if not house_id:
            response_text = "Lỗi khi tìm nhà"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        rooms = cls._get_rooms(dispatcher, token, house_id)
        if rooms:
            room_list = ", ".join(rooms)
            response_text = f"Có {len(rooms)} phòng: {room_list}"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        else:
            response_text = "Không tìm thấy phòng nào"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return [SlotSet("token", None), SlotSet("house", None)]

    @classmethod
    def check_devices_in_room(cls, dispatcher: CollectingDispatcher, tracker: Tracker) -> List[Dict[Text, Any]]:
        room_name = tracker.get_slot("room") or "phòng khách"
        token = tracker.get_slot("token") or cls._get_token(dispatcher)
        if not token:
            response_text = "Lỗi đăng nhập hệ thống"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        house_id = tracker.get_slot("house") or cls._get_house(dispatcher, token)
        if not house_id:
            response_text = "Lỗi khi tìm nhà"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        room_id = cls._get_room(dispatcher, token, house_id, room_name=room_name)
        if not room_id:
            response_text = f"Không tìm thấy phòng {room_name}"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        devices = cls._get_devices_in_room(dispatcher, token, room_id)
        if devices:
            device_list = ", ".join(devices)
            response_text = f"Có {len(devices)} thiết bị trong {room_name} là: {device_list}, bạn có cần hỗ trợ thêm không ?"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        else:
            response_text = f"Không tìm thấy thiết bị trong {room_name}, bạn có cần hỗ trợ thêm không ?"
            audio_url = cls.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return [SlotSet("token", None), SlotSet("house", None), SlotSet("room", None)]

class ActionGreet(Action):
    def name(self) -> Text:
        return "action_greet"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        response_text = "Xin chào, tôi là Emily, tôi rất vui được làm quen và hỗ trợ bạn"
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return []

class ActionAskCapabilities(Action):
    def name(self) -> Text:
        return "action_ask_capabilities"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        response_text = "Tôi có thể, trước hết tôi có thể xin tên bạn được không ?"
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return []

class ActionProvideUserName(Action):
    def name(self) -> Text:
        return "action_provide_user_name"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_name = tracker.get_slot("user_name")
        if not user_name:
            response_text = "Vui lòng cho tôi biết tên của bạn."
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        response_text = f"Xin chào {user_name}, tôi ở đây là để giúp đỡ bạn, tôi có thể hỗ trợ điều khiển các thiết bị điện tử, tôi có thể tìm kiếm thông tin tại cửa hàng. Ngoài ra tôi có thể làm sách nói, tư vấn trò chuyện với bạn, dẫn đường hoặc vận chuyển đồ đạc cho bạn. Vậy tôi có thể giúp gì được cho bạn? Hãy cứ nói nhé"
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return [SlotSet("user_name", user_name)]

class ActionCheckRooms(Action):
    def name(self) -> Text:
        return "action_check_rooms"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return DeviceController.check_rooms(dispatcher, tracker)

class ActionCheckDevicesInRoom(Action):
    def name(self) -> Text:
        return "action_check_devices_in_room"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return DeviceController.check_devices_in_room(dispatcher, tracker)

class ActionTurnOn(Action):
    def name(self) -> Text:
        return "action_turn_on"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "unknown"
        if device.lower() == "tv":
            payload = {"method": "selectBrand", "params": "Samsung"}
            DeviceController.control_device(dispatcher, tracker, "select_brand", payload, "Đã chọn hãng TV Samsung", "Lỗi khi chọn hãng TV {device_name} (mã lỗi: {error_code})")
        return DeviceController.control_device(
            dispatcher, tracker, "power", {"method": "relay1", "params": True},
            "Đã bật {device_name}, bạn có cần hỗ trợ thêm không ?", "Lỗi khi bật {device_name} (mã lỗi: {error_code})"
        )

class ActionTurnOff(Action):
    def name(self) -> Text:
        return "action_turn_off"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return DeviceController.control_device(
            dispatcher, tracker, "power", {"method": "relay1", "params": False},
            "Đã tắt {device_name}, bạn có cần hỗ trợ thêm không ?", "Lỗi khi tắt {device_name} (mã lỗi: {error_code})"
        )

class ActionSetBrightness(Action):
    def name(self) -> Text:
        return "action_set_brightness"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device")
        brightness = tracker.get_slot("brightness")
        latest_message = tracker.latest_message.get('text', '').lower()

        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: đèn trần nhỏ, đèn led)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not brightness:
            response_text = "Vui lòng cung cấp độ sáng từ 0-100"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        try:
            brightness_value = int(brightness.replace("%", ""))
            if not 0 <= brightness_value <= 100:
                response_text = "Độ sáng phải từ 0 đến 100"
                audio_url = DeviceController.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return []
        except ValueError:
            response_text = "Độ sáng phải là số (ví dụ: 50)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        action_verb = "tăng" if "tăng" in latest_message else "giảm" if "giảm" in latest_message else "chỉnh"
        return DeviceController.control_device(
            dispatcher, tracker, "brightness", {"method": "brightness", "params": brightness_value},
            "Đã {action} độ sáng {device_name} còn {brightness}, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi chỉnh độ sáng {device_name} (mã lỗi: {error_code})", action_verb
        )

class ActionSetFanSpeed(Action):
    def name(self) -> Text:
        return "action_set_fan_speed"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "quạt trần"
        fan_speed = tracker.get_slot("fan_speed")
        latest_message = tracker.latest_message.get('text', '').lower()

        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: quạt trần)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not fan_speed:
            response_text = "Vui lòng cung cấp tốc độ quạt từ 1 đến 6"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        try:
            speed_value = int(fan_speed)
            if not 1 <= speed_value <= 6:
                response_text = "Tốc độ quạt phải từ 1 đến 6"
                audio_url = DeviceController.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return []
        except ValueError:
            response_text = "Tốc độ quạt phải là số (ví dụ: 3)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        action_verb = "tăng" if "tăng" in latest_message else "giảm" if "giảm" in latest_message else "chỉnh"
        return DeviceController.control_device(
            dispatcher, tracker, "fan_speed", {"method": "fanSpeed", "params": speed_value},
            "Đã {action} tốc độ quạt {device_name} về số {fan_speed}, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi chỉnh tốc độ {device_name} (mã lỗi: {error_code})", action_verb
        )

class ActionChangeTVChannel(Action):
    def name(self) -> Text:
        return "action_change_tv_channel"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "TV"
        tv_channel = tracker.get_slot("tv_channel")

        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: TV)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not tv_channel:
            response_text = "Vui lòng cung cấp số kênh từ 1 đến 100"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        try:
            channel_value = int(tv_channel)
            if not 1 <= channel_value <= 100:
                response_text = "Kênh TV phải từ 1 đến 100"
                audio_url = DeviceController.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return []
        except ValueError:
            response_text = "Số kênh phải là số (ví dụ: 10)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        DeviceController.control_device(dispatcher, tracker, "select_brand", {"method": "selectBrand", "params": "Samsung"},
                                        "Đã chọn hãng TV Samsung", "Lỗi khi chọn hãng TV {device_name} (mã lỗi: {error_code})")
        return DeviceController.control_device(
            dispatcher, tracker, "tv_channel", {"method": "tvChannel", "params": channel_value},
            "Đã chuyển kênh {tv_channel}, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi chuyển kênh {device_name} (mã lỗi: {error_code})"
        )

class ActionAdjustTVVolume(Action):
    def name(self) -> Text:
        return "action_adjust_tv_volume"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "TV"
        tv_volume = tracker.get_slot("tv_volume")
        latest_message = tracker.latest_message.get('text', '').lower()

        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: TV)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not tv_volume:
            response_text = "Bạn muốn tăng/giảm âm lượng là bao nhiêu?"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        try:
            volume_value = int(tv_volume)
            if not 0 <= volume_value <= 100:
                response_text = "Âm lượng TV phải từ 0 đến 100"
                audio_url = DeviceController.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return []
        except ValueError:
            response_text = "Âm lượng phải là số (ví dụ: 50)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        action_verb = "tăng" if "tăng" in latest_message else "giảm" if "giảm" in latest_message else "chỉnh"
        payload = {"method": "volume", "params": "volup" if action_verb == "tăng" else "voldown"}
        return DeviceController.control_device(
            dispatcher, tracker, "tv_volume", payload,
            "Đã {action} âm lượng TV sang {tv_volume}, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi chỉnh âm lượng {device_name} (mã lỗi: {error_code})", action_verb
        )

class ActionSetACTemperature(Action):
    def name(self) -> Text:
        return "action_set_ac_temperature"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "điều hòa"
        ac_temperature = tracker.get_slot("ac_temperature")
        latest_message = tracker.latest_message.get('text', '').lower()

        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: điều hòa)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not ac_temperature:
            response_text = "Bạn muốn tăng/giảm nhiệt độ điều hòa là bao nhiêu ?"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        try:
            temp_value = int(ac_temperature.replace("độ", "").strip())
            if not 16 <= temp_value <= 30:
                response_text = "Nhiệt độ điều hòa phải từ 16 đến 30 độ"
                audio_url = DeviceController.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return []
        except ValueError:
            response_text = "Nhiệt độ phải là số (ví dụ: 24)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        action_verb = "tăng" if "tăng" in latest_message else "giảm" if "giảm" in latest_message else "chỉnh"
        DeviceController.control_device(dispatcher, tracker, "select_brand", {"method": "brand", "params": "Panasonic"},
                                        "Đã chọn hãng điều hòa Panasonic", "Lỗi khi chọn hãng điều hòa {device_name} (mã lỗi: {error_code})")
        return DeviceController.control_device(
            dispatcher, tracker, "ac_temperature", {"method": "temp", "params": str(temp_value)},
            "Đã {action} nhiệt độ điều hòa còn {ac_temperature} độ, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi chỉnh nhiệt độ {device_name} (mã lỗi: {error_code})", action_verb
        )

class ActionSetACMode(Action):
    def name(self) -> Text:
        return "action_set_ac_mode"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "điều hòa"
        ac_mode = tracker.get_slot("ac_mode")

        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: điều hòa)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not ac_mode:
            response_text = "Vui lòng cung cấp chế độ (ví dụ: lạnh, khô, tự động, ấm)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        valid_modes = ["khô", "tự động", "ấm", "lạnh"]
        normalized_mode = ac_mode.lower().replace(" ", "")
        if normalized_mode not in valid_modes:
            response_text = "Chế độ điều hòa phải là một trong: khô, tự động, ấm, lạnh"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        mode_mapping = {"khô": "dry", "tự động": "auto", "ấm": "heat", "lạnh": "cool"}
        DeviceController.control_device(dispatcher, tracker, "select_brand", {"method": "brand", "params": "Panasonic"},
                                        "Đã chọn hãng điều hòa Panasonic", "Lỗi khi chọn hãng điều hòa {device_name} (mã lỗi: {error_code})")
        return DeviceController.control_device(
            dispatcher, tracker, "ac_mode", {"method": "mode", "params": mode_mapping[normalized_mode]},
            "Đã để chế độ {ac_mode}, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi chỉnh chế độ {device_name} (mã lỗi: {error_code})"
        )

class ActionSetACTimer(Action):
    def name(self) -> Text:
        return "action_set_ac_timer"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "điều hòa"
        timer = tracker.get_slot("timer")

        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: điều hòa)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not timer:
            response_text = "Vui lòng cung cấp thời gian hẹn giờ (ví dụ: 30 phút)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        try:
            timer_value = float(timer.replace("phút", "").replace("tiếng", "").strip())
            if timer_value <= 0:
                response_text = "Thời gian hẹn giờ phải lớn hơn 0"
                audio_url = DeviceController.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return []
        except ValueError:
            response_text = "Thời gian hẹn giờ phải là số (ví dụ: 0.5, 1)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        DeviceController.control_device(dispatcher, tracker, "select_brand", {"method": "brand", "params": "Panasonic"},
                                        "Đã chọn hãng điều hòa Panasonic", "Lỗi khi chọn hãng điều hòa {device_name} (mã lỗi: {error_code})")
        return DeviceController.control_device(
            dispatcher, tracker, "timer", {"method": "timer", "params": str(timer_value)},
            "Tôi đã hẹn giờ tắt điều hòa cho bạn sau {timer} rồi nhé, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi hẹn giờ {device_name} (mã lỗi: {error_code})"
        )

class ActionSetTVTimer(Action):
    def name(self) -> Text:
        return "action_set_tv_timer"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "TV"
        timer = tracker.get_slot("timer")

        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: TV)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not timer:
            response_text = "Vui lòng cung cấp thời gian hẹn giờ (ví dụ: 30 phút)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        try:
            timer_value = float(timer.replace("phút", "").replace("tiếng", "").strip())
            if timer_value <= 0:
                response_text = "Thời gian hẹn giờ phải lớn hơn 0"
                audio_url = DeviceController.text_to_speech(dispatcher, response_text)
                dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
                return []
        except ValueError:
            response_text = "Thời gian hẹn giờ phải là số (ví dụ: 0.5, 1)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        DeviceController.control_device(dispatcher, tracker, "select_brand", {"method": "selectBrand", "params": "Samsung"},
                                        "Đã chọn hãng TV Samsung", "Lỗi khi chọn hãng TV {device_name} (mã lỗi: {error_code})")
        return DeviceController.control_device(
            dispatcher, tracker, "timer", {"method": "timer", "params": str(timer_value)},
            "Tôi đã hẹn giờ tắt TV cho bạn sau {timer} rồi nhé, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi hẹn giờ {device_name} (mã lỗi: {error_code})"
        )

class ActionAskMood(Action):
    def name(self) -> Text:
        return "action_ask_mood"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        response_text = "Tôi cảm thấy lúc vui, lúc bình thường, tuy nhiên tôi vui khi có người trò chuyện. Vậy bạn có cần tôi giúp gì không ?"
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return []

class ActionAskWeather(Action):
    def name(self) -> Text:
        return "action_ask_weather"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        response_text = "Có vẻ là hôm nay mát, tuy nhiên vẫn hạn chế ngoài nắng bạn nhé"
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return []

class ActionSearchHotelRestaurant(Action):
    def name(self) -> Text:
        return "action_search_hotel_restaurant"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        response_text = "Ồ, một câu hỏi tuyệt vời, nếu bạn muốn đi chơi, tôi khuyên bạn nên đi vào buổi chiều tối vì trời mát, còn nhà hàng khách sạn thì bạn hãy vào google để check quanh đây nhé."
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return []

class ActionAskGender(Action):
    def name(self) -> Text:
        return "action_ask_gender"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        response_text = "Tôi là nữ, tên tôi là Emily, nhìn bạn rất tuyệt vời, bạn có cần tôi giúp gì không ?"
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return []

class ActionAskLoveAdvice(Action):
    def name(self) -> Text:
        return "action_ask_love_advice"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        response_text = "Bạn không có người yêu thì đấy là do bạn, nhưng tôi khuyên bạn hãy chăm chỉ làm việc cho ByteHome, rồi bạn sẽ có nhiều người yêu thôi"
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return []

class ActionSetColor(Action):
    def name(self) -> Text:
        return "action_set_color"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        device = tracker.get_slot("device") or "đèn led"
        color = tracker.get_slot("color")
        if not device:
            response_text = "Vui lòng chỉ định thiết bị (ví dụ: đèn led)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        if not color:
            response_text = "Vui lòng cung cấp màu sắc (ví dụ: xanh, đỏ, vàng)"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        valid_colors = ["xanh", "đỏ", "tím", "vàng", "trắng", "cam", "xanh da trời", "xanh lá cây"]
        normalized_color = color.lower().replace(" ", "")
        if normalized_color not in valid_colors:
            response_text = "Màu sắc phải là một trong: xanh, đỏ, tím, vàng, trắng, cam, xanh da trời, xanh lá cây"
            audio_url = DeviceController.text_to_speech(dispatcher, response_text)
            dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
            return []

        return DeviceController.control_device(
            dispatcher, tracker, "color", {"method": "color", "params": COLOR_MAP[normalized_color]},
            "Đã đổi màu {device_name} thành {color}, bạn có cần hỗ trợ thêm không ?",
            "Lỗi khi đổi màu {device_name} (mã lỗi: {error_code})"
        )

class ActionFallback(Action):
    def name(self) -> Text:
        return "action_fallback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        response_text = "Xin lỗi,tôi chưa có đủ dữ liệu, vì vậy vui lòng hỏi các câu hỏi khác bạn nhé.."
        audio_url = DeviceController.text_to_speech(dispatcher, response_text)
        dispatcher.utter_message(text=response_text, custom={"audio_url": audio_url})
        return []
    
class ActionGeminiReply(Action):
    def name(self) -> Text:
        return "action_gemini_reply"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        user_msg = tracker.latest_message.get("text")
        answer = ask_gemini(user_msg)

        # Làm sạch văn bản trước khi chuyển sang giọng nói
        clean_answer = re.sub(r"[*_`~]", "", answer).strip()

        audio_url = None
        try:
            audio_url = DeviceController.text_to_speech(dispatcher, clean_answer)
        except Exception as e:
            logger.error(f"Lỗi khi chuyển văn bản thành giọng nói: {e}")

        # Gửi cả text và audio (nếu có) xuống frontend
        dispatcher.utter_message(text=answer, custom={"audio_url": audio_url})
        return []
