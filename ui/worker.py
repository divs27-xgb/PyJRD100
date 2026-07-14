from PyQt6.QtCore import QThread, pyqtSignal


class Worker(QThread):
    """Runs a callable in a background thread and emits the result.

    Usage:
        worker = Worker(some_function, arg1, arg2)
        worker.result_ready.connect(on_result)
        worker.start()

    Signals:
        result_ready(object)  -- emitted with the return value of the function
        error(str)            -- emitted with the exception message on failure
    """

    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class StreamWorker(QThread):
    """Continuously yields tag data from reader.stream_tags().

    Signals:
        tag_received(dict)  -- emitted for each tag dict
        error(str)          -- emitted on stream error
        stopped()           -- emitted when the stream ends
    """

    tag_received = pyqtSignal(dict)
    error = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(self, reader, timeout=1):
        super().__init__()
        self._reader = reader
        self._timeout = timeout
        self._running = True

    def run(self):
        try:
            for tag in self._reader.stream_tags(timeout=self._timeout):
                if not self._running:
                    break
                if tag is not None:
                    self.tag_received.emit(tag)
        except Exception as e:
            if self._running:
                self.error.emit(str(e))
        finally:
            self.stopped.emit()

    def stop(self):
        self._running = False
