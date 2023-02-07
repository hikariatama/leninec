import typing


class Registers(dict):
    AVAILABLE_INSTRUCTIONS: typing.List[str] = ["add", "div", "mov", "mul", "sub"]

    def __init__(self, registers: str):
        self.registers: str = registers  # skipcq: PTC-W0052
        super().__init__()
        for letter in registers:
            self[letter] = 0

    def __missing__(self, key: str):
        return int(key)

    def __contains__(self, key: str):
        return key in self.registers

    def execute(self, instruction: str, a: str, b: str):
        """
        Execute an instruction.
        :param instruction: Instruction to execute.
        :param a: First register.
        :param b: Second register.
        """
        if instruction not in self.AVAILABLE_INSTRUCTIONS:
            raise ValueError("Invalid instruction")

        getattr(self, instruction)(a, b)

    def add(self, a: str, b: str):
        """
        Add the value of register b to the value of register a.
        :param a: First register.
        :param b: Second register.
        """
        self[a] += self[b]

    def div(self, a: str, b: str):
        """
        Divide the value of register a by the value of register b.
        :param a: First register.
        :param b: Second register.
        """
        self[a] //= self[b]

    def mov(self, a: str, b: str):
        """
        Move value in register b to register a
        :param a: register to move value in
        :param b: register to get value from
        """
        self[a] = self[b]

    def mul(self, a: str, b: str):
        """
        Multiply register b by register a
        :param a: register to multiply
        :param b: register to multiply by
        """
        self[a] *= self[b]

    def sub(self, a: str, b: str):
        """
        Subtract register b from register a
        :param a: register to subtract from
        :param b: register to subtract
        """
        self[a] -= self[b]

    def to_str(self) -> str:
        """
        Return a string representation of the registers.
        Example: 1|0|-5|1
        """
        return "|".join(map(str, self.values()))
