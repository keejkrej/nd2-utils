from typing import Protocol, Any, Optional, Callable, runtime_checkable

class OperationCancelled(Exception):
    """Exception raised when an operation is cancelled."""
    pass

@runtime_checkable
class WorkerSignal(Protocol):
    def emit(self, *args: Any) -> None:
        ...

class SignalsInterface(Protocol):
    progress: WorkerSignal
    finished: WorkerSignal
    error: WorkerSignal

class AbstractWorker:
    """Base class for workers, implementation agnostic."""
    
    def __init__(self):
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def _check_cancelled(self):
        if self._is_cancelled:
            raise OperationCancelled("Operation was cancelled")
