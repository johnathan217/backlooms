import logging
import json
from datetime import datetime
from pathlib import Path


class JsonFormatter(logging.Formatter):

    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "event": record.getMessage()
        }

        # Include extra data if provided
        if hasattr(record, 'data'):
            log_data.update(record.data)

        return json.dumps(log_data)


def setup_agent_logger(agent_id: str) -> logging.Logger:
    project_root = Path(__file__).parent.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(f"agent.{agent_id}")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Single log file with all events
        log_file = logs_dir / f"agent_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger
