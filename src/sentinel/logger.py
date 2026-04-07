import json
from datetime import datetime
from pathlib import Path


class SentinelLogger:
    def __init__(self, path="logs/decisions.log"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: dict):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            **record
        }

        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
