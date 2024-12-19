import json
import logging

from app.celery import app


@app.task()
def process_webhook(**kwargs):
    payload = json.loads(kwargs["payload"])
    print(payload)


if __name__ == "__main__":  # Testing.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
