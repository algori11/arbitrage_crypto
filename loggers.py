import time
import requests
import json
import threading

class console_logger:
    def log(msg):
        print(msg)

class file_logger:
    def __init__(self, filename):
        self.filename = filename
    
    def log(self, msg):
        with open(self.filename, 'a') as f:
            f.write(msg + "\r\n")

class slack_logger:
    def __init__(self, url):
        self.slack_url = url

        self.messages = []

        self.writer_lock = threading.Lock()

        self.shutdown_event = threading.Event()
        self.resume_event = threading.Event()
        self.thread = threading.Thread(target = self.target)
        self.thread.start()

    def log(self, msg):
        with self.writer_lock:
            self.messages.append(msg)
            self.resume_event.set()

    def slack_post(self, msg):
        retry_count = 5
        while retry_count > 0:
            try:
                requests.post(self.slack_url, data=json.dumps({'text': msg}), timeout=2)
                retry_count = 0
            except Exception as e:
                print(e, 'SLACK post error')
                retry_count -= 1
                time.sleep(2)

    def target(self):
        while not self.shutdown_event.is_set():
            while not self.resume_event.is_set():
                time.sleep(1)
            self.resume_event.clear()
            if len(self.messages) > 0:
                with self.writer_lock:
                    while len(self.messages) > 0:
                        self.slack_post(self.messages.pop(0))
    
    def shutdown(self):
        with self.writer_lock:
            self.messages = []

        self.resume_event.set()
        self.shutdown_event.set()
        self.thread.join()
