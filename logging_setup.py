import logging
import os
import sys

_CONFIGURED = False


def configure() -> None:
  global _CONFIGURED
  if _CONFIGURED:
    return
  level_name = os.environ.get('VC_LOG_LEVEL', 'INFO').upper()
  level = getattr(logging, level_name, logging.INFO)
  handler = logging.StreamHandler(stream=sys.stderr)
  handler.setFormatter(logging.Formatter(
    fmt='%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S',
  ))
  root = logging.getLogger()
  root.handlers.clear()
  root.addHandler(handler)
  root.setLevel(level)
  _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
  return logging.getLogger(name)
