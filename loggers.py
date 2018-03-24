import time
import requests
import json
import threading

class aggregator:
    def __init__(self, l):
        if isinstance(l, list):
            self.lagg = l
        else:
            self.lagg = [l]

    def append(self, l):
        if isinstance(l, list):
            self.lagg += l
        else:
            self.lagg.append(l)
    
    def log(self, msg):
        for logger in self.lagg:
            logger.log(msg)

    def shutdown(self):
        for logger in self.lagg:
            if callable(getattr(logger, 'shutdown', None)):
                logger.shutdown()


class console_logger:
    def log(self, msg):
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
            self.resume_event.wait()
            self.resume_event.clear()
            if len(self.messages) > 0:
                while len(self.messages) > 0:
                    message = self.messages[0]
                    with self.writer_lock:
                        self.messages.pop(0)
                    self.slack_post(message)
    
    def shutdown(self):
        with self.writer_lock:
            self.messages = []

        self.shutdown_event.set()
        self.resume_event.set()
        self.thread.join()
