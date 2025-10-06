import asyncio
from rasa.core.agent import Agent
from voice_interface import VoiceInterface
import os

async def main():
    model_path = "rasa/models/20250710-161804-elaborate-betta.tar.gz"  # Thay bằng tên file mô hình mới
    if not os.path.exists(model_path):
        print(f"Lỗi: Không tìm thấy mô hình tại {model_path}")
        return
    try:
        agent = Agent.load(model_path)
    except Exception as e:
        print(f"Lỗi khi tải mô hình: {e}")
        return
    voice = VoiceInterface()

    print("Bot đã sẵn sàng. Nói '/stop' để thoát.")
    while True:
        user_input = await voice.listen_with_timeout()
        if user_input == "/stop":
            voice.speak("Tạm biệt! Hẹn gặp lại bạn!")
            break
        if user_input:
            try:
                responses = await agent.handle_text(user_input)
                for response in responses:
                    text = response.get("text", "")
                    if text:
                        voice.speak(text)
            except Exception as e:
                print(f"Lỗi khi xử lý input: {e}")
                voice.speak("Đã có lỗi xảy ra, vui lòng thử lại.")

if __name__ == "__main__":
    asyncio.run(main())