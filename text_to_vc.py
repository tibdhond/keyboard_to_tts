from gtts import gTTS
import sounddevice as sd
import pydub
import numpy as np
from pynput.keyboard import Key, Listener

message = ""
enter_pressed = False
shift_pressed = False

to_shift = {"&": 1, "é": 2, "\"": 3, "'": 4, "(": 5, "§": 6, "è": 7, "!": 8, "ç": 9, "à": 0, "-": "_",
            ",": "?", ";": ".", ":": "/", "=": "+"}


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


def on_press(key):
    global message
    global enter_pressed
    global shift_pressed
    if key == Key.enter:
        if enter_pressed:
            try:
                file = "message.mp3"
                if message[-4:] == ".mp3":
                    file = "Soundboard/{0}".format(message)
                else:
                    t2s = gTTS(text=message, lang='en-US')
                    t2s.save("message.mp3")
                sr, array = read(file, True)
                sd.default.device = 6
                sd.play(array, sr)
                message = ""
            except AssertionError:
                print()
            except FileNotFoundError:
                print()
            enter_pressed = False
        else:
            enter_pressed = True
    elif key == Key.esc:
        enter_pressed = False
    elif key == Key.backspace and enter_pressed:
        message = message[:-1]
    elif key == Key.shift and enter_pressed:
        shift_pressed = True
    elif key == Key.space and enter_pressed:
        message += ' '
    elif enter_pressed:
        key = str(key)
        if key.count('"') > 1:
            key = key.replace('"', '')
        elif key.count("'") > 1:
            key = key.replace("'", "")
        if len(key) == 1:
            if shift_pressed:
                key = str(to_shift.get(key, key.upper()))
                shift_pressed = False
            print(key)
            message += key


# Collect events until released
with Listener(
        on_press=on_press) as listener:
    listener.join()


