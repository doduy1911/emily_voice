import torch
import sounddevice as sd
import numpy as np
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor


class VietnameseSTT:
    def __init__(self):
        self.processor = Wav2Vec2Processor.from_pretrained("nguyenvulebinh/wav2vec2-base-vietnamese-250h")
        self.model = Wav2Vec2ForCTC.from_pretrained("nguyenvulebinh/wav2vec2-base-vietnamese-250h")
        self.sample_rate = 16000
        self.duration = 5
        self.channels = 1

    def record_audio(self):
        print("Đang ghi âm... Nói ngay bây giờ!")
        audio = sd.rec(int(self.duration * self.sample_rate),
                       samplerate=self.sample_rate,
                       channels=self.channels,
                       dtype='float32')
        sd.wait()
        print("Đã ghi âm xong!")
        return audio[0]

    def speech_to_text(self, audio):
        input_values = self.processor(audio,
                                      sampling_rate=self.sample_rate,
                                      return_tensors="pt").input_values

        with torch.no_grad():
            logits = self.model(input_values).logits

        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.batch_decode(predicted_ids)[0]

        return transcription.lower()

    def listen_and_transcribe(self):
        audio = self.record_audio()
        text = self.speech_to_text(audio)
        return text