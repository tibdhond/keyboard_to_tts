from tkinter import *
from gtts import gTTS
import sounddevice as sd
import pydub
import numpy as np
from pynput.keyboard import Key, Listener
import re
import threading as t
import os
import sys


class App:
    def __init__(self):
        self.locked = True
        self.x = 0
        self.y = 0
        self.prev_mouse_x = 0
        self.prev_mouse_y = 0
        self.root = Tk()

        self.frame = Frame(self.root, width=300, height=30,
                           borderwidth=4, relief=RAISED)

        self.frame.pack_propagate(False)
        self.frame.pack()

        self.bMessage = Entry(self.frame, width=300, background="brown", fg="black")
        self.bMessage.config(font=("Courier", 14, 'bold'))
        self.bMessage.pack(pady=0)

        self.root.overrideredirect(True)
        self.root.geometry("+%d+%d" % (self.x, self.y))
        self.root.lift()
        self.root.wm_attributes("-transparentcolor", "brown")
        self.root.attributes("-alpha", 1)

        self.root.bind("<Button-1>", self.click)
        self.root.bind("<B1-Motion>", self.drag)
        self.root.wm_attributes("-topmost", True)

    def click(self, event):
        self.prev_mouse_x = event.x
        self.prev_mouse_y = event.y

    def drag(self, event):
        if not self.locked:
            self.x -= self.prev_mouse_x - event.x
            self.y -= self.prev_mouse_y - event.y
            self.root.geometry("+%d+%d" % (self.x, self.y))

    def recording(self):
        self.frame.config(background='red')

    def not_recording(self):
        self.frame.config(background='white')

    def message(self):
        self.root.wm_attributes("-topmost", True)
        self.bMessage.delete(0, END)
        self.bMessage.insert(0, message[-26:])

    def lock(self, state):
        self.locked = state

    def color(self, n_color):
        try:
            self.bMessage.config(fg=n_color)
        except TclError:
            print()

    def quit(self):
        self.root.destroy()


message = ""
index = 0
enter_pressed = False
shift_pressed = False
options = ["!tts", "!lock", "!unlock", "!white", "!black", "!yellow", "!blue", "!red", "!quit", "!exit"]
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
                if len(message) > 0 and message[0] == '!':
                    c = message[1:].lower()
                    if c == "tts":
                        tts_enabled = not tts_enabled
                    elif c == "lock":
                        app.lock(True)
                    elif c == "unlock":
                        app.lock(False)
                    elif c == "quit" or c == "exit":
                        app.quit()
                        sys.exit()
                    else:
                        app.color(c)
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
y.daemon = True
y.start()
app.root.mainloop()
sys.exit()
