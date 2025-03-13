

class IntCounter:
    def __init__(self, start: int = 0, step: int = 1) -> None:
        self.n = self.start = start
        self.step = step

    def next(self) -> int:
        ret = self.n
        self.n += self.step
        return ret
    
    def __call__(self) -> int:
        return self.next()

    def reset(self) -> None:
        self.n = self.start

