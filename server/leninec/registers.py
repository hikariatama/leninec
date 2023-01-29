class Registers(dict):
    AVAILABLE_INSTRUCTIONS = ["add", "div", "mov", "mul", "sub"]

    def __init__(self, registers):
        self.registers = registers
        super().__init__()
        for letter in registers:
            self[letter] = 0

    def __missing__(self, key):
        return int(key)

    def __contains__(self, key):
        return key in self.registers

    def execute(self, instruction: str, a: str, b: str):
        if instruction not in self.AVAILABLE_INSTRUCTIONS:
            raise ValueError("Invalid instruction")

        getattr(self, instruction)(a, b)

    def add(self, a: str, b: str):
        self[a] += self[b]

    def div(self, a: str, b: str):
        self[a] //= self[b]

    def mov(self, a: str, b: str):
        self[a] = self[b]

    def mul(self, a: str, b: str):
        self[a] *= self[b]

    def sub(self, a: str, b: str):
        self[a] -= self[b]

    def to_str(self) -> str:
        """
        Return a string representation of the registers.
        Example: 1|0|-5|1
        """
        return "|".join(map(str, self.values()))
