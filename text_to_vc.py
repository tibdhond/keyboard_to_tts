from tkinter import *
from gtts import gTTS
import sounddevice as sd
import pydub
import numpy as np
from pynput.keyboard import Key, Listener
import re
import threading as t
import os

class App:
    def __init__(self):
        self.root = Tk()
        self.root.overrideredirect(1)

        self.frame = Frame(self.root, width=300, height=30,
                           borderwidth=2, relief=RAISED)

        self.frame.pack_propagate(False)
        self.frame.pack()

        self.bMessage = Entry(self.frame, width=300, background="white")
        self.bMessage.config(font=("Courier", 14, 'bold'))
        self.bMessage.pack(pady=0)

        self.root.overrideredirect(True)
        self.root.geometry("+1275+975")
        self.root.lift()
        self.root.wm_attributes("-transparentcolor", "white")
        self.root.attributes("-alpha", 1)

        self.root.wm_attributes("-topmost", True)

    def recording(self):
        self.frame.config(background='red')

    def not_recording(self):
        self.frame.config(background='white')

    def message(self):
        self.root.wm_attributes("-topmost", True)
        self.bMessage.delete(0, END)
        self.bMessage.insert(0, message[-26:])

    def quit(self):
        exit(0)


message = ""
index = 0
enter_pressed = False
shift_pressed = False
options = ["!tts"]
options += os.listdir("./Soundboard")
matches = []
matchIndex = -1
tts_enabled = False
app = App()

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
    global index
    global app
    global matches
    global matchIndex
    global tts_enabled
    global options
    if key == Key.enter:
        if enter_pressed:
            matchIndex = -1
            try:
                file = ""
                if message[0] == '!':
                    if message[1:].lower() == "tts":
                        tts_enabled = not tts_enabled
                elif message[-4:] == ".mp3":
                    file = "Soundboard/{0}".format(message)
                else:
                    if tts_enabled:
                        file = "message.mp3"
                        message = re.sub("([a-zA-Z]{2,3})[cC][cC] ", r'\1ck', message)
                        message = re.sub("([a-zA-Z]{2,3})[cC][cC]$", r'\1ck', message)
                        message.replace("wtf", "what the fuck")
                        print(message)
                        t2s = gTTS(text=message, lang='en-US')
                        t2s.save("message.mp3")
                if file != "":
                    sr, array = read(file, True)
                    sd.default.device = 4
                    sd.play(array, sr)
            except AssertionError:
                print()
            except FileNotFoundError:
                print()
            message = ""
            app.not_recording()
            enter_pressed = False
        else:
            app.recording()
            enter_pressed = True
    elif key == Key.esc:
        app.not_recording()
        enter_pressed = False
    elif key == Key.backspace and enter_pressed:
        matchIndex = -1
        message = message[:-1]
    elif key == Key.shift and enter_pressed:
        shift_pressed = True
    elif key == Key.space and enter_pressed:
        matchIndex = -1
        message += ' '
    elif key == Key.tab and enter_pressed:
        if matchIndex == -1:
            matches = list(filter(lambda x: re.match(message, x, re.IGNORECASE), options))
        if len(matches) > 0:
            matchIndex = (matchIndex + 1) % len(matches)
            message = matches[matchIndex]
    elif enter_pressed:
        matchIndex = -1
        key = str(key)
        if key.count('"') > 1:
            key = key.replace('"', '')
        elif key.count("'") > 1:
            key = key.replace("'", "")
        if len(key) == 1:
            if shift_pressed:
                key = str(to_shift.get(key, key.upper()))
                shift_pressed = False
            # print(key, shift_pressed)
            message += key
            index = min(26, index + 1)

    app.message()


def loop():
    with Listener(
            on_press=on_press) as listener:
        listener.join()


y = t.Thread(target=loop)
y.start()
app.root.mainloop()
print("check")
