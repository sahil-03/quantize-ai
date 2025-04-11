import logging
import os
import sys
from pathlib import Path


class Logger:
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    def __init__(
        self, 
        name: str, 
        log_level: str = 'INFO', 
        log_file: Path | str = None, 
        console_output: bool = True, 
        format_string: str = None
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.LOG_LEVELS.get(log_level.upper(), logging.INFO))
        self.logger.handlers = []
        self.logger.propagate = False
        
        if not format_string:
            format_string = "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"
        
        formatter = logging.Formatter(format_string)
        
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)
    
    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)
    
    def warning(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs)
    
    def critical(self, *args, **kwargs):
        self.logger.critical(*args, **kwargs)
    
    def exception(self, *args, **kwargs):
        self.logger.exception(*args, **kwargs)