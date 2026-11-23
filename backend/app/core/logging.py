"""Process-wide logging. Connection strings are never written to the log."""

import logging
import sys

_HANDLER_FLAG = "_skin_analysis_handler"


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    if not any(getattr(handler, _HANDLER_FLAG, False) for handler in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        setattr(handler, _HANDLER_FLAG, True)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        root.addHandler(handler)

    for noisy in ("motor", "pymongo", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
