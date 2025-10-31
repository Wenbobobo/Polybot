import logging
from polybot.observability.logging import setup_logging


def test_setup_logging_json(capsys):
    setup_logging(level="INFO", json_output=True)
    logger = logging.getLogger("polybot.test")
    logger.info("hello %s", "world")
    captured = capsys.readouterr().out.strip()
    assert captured.startswith("{") and captured.endswith("}")
    assert '"message": "hello world"' in captured

