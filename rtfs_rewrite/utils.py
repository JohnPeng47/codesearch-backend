class TextRange:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def __str__(self):
        return f"({self.start}, {self.end})"

    def to_range(self):
        return (self.start, self.end)

    def overlap(self, other: "TextRange"):
        return (other.start >= self.start and other.start <= self.end) or (
            other.end <= self.end and other.end >= self.start
        )
