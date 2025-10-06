import torch
import sounddevice as sd
import numpy as np
from scipy.io import wavfile
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

class VietnameseSTT:
    def __init__(self):
        self.processor = Wav2Vec2Processor.from_pretrained("nguyenvulebinh/wav2vec2-base-vietnamese-250h")
        self.model = Wav2Vec2ForCTC.from_pretrained("nguyenvulebinh/wav2vec2-base-vietnamese-250h")
        self.sample_rate = 16000
        self.duration = 7
        self.channels = 1
        self.device = 2

    def record_audio(self):
        print("Đang ghi âm... Nói ngay bây giờ!")
        try:
            audio = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                device=self.device
            )
            sd.wait()
            print("Đã ghi âm xong!")
            audio = np.clip(audio, -1.0, 1.0)
            print(f"Shape of audio: {audio.shape}, Max amplitude: {np.max(np.abs(audio))}")
            return audio.flatten()
        except Exception as e:
            print(f"Lỗi khi ghi âm: {e}")
            return np.zeros(int(self.duration * self.sample_rate), dtype=np.float32)

    def save_audio(self, audio, filename="test.wav"):
        try:
            audio_2d = audio.reshape(-1, 1)
            wavfile.write(filename, self.sample_rate, audio_2d)
            print(f"Đã lưu file âm thanh: {filename}")
        except Exception as e:
            print(f"Lỗi khi lưu file âm thanh: {e}")

    def speech_to_text(self, audio):
        try:
            if len(audio) < 1600 or np.max(np.abs(audio)) < 0.01:
                print("Âm thanh quá nhỏ hoặc không có giọng nói.")
                return ""
            input_values = self.processor(
                audio,
                sampling_rate=self.sample_rate,
                return_tensors="pt"
            ).input_values
            with torch.no_grad():
                logits = self.model(input_values).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.processor.batch_decode(predicted_ids)[0]
            print(f"Transcribed text: {transcription}")
            return transcription.lower()
        except Exception as e:
            print(f"Lỗi khi chuyển giọng nói thành văn bản: {e}")
            return ""

    def listen_and_transcribe(self):
        audio = self.record_audio()
        if audio is None:
            return ""
        self.save_audio(audio, "test.wav")
        return self.speech_to_text(audio)