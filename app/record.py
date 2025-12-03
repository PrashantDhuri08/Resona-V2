import sounddevice as sd       
from scipy.io.wavfile import write
import numpy as np

def record_wav(filename="recorded.wav", duration_sec=8, sample_rate=44100, channels=1):
    print("Recording...")
    data = sd.rec(int(duration_sec * sample_rate), samplerate=sample_rate, channels=channels, dtype="float32")
    sd.wait()
    audio_int16 = np.int16(np.clip(data, -1.0, 1.0) * 32767)
    write(filename, sample_rate, audio_int16)
    print(f"Saved {filename}")

if __name__ == "__main__":
    record_wav("query.wav", duration_sec=8)