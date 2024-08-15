# main.py
import os
import signal
import sys
import time
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox
from channel import channel_factory
from common import const
from config import load_config, conf
from plugins import *
import threading
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CONFIG_PATH = "./config.json"

def sigterm_handler_wrap(_signo):
    old_handler = signal.getsignal(_signo)

    def func(_signo, _stack_frame):
        logger.info("signal {} received, exiting...")
        conf().save_user_datas()
        if callable(old_handler):
            return old_handler(_signo, _stack_frame)
        sys.exit(0)

    signal.signal(_signo, func)

def start_channel(channel_name: str):
    channel = channel_factory.create_channel(channel_name)
    if channel_name in ["wx", "wxy", "terminal", "wechatmp", "wechatmp_service", "wechatcom_app", "wework",
                        "wechatcom_service", const.FEISHU, const.DINGTALK]:

        PluginManager().load_plugins()

    if conf().get("use_linkai"):
        try:
            from common import linkai_client
            threading.Thread(target=linkai_client.start, args=(channel,)).start()
        except Exception as e:
            pass
    channel.startup()

def run():
    try:
        load_config()
        channel_name = conf().get("channel_type", "wx")
        if "--cmd" in sys.argv:
            channel_name = "terminal"
        if channel_name == "wxy":
            os.environ["WECHATY_LOG"] = "warn"
        start_channel(channel_name)
        while True:
            time.sleep(1)
    except Exception as e:
        logger.error("App startup failed!")
        logger.exception(e)

def save_config(bot_id, token):
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        config["coze_bot_id"] = bot_id
        config["coze_api_key"] = token
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error("Failed to save config!")
        logger.exception(e)

class TextHandler(logging.Handler):
    """ This class allows you to log to a Tkinter Text widget """
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("白话一键微信机器人包-cow版")
        self.root.geometry("500x400")

        self.bot_id = tk.StringVar()
        self.token = tk.StringVar()
        
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                self.bot_id.set(config.get("coze_bot_id", ""))
                self.token.set(config.get("coze_api_key", ""))
        except Exception as e:
            logger.error("Failed to load config!")
            logger.exception(e)
        
        # BOT_ID input
        tk.Label(root, text="BOT_ID").grid(row=0, column=0, padx=5, pady=5)
        tk.Entry(root, textvariable=self.bot_id, width=30).grid(row=0, column=1, padx=5, pady=5)

        # TOKEN input
        tk.Label(root, text="TOKEN").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(root, textvariable=self.token, width=30).grid(row=1, column=1, padx=5, pady=5)

        # Start/Stop button
        self.start_button = tk.Button(root, text="启动", command=self.toggle_start)
        self.start_button.grid(row=2, column=1, padx=5, pady=5, sticky="e")

        # Log display
        tk.Label(root, text="运行日志").grid(row=3, column=0, padx=5, pady=5)
        self.log_display = scrolledtext.ScrolledText(root, width=58, height=15, state='disabled')
        self.log_display.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        # Footer
        tk.Label(root, text="@白话Agent   代码主页：https://github.com/ImGoodBai/onewebot2").grid(row=5, column=0, columnspan=2, padx=5, pady=5)

        self.process_thread = None

        # Set up signal handlers in the main thread
        sigterm_handler_wrap(signal.SIGINT)
        sigterm_handler_wrap(signal.SIGTERM)

        # Set up logging to text widget
        text_handler = TextHandler(self.log_display)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(text_handler)

        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)

    def toggle_start(self):
        if self.start_button["text"] == "启动":
            if not self.bot_id.get() or not self.token.get():
                messagebox.showerror("错误", "BOT_ID和TOKEN为必填项")
                return

            save_config(self.bot_id.get(), self.token.get())
            self.process_thread = threading.Thread(target=run)
            self.process_thread.start()
            self.start_button["text"] = "退出"
        else:
            # Stop the running process
            os.kill(os.getpid(), signal.SIGINT)
            self.start_button["text"] = "启动"

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
