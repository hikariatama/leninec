class Stack(list):
    """Stack class, subclass of list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def push(self, value):
        """Push a value to the stack."""
        self.append(value)

    def pop(self):
        """Pop a value from the stack."""
        return super().pop()

    def __repr__(self):
        return f"Stack({super().__repr__()})"

    def to_str(self):
        """
        Return a string representation of the stack.
        Example: 1|0|-5|1
        """
        return "|".join(map(str, self))

    @property
    def size(self):
        """Return the size of the stack."""
        return len(self)

    @property
    def is_empty(self):
        """Return True if the stack is empty."""
        return self.size == 0
