from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class WorkerSignal(Protocol):
    def emit(self, *args: Any) -> None:
        ...

class SignalsInterface(Protocol):
    progress: WorkerSignal
    finished: WorkerSignal
    error: WorkerSignal

class DummySignal:
    def emit(self, *args: Any) -> None:
        pass

class DefaultSignals:
    def __init__(self):
        self.progress = DummySignal()
        self.finished = DummySignal()
        self.error = DummySignal()
