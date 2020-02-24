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
        self.locked = False
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

    def message(self, message):
        self.bMessage.focus_set()
        self.root.wm_attributes("-topmost", True)
        self.bMessage.delete(0, END)
        self.bMessage.insert(0, message[-26:])

    def cursor(self, index):
        self.bMessage.focus_set()
        self.bMessage.icursor(index)

    def lock(self, state):
        self.locked = state

    def color(self, n_color):
        try:
            self.bMessage.config(fg=n_color)
        except TclError:
            print()

    def quit(self):
        self.root.destroy()


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


class Dispatch:
    def __init__(self):
        self.message = ""
        self.index = 0
        self.enter_pressed = False
        self.shift_pressed = False
        self.options = ["!tts", "!lock", "!unlock", "!white", "!black", "!yellow", "!blue", "!red", "!quit", "!exit",
                        "!stop"]
        self.options += os.listdir("./Soundboard")
        self.matches = []
        self.history = []
        self.history_index = 0
        self.matchIndex = -1
        self.tts_enabled = False
        self.app = App()

        self.to_shift = {"&": 1, "é": 2, "\"": 3, "'": 4, "(": 5, "§": 6, "è": 7, "!": 8, "ç": 9, "à": 0, "-": "_",
                         ",": "?", ";": ".", ":": "/", "=": "+"}

    def on_press(self, key):
        if key == Key.enter:
            if self.enter_pressed:
                try:
                    file = ""
                    if len(self.message) > 0 and self.message[0] == '!':  # Indicates command
                        c = self.message[1:].lower()
                        if c == "tts":
                            self.tts_enabled = not self.tts_enabled
                        elif c == "lock":
                            self.app.lock(True)
                        elif c == "unlock":
                            self.app.lock(False)
                        elif c == "stop":
                            sd.stop()
                        elif c == "quit" or c == "exit":
                            self.app.quit()
                            sys.exit()
                        else:
                            self.app.color(c)
                    elif self.message[-4:] == ".mp3":
                        file = "Soundboard/{0}".format(self.message)
                    else:
                        if self.tts_enabled:
                            file = "message.mp3"
                            self.message = re.sub("([a-zA-Z]{2,3})[cC][cC] ", r'\1ck', self.message)
                            self.message = re.sub("([a-zA-Z]{2,3})[cC][cC]$", r'\1ck', self.message)
                            self.message.replace("wtf", "what the fuck")
                            t2s = gTTS(text=self.message, lang='en-US')
                            t2s.save("message.mp3")
                    if file != "":
                        sr, array = read(file, True)
                        sd.default.device = 4
                        sd.play(array, sr)
                except AssertionError:
                    print()
                except FileNotFoundError:
                    print()

                self.index = 0
                self.matchIndex = -1
                if self.history_index != len(self.history):
                    self.history.pop()
                if self.message != "" and (len(self.history) == 0 or self.history[-1] != self.message):
                    self.history.append(self.message)
                if len(self.history) > 20:  # History size
                    self.history.pop(0)
                self.history_index = len(self.history)
                self.message = ""
                self.app.not_recording()
                self.enter_pressed = False
            else:
                self.app.recording()
                self.enter_pressed = True
        elif key == Key.esc:
            self.app.not_recording()
            self.enter_pressed = False
        elif self.enter_pressed:
            if key == Key.backspace:
                self.matchIndex = -1
                if self.index > 0:
                    self.message = self.message[:self.index - 1] + self.message[self.index:]
                    self.index -= 1
            elif key == Key.delete:
                self.matchIndex = -1
                if self.index < len(self.message):
                    self.message = self.message[:self.index] + self.message[self.index + 1:]
            elif key == Key.shift:
                self.shift_pressed = True
            elif key == Key.tab:
                if self.matchIndex == -1:
                    self.matches = list(filter(lambda x: re.match(re.escape(self.message[:self.index]),
                                                                  x, re.IGNORECASE), self.options))
                if len(self.matches) > 0:
                    self.matchIndex = (self.matchIndex + 1) % len(self.matches)
                    self.message = self.matches[self.matchIndex]
                    self.index = len(self.message)
            elif key == Key.left:
                self.index = max(self.index - 1, 0)
            elif key == Key.right:
                self.index = min(self.index + 1, len(self.message))
            elif key == Key.up and self.history_index > 0:
                if self.message != "":
                    self.history.insert(self.history_index, self.message)
                self.history_index = max(0, self.history_index - 1)
                self.message = self.history.pop(self.history_index)
            elif key == Key.down:
                if self.message != "":
                    self.history.insert(self.history_index, self.message)
                self.history_index = min(self.history_index + 1, len(self.history))
                if self.history_index < len(self.history):
                    self.message = self.history.pop(self.history_index)
                else:
                    self.message = ""
            else:
                if key == Key.space:
                    self.matchIndex = -1
                    self.message += ' '
                    self.index += 1
                else:
                    self.matchIndex = -1
                    key = str(key)
                    if key.count('"') > 1:
                        key = key.replace('"', '')
                    elif key.count("'") > 1:
                        key = key.replace("'", "")
                    if len(key) == 1:
                        if self.shift_pressed:
                            key = str(self.to_shift.get(key, key.upper()))
                            self.shift_pressed = False
                        self.message = self.message[:self.index] + key + self.message[self.index:]
                        self.index = self.index + 1

        self.app.message(self.message)
        self.app.cursor(self.index)


def loop(dispatch):
    with Listener(
            on_press=dispatch.on_press) as listener:
        listener.join()


def main():
    dispatch = Dispatch()
    capture = t.Thread(target=loop, args=[dispatch])
    capture.daemon = True
    capture.start()
    dispatch.app.root.mainloop()
    sys.exit()


if __name__ == '__main__':
    main()
