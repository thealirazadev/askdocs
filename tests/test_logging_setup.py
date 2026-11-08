import json
import logging

from app.logging import JsonFormatter, configure_logging


def test_uvicorn_logs_go_through_the_json_handler(capsys):
    plain = logging.StreamHandler()
    logging.getLogger("uvicorn.error").addHandler(plain)
    logging.getLogger("uvicorn.access").addHandler(plain)

    configure_logging("INFO")
    logging.getLogger("uvicorn.error").info("Application startup complete.")
    logging.getLogger("uvicorn.access").info("GET /health 200")

    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert [json.loads(line)["message"] for line in lines] == ["Application startup complete."]
    assert not logging.getLogger("uvicorn.error").handlers
    assert isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)


def test_uvicorn_color_copy_is_dropped():
    record = logging.LogRecord("uvicorn.error", logging.INFO, "", 0, "started", (), None)
    record.color_message = "\x1b[32mstarted\x1b[0m"
    assert "color_message" not in json.loads(JsonFormatter().format(record))
