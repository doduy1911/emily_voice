import asyncio
import subprocess
import platform
from .wav2vec2_vietnamese import VietnameseSTT

class VoiceInterface:
    def __init__(self):
        self.stt = VietnameseSTT()
        self.voice = 'Linh' if platform.system() == 'Darwin' else None

    def speak(self, text):
        print(f"Assistant: {text}")
        if platform.system() == 'Darwin':
            try:
                subprocess.run(['say', '-v', self.voice, text], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Lỗi khi phát giọng nói: {e}")

    async def listen_with_timeout(self, timeout=10):
        print("\nĐang nghe... (nói trong 7 giây)")
        try:
            loop = asyncio.get_event_loop()
            text = await asyncio.wait_for(
                loop.run_in_executor(None, self.stt.listen_and_transcribe),
                timeout
            )
            if text and text.strip():
                print(f"Người dùng nói: {text}")
                return text.lower()
            return ""
        except asyncio.TimeoutError:
            print("Hết thời gian chờ, không nhận diện được giọng nói.")
            return ""

    def listen(self):
        return self.stt.listen_and_transcribe()