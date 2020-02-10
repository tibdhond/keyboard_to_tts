import speech_recognition as sr
import pydub
import numpy as np
from gtts import gTTS
import sounddevice as sd


def read(f, normalized=False):
    """MP3 to numpy array"""
    a = pydub.AudioSegment.from_mp3(f)
    y = np.array(a.get_array_of_samples())
    if a.channels == 2:
        y = y.reshape((-1, 2))
    if normalized:
        return a.frame_rate, np.float32(y) / 2 ** 15
    else:
        return a.frame_rate, y


message = ""
r = sr.Recognizer()
mic = sr.Microphone(device_index=2)
file = "message.mp3"
print(sr.Microphone.list_microphone_names())
while True:
    try:

        with mic as source:
            r.adjust_for_ambient_noise(source)
            audio = r.listen(source)

        message = "You said: %s" % r.recognize_sphinx(audio)

    except sr.UnknownValueError:
        message = "wot?"
    finally:
        t2s = gTTS(text=message, lang='en-US')
        t2s.save("message.mp3")

        s, array = read(file, True)
        sd.default.device = 5
        sd.play(array, s)
        sd.wait()