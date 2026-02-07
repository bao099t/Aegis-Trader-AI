import json
import os
import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '../../data')
SEEN_FILE = os.path.join(DATA_DIR, 'seen.json')

class StateManager:
    def __init__(self):
        self.ensure_data_dir()
        self.seen_links = self.load_seen()

    def ensure_data_dir(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def load_seen(self):
        if os.path.exists(SEEN_FILE):
            try:
                with open(SEEN_FILE, 'r') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_seen(self):
        with open(SEEN_FILE, 'w') as f:
            json.dump(list(self.seen_links), f)

    def is_seen(self, link):
        return link in self.seen_links

    def add_seen(self, link):
        self.seen_links.add(link)
        # Auto-save every time or periodically? 
        # For MVP, save every time is safer vs crash.
        self.save_seen()
