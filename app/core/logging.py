import logging
import sys

LOG_FORMAT = "%(asctime)s || %(levelname)-8s | %(name)s - %(message)s"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
