"""
Threading utilities for background operations.
"""

import logging
from typing import Callable, Any
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class BaseWorkerThread(QThread):
    """Base class for worker threads with common functionality."""
    
    # Common signals
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self._is_cancelled = False
    
    def cancel(self):
        """Cancel the operation."""
        logger.debug("Worker thread cancelled")
        self._is_cancelled = True
    
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled."""
        return self._is_cancelled
    
    def run(self):
        """Override in subclasses to implement the actual work."""
        raise NotImplementedError("Subclasses must implement run() method")
    
    def _check_cancelled(self):
        """Check if operation was cancelled and raise exception if so."""
        if self._is_cancelled:
            raise OperationCancelled("Operation was cancelled by user")


class OperationCancelled(Exception):
    """Exception raised when an operation is cancelled."""
    pass


def progress_callback(total_steps: int) -> Callable[[int], None]:
    """Create a progress callback function for worker threads."""
    def _progress_update(current_step: int):
        progress = min(int((current_step / total_steps) * 100), 100)
        return progress
    
    return _progress_update
