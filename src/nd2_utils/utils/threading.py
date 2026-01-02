"""
Threading utilities for background operations.
"""

import logging
from typing import Callable

from PySide6.QtCore import QThread, Signal
from ..core.worker import AbstractWorker, OperationCancelled as CoreOperationCancelled

logger = logging.getLogger(__name__)

# Alias for backward compatibility
OperationCancelled = CoreOperationCancelled

class BaseWorkerThread(QThread, AbstractWorker):
    """Base class for worker threads with common functionality."""

    # Common signals
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self):
        # Initialize both parents
        QThread.__init__(self)
        AbstractWorker.__init__(self)

    # Note: cancel(), is_cancelled(), and _check_cancelled() are inherited from AbstractWorker

    def run(self):
        """Override in subclasses to implement the actual work."""
        raise NotImplementedError("Subclasses must implement run() method")


def progress_callback(total_steps: int) -> Callable[[int], None]:
    """Create a progress callback function for worker threads."""

    def _progress_update(current_step: int):
        progress = min(int((current_step / total_steps) * 100), 100)
        return progress

    return _progress_update
