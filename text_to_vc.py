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
import json


class App:
    def __init__(self, config):
        self.locked = config["locked"]
        self.x = config["x"]
        self.y = config["y"]
        self.prev_mouse_x = 0
        self.prev_mouse_y = 0
        self.font_color = config["font_color"]
        self.window_start = 0
        self.window_length = 25

        self.root = Tk()

        self.frame = Frame(self.root, width=300, height=30,
                           borderwidth=4, relief=RAISED)

        self.frame.pack_propagate(False)
        self.frame.pack()

        self.bMessage = Entry(self.frame, width=300, background="brown", fg="black")
        self.bMessage.config(font=("Courier", 14, 'bold'))
        self.bMessage.pack(pady=0)

        try:
            self.bMessage.config(fg=self.font_color)
        except TclError:
            pass

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

    def message(self, message, index):
        self.bMessage.focus_set()
        self.root.wm_attributes("-topmost", True)
        self.bMessage.delete(0, END)
        start = max(0, min(index, len(message)-self.window_length))
        self.bMessage.insert(0, message[start:start+self.window_length])
        self.cursor(index-start)

    def cursor(self, index):
        self.bMessage.focus_set()
        self.bMessage.icursor(index)

    def lock(self, state):
        self.locked = state

    def color(self, n_color):
        try:
            self.bMessage.config(fg=n_color)
        except TclError:
            pass

    def quit(self):
        self.root.destroy()


def read(f, normalized=True):
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
    def __init__(self, config):
        self.message = ""
        self.index = 0                  # Location of cursor
        self.enter_pressed = False      # Keep track of whether the program is recording
        self.shift_pressed = False
        self.commands = {"!tts": self.toggle_tts, "!lock": self.lock, "!unlock": self.unlock,
                         "!colour": self.font_colour, "!stop": self.stop, "!sound_device": self.detect_sd,
                         "!quit": self.quit, "!exit": self.quit, "!reload": self.reload}
        self.options = sorted(self.commands.keys())
        self.options += sorted(os.listdir("./Soundboard"))
        self.matches = []       # autocomplete matches
        self.matchIndex = -1
        self.history = []       # Keep track of previous entries
        self.history_index = 0  # Index in history
        self.temp = False       # Keeps track of whether a temp entry is added to history
        self.tts_enabled = config["tts_enabled"]
        self.app = App(config)

        self.curr_dir = ''

        self.sound_device = config["sound_device"]
        if self.sound_device == -1:
            self.detect_sd()

        sd.default.device = self.sound_device

        self.to_shift = {"&": 1, "é": 2, "\"": 3, "'": 4, "(": 5, "§": 6, "è": 7, "!": 8, "ç": 9, "à": 0, "-": "_",
                         ",": "?", ";": ".", ":": "/", "=": "+"}

        self.top_dispatch = {Key.enter: self.on_enter, Key.esc: self.on_esc}
        self.bottom_dispatch = {Key.backspace: self.on_backspace, Key.delete: self.on_delete,
                                Key.shift: self.on_shift, Key.tab: self.on_tab, Key.left: self.on_left,
                                Key.right: self.on_right, Key.up: self.on_up, Key.down: self.on_down,
                                Key.space: self.on_space}

    def detect_sd(self):
        i = 0
        devices = sd.query_devices()
        while i < len(devices) and devices[i]['name'] != "CABLE Input (VB-Audio Virtual C":
            i += 1
        if i == len(devices):
            self.app.font_color = 'red'
            self.message = "SD could not be determined"
            self.index = len(self.message)
            self.app.message(self.message)
            self.app.cursor(self.index)
            return True
        else:
            self.sound_device = i
            sd.default.device = i
            return False

    def toggle_tts(self):
        self.tts_enabled = not self.tts_enabled
        return False

    def lock(self):
        self.app.lock(True)
        return False

    def unlock(self):
        self.app.lock(False)
        return False

    def font_colour(self, args):
        self.app.color(args[0])
        return False

    def stop(self):
        sd.stop()
        return False

    def reload(self):
        self.options = sorted(self.commands.keys())
        self.options += [x for x in sorted(os.listdir("./Soundboard/"))]
        return False

    def quit(self):
        self.write_settings()
        self.app.quit()
        sys.exit()

    def on_press(self, key):
        self.top_dispatch.get(key, self.on_any)(key)

        self.app.message(self.message, self.index)
        # self.app.cursor(self.index)

    def on_enter(self, key):
        if self.enter_pressed:
            try:
                file = ""
                if len(self.message) > 0 and self.message[0] == '!':  # Indicates command
                    try:
                        c = self.message.lower().split(" ")
                        if len(c) == 1:
                            if self.commands[c[0]]():
                                return
                        else:
                            try:
                                if self.commands[c[0]](c[1:]):
                                    return
                            except TypeError:
                                pass
                    except KeyError:
                        pass
                elif self.message[-4:] == ".mp3" or self.message[-4:] == ".wav":
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
                    sd.play(array, sr)
            except AssertionError:
                pass
            except FileNotFoundError:
                pass

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
            self.curr_dir = ""
            self.reload()
            self.app.not_recording()
            self.enter_pressed = False
        else:
            self.app.recording()
            self.enter_pressed = True

    def on_esc(self, key):
        self.app.not_recording()
        self.enter_pressed = False

    def on_backspace(self, key):
        self.matchIndex = -1
        if self.index > 0:
            if self.message[self.index-1] == '/':
                # find first '/' before deleted char and refresh option list
                self.curr_dir = self.message[:self.message[:self.index-1].rfind('/')]
                if os.path.exists("./Soundboard/%s" % self.curr_dir):
                    self.options = ["%s/%s" % (self.curr_dir, x)
                                    for x in sorted(os.listdir("./Soundboard/%s" % self.curr_dir))]
            self.message = self.message[:self.index - 1] + self.message[self.index:]
            self.index -= 1

    def on_delete(self, key):
        self.matchIndex = -1
        if self.index < len(self.message):
            if self.message[self.index] == '/':
                # find first '/' before deleted char and refresh option list
                self.curr_dir = self.message[:self.message[:self.index].rfind('/')]
                if os.path.exists("./Soundboard/%s" % self.curr_dir):
                    self.options = ["%s/%s" % (self.curr_dir, x)
                                    for x in sorted(os.listdir("./Soundboard/%s" % self.curr_dir))]
            self.message = self.message[:self.index] + self.message[self.index + 1:]

    def on_shift(self, key):
        self.shift_pressed = True

    def on_tab(self, key):
        print(self.options)
        if self.temp:
            self.history.pop()
            self.temp = False
            self.history_index = len(self.history)
        if self.matchIndex == -1:
            self.matches = list(filter(lambda x: re.match(re.escape(self.message[:self.index]),
                                                          x, re.IGNORECASE), self.options))
        if len(self.matches) > 0:
            self.matchIndex = (self.matchIndex + 1) % len(self.matches)
            self.message = self.matches[self.matchIndex]
            self.index = len(self.message)

    def on_left(self, key):
        self.index = max(self.index - 1, 0)

    def on_right(self, key):
        self.index = min(self.index + 1, len(self.message))

    def on_up(self, key):
        if self.history_index > 0:
            if self.message != "":
                self.history.insert(self.history_index, self.message)
            self.history_index = max(0, self.history_index - 1)
            self.message = self.history.pop(self.history_index)
        if self.history_index <= len(self.history) and self.temp:
            self.temp = False

    def on_down(self, key):
        if self.temp and self.history_index == len(self.history):
            self.history.pop()
        if self.message != "":
            self.history.insert(self.history_index, self.message)
        self.history_index = min(self.history_index + 1, len(self.history))
        if self.history_index < len(self.history):
            self.message = self.history.pop(self.history_index)
        else:
            self.message = ""
            self.temp = True

    def on_space(self, key):
        self.matchIndex = -1
        self.message += ' '
        self.index += 1

    def on_non_special(self, key):
        if self.temp:
            self.history.pop()
            self.temp = False
            self.history_index = len(self.history)
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
            if key == "/":
                self.curr_dir = self.message
                if os.path.exists("./Soundboard/%s" % self.curr_dir):
                    self.options = ["%s/%s" % (self.curr_dir, x)
                                    for x in sorted(os.listdir("./Soundboard/%s" % self.curr_dir))]
                print(self.curr_dir, self.message)
            self.message = self.message[:self.index] + key + self.message[self.index:]
            self.index = self.index + 1

    def on_any(self, key):
        if self.enter_pressed:
            self.bottom_dispatch.get(key, self.on_non_special)(key)

    def write_settings(self):
        with open("config.json", "w") as f:
            json.dump({"tts_enabled": self.tts_enabled, "locked": self.app.locked,
                       "x": self.app.x, "y": self.app.y, "font_color": self.app.font_color,
                       "sound_device": self.sound_device}, f)


def loop(dispatch):
    with Listener(
            on_press=dispatch.on_press) as listener:
        listener.join()


def read_settings():
    with open("config.json", "r") as f:
        config = json.load(f)
    return config


def main():
    config = read_settings()
    dispatch = Dispatch(config)
    capture = t.Thread(target=loop, args=[dispatch])
    capture.daemon = True
    capture.start()
    dispatch.app.root.mainloop()
    sys.exit()


if __name__ == '__main__':
    main()
