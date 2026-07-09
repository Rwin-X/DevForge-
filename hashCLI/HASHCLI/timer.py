import time


class Timer:

    def __init__(self):

        self.start = None
        self.end = None

    def __enter__(self):

        self.start = time.perf_counter()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.end = time.perf_counter()

    @property
    def elapsed(self):

        return self.end - self.start
