#!/usr/bin/env python3

import curses
import subprocess
import threading
import time
import os
from pathlib import Path
from datetime import datetime

class YtDlpTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        curses.start_color()
        curses.use_default_colors()
        self.init_colors()
        self.url_input = ""
        self.url_queue = []
        self.download_path = str(Path.home() / "Downloads")
        self.audio_only = False
        self.quality = "720"
        self.current_field = 0
        self.downloading = False
        self.log_messages = []
        self.fields = ["url", "path", "audio", "quality", "download"]
        self.labels = ["Add URL", "Path", "Audio Only", "Quality", "Download"]
        curses.curs_set(0)
        self.stdscr.nodelay(True)

    def init_colors(self):
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_CYAN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_WHITE, -1)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(8, curses.COLOR_BLUE, -1)

    def draw_border(self, y, x, h, w, title=""):
        self.stdscr.addstr(y, x, "╭" + "─" * (w - 2) + "╮", curses.color_pair(2))
        for i in range(1, h - 1):
            self.stdscr.addstr(y + i, x, "│", curses.color_pair(2))
            self.stdscr.addstr(y + i, x + w - 1, "│", curses.color_pair(2))
        self.stdscr.addstr(y + h - 1, x, "╰" + "─" * (w - 2) + "╯", curses.color_pair(2))
        if title:
            t = f" {title} "
            xpos = x + (w - len(t)) // 2
            self.stdscr.addstr(y, xpos, t, curses.color_pair(2) | curses.A_BOLD)

    def draw_header(self):
        title = "yt-dlp Queue TUI"
        subtitle = "Add URLs → hit Space to batch download"
        tx = (self.width - len(title)) // 2
        sx = (self.width - len(subtitle)) // 2
        self.stdscr.addstr(1, tx, title, curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(2, sx, subtitle, curses.color_pair(8))
        self.stdscr.addstr(3, 2, "─" * (self.width - 4), curses.color_pair(2))

    def draw_inputs(self):
        base_y = 5
        h = 3
        for i, (f, label) in enumerate(zip(self.fields[:-1], self.labels[:-1])):
            y = base_y + i * h
            selected = (i == self.current_field)
            color = curses.color_pair(3) if selected else curses.color_pair(2)
            self.draw_border(y, 2, 3, self.width - 4)
            self.stdscr.addstr(y, 4, f" {label} ", color | curses.A_BOLD)

            if f == "url":
                val = self.url_input[:self.width - 10] + "..." if len(self.url_input) > self.width - 10 else self.url_input
                val_color = curses.color_pair(6) if self.url_input else curses.color_pair(8)
            elif f == "path":
                val = self.download_path
                if len(val) > self.width - 10:
                    val = "..." + val[-(self.width - 13):]
                val_color = curses.color_pair(6)
            elif f == "audio":
                val = "Yes" if self.audio_only else "No"
                val_color = curses.color_pair(1) if self.audio_only else curses.color_pair(6)
            elif f == "quality":
                val = f"{self.quality}p"
                val_color = curses.color_pair(6)

            if selected:
                val_color |= curses.A_REVERSE
            self.stdscr.addstr(y + 1, 4, val, val_color)

    def draw_download_button(self):
        y = 5 + (len(self.fields) - 1) * 3
        selected = (self.current_field == len(self.fields) - 1)
        if self.downloading:
            text = "⏳ Working..."
            color = curses.color_pair(3) | curses.A_BOLD
        else:
            text = f"🚀 Download {len(self.url_queue)} Queued"
            color = curses.color_pair(1) | curses.A_BOLD
        if selected:
            color |= curses.A_REVERSE
        w = len(text) + 4
        x = (self.width - w) // 2
        self.draw_border(y, x - 1, 3, w + 2)
        self.stdscr.addstr(y + 1, x + 1, text, color)

    def draw_log(self):
        y = max(22, self.height - 10)
        h = self.height - y - 1
        if h <= 2:
            return
        self.draw_border(y, 2, h, self.width - 4, "Log")
        recent = self.log_messages[-(h - 2):]
        for i, (t, msg, color) in enumerate(recent):
            if y + 1 + i < self.height - 1:
                time_str = t.strftime("%H:%M:%S")
                self.stdscr.addstr(y + 1 + i, 4, time_str, curses.color_pair(8))
                self.stdscr.addstr(y + 1 + i, 13, msg[:self.width - 15], curses.color_pair(color))

    def add_log(self, msg, color=6):
        self.log_messages.append((datetime.now(), msg, color))
        if len(self.log_messages) > 100:
            self.log_messages.pop(0)

    def edit_field(self, name):
        if name == "url":
            val = self.prompt_input("Add a YouTube link", self.url_input)
            if val:
                self.url_queue.append(val)
                self.url_input = ""
                self.add_log(f"+ Queued: {val}", 5)
        elif name == "path":
            val = self.prompt_input("Download Path", self.download_path)
            if val:
                self.download_path = val
        elif name == "audio":
            self.audio_only = not self.audio_only
        elif name == "quality":
            opts = ["360", "480", "720", "1080", "best"]
            i = opts.index(self.quality) if self.quality in opts else 2
            self.quality = opts[(i + 1) % len(opts)]

    def prompt_input(self, prompt, default=""):
        win = curses.newwin(5, self.width - 10, self.height // 2 - 2, 5)
        win.box()
        win.addstr(1, 2, prompt, curses.color_pair(2) | curses.A_BOLD)
        win.addstr(3, 2, "Enter text (ESC to cancel):", curses.color_pair(6))
        win.refresh()
        curses.curs_set(1)
        curses.echo()
        try:
            val = win.getstr(2, 2, self.width - 16).decode('utf-8')
            return val if val else default
        except:
            return None
        finally:
            curses.noecho()
            curses.curs_set(0)
            win.clear()
            win.refresh()

    def start_download(self):
        if not self.url_queue:
            self.add_log("Queue is empty", 4)
            return
        if not os.path.exists(self.download_path):
            self.add_log("Download path doesn't exist", 4)
            return
        self.downloading = True
        threading.Thread(target=self.download_worker, daemon=True).start()

    def download_worker(self):
        while self.url_queue:
            url = self.url_queue.pop(0)
            try:
                self.add_log(f"⏬ {url}", 3)
                cmd = ['yt-dlp', '-o', os.path.join(self.download_path, '%(title)s.%(ext)s')]
                if self.audio_only:
                    cmd += ['-f', 'bestaudio/best', '--extract-audio']
                else:
                    if self.quality == "best":
                        cmd += ['-f', 'best']
                    else:
                        cmd += ['-f', f'best[height<={self.quality}]/best']
                cmd.append(url)

                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        self.add_log(line, 6)
                proc.wait()
                if proc.returncode == 0:
                    self.add_log("✓ Done", 1)
                else:
                    self.add_log("✗ Failed", 4)
            except Exception as e:
                self.add_log(f"Error: {str(e)}", 4)
        self.downloading = False

    def run(self):
        self.add_log("yt-dlp queue ready", 1)
        while True:
            self.stdscr.clear()
            self.draw_header()
            self.draw_inputs()
            self.draw_download_button()
            self.draw_log()
            self.stdscr.addstr(self.height - 1, 0,
                f"Fields: {self.current_field + 1}/{len(self.fields)} | q:quit | Enter:add/edit | Space:download"[:self.width - 1],
                curses.color_pair(7))
            self.stdscr.refresh()

            try:
                key = self.stdscr.getch()
                if key == -1:
                    pass
                elif key in [ord('q'), 27]:
                    break
                elif key == curses.KEY_UP:
                    self.current_field = (self.current_field - 1) % len(self.fields)
                elif key == curses.KEY_DOWN:
                    self.current_field = (self.current_field + 1) % len(self.fields)
                elif key in [ord('\n'), ord('\r')]:
                    if self.current_field < len(self.fields):
                        self.edit_field(self.fields[self.current_field])
                elif key == ord(' ') and not self.downloading:
                    self.start_download()
            except KeyboardInterrupt:
                break
            time.sleep(0.05)

def main():
    try:
        curses.wrapper(lambda stdscr: YtDlpTUI(stdscr).run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
