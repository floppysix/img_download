import pytest
from img_download.logger import setup_logger

def test_logger_creation():
    logger = setup_logger()
    assert logger.name == "img_download"
    assert logger.level == 20  # INFO level

def test_logger_singleton():
    logger1 = setup_logger()
    logger2 = setup_logger()
    assert logger1 is logger2
