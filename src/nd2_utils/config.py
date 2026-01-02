"""
Configuration settings for ND2 Utils.
"""

import logging
import sys

# Application metadata
APP_NAME = "ND2 Utils"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "Utility tools for working with ND2 files"

# File format constants
ND2_EXTENSIONS = [".nd2"]
TIFF_EXTENSIONS = [".tif", ".tiff"]

# Default settings
DEFAULT_OUTPUT_FORMAT = ".tif"

# Dimension order
STANDARD_AXES = ["T", "P", "C", "Y", "X"]

# GUI settings
WINDOW_GEOMETRY = (100, 100, 1000, 700)
GUI_STYLE = "Fusion"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.DEBUG


def setup_logging():
    """Set up logging configuration for the application."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=LOG_LEVEL,
            format=LOG_FORMAT,
            handlers=[logging.StreamHandler(sys.stdout)],
        )
    # Set debug level for all loggers
    logging.getLogger().setLevel(LOG_LEVEL)

    # Ensure all nd2_utils loggers are at debug level
    for logger_name in logging.Logger.manager.loggerDict:
        if "nd2_utils" in logger_name:
            logging.getLogger(logger_name).setLevel(LOG_LEVEL)
