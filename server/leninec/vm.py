import asyncio
import logging
import time
import typing
from collections import deque

from .errors import (
    CodeTooBigError,
    InvalidArgError,
    InvalidInstructionError,
    InvalidLabelError,
    InvalidMacroError,
    LabelRedefinitionError,
    MacroRedefinitionError,
    PopFromEmptyStackError,
    StackOverflowError,
    TimeoutExceededError,
    UndefinedLabelError,
    UndefinedMacroError,
    ValueOverflowError,
    VMSyntaxError,
)
from .registers import Registers
from .stack import Stack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Original idea behing this interpreter belongs to UgraCTF
# organizers. It was re-implemented from scratch by me.


class VM:
    MAX_STACK_SIZE: int = 1000
    MAX_VALUE: int = 2**31
    MAX_CODE_SIZE: int = 2048
    VALID_NUMBERS: set = set(map(str, range(-999, 1000)))

    def __init__(self):
        self._position_change_hooks: typing.List[callable] = []
        self._registers_change_hooks: typing.List[callable] = []
        self._stack_change_hooks: typing.List[callable] = []
        self._labels: dict = {}

        self.instructions: list = []
        self.registers: Registers = None
        self.stack: Stack = None
        self.delay: float = 0.15

    def add_position_change_hook(self, hook: callable):
        """
        Add hook that is called when VM position changes.
        Hook needs to accept one argument - new position.
        """
        self._position_change_hooks.append(hook)

    def remove_position_change_hook(self, hook: callable):
        """Remove hook that is called when VM position changes."""
        self._position_change_hooks.remove(hook)

    def add_registers_change_hook(self, hook: callable):
        """
        Add hook that is called when VM registers change.
        Hook needs to accept one argument - new registers.
        """
        self._registers_change_hooks.append(hook)

    def remove_registers_change_hook(self, hook: callable):
        """Remove hook that is called when VM registers change."""
        self._registers_change_hooks.remove(hook)

    def add_stack_change_hook(self, hook: callable):
        """
        Add hook that is called when VM stack changes.
        Hook needs to accept one argument - new stack.
        """
        self._stack_change_hooks.append(hook)

    def remove_stack_change_hook(self, hook: callable):
        """Remove hook that is called when VM stack changes."""
        self._stack_change_hooks.remove(hook)

    def on_position_change(self, func: callable):
        """Decorator for adding position change hook."""
        self.add_position_change_hook(func)
        return func

    def on_register_change(self, func: callable):
        """Decorator for adding register change hook."""
        self.add_registers_change_hook(func)
        return func

    def on_stack_change(self, func: callable):
        """Decorator for adding stack change hook."""
        self.add_stack_change_hook(func)
        return func

    def update_code(self, code: str):
        """Update VM code. Resets VM state to initial values."""
        self.reset_state()
        self._compile(code)

    def reset_state(self):
        """Reset VM state to initial values."""
        self.stack = Stack()
        self.registers = Registers("abcd")

    def check_state(self) -> bool:
        if self.stack.size > self.MAX_STACK_SIZE:
            raise StackOverflowError(f"Stack size exceeded {self.MAX_STACK_SIZE}")

        if any(abs(v) > self.MAX_VALUE for v in self.registers.values()):
            raise ValueOverflowError(f"Value exceeded {self.MAX_VALUE}")

        return True

    async def run(self, timeout: int = 300):
        """Run VM code. If timeout is specified, raises TimeoutExceededError"""
        if not self.instructions:
            return

        CONDITIONAL_JUMPS = {
            "je": lambda a: self.registers[a] == 0,
            "jg": lambda a: self.registers[a] > 0,
            "jl": lambda a: self.registers[a] < 0,
        }

        pos = 0
        start = time.perf_counter()
        while self.check_state() and pos < len(self.instructions):
            cmd, *args = self.instructions[pos]
            if cmd in self.registers.AVAILABLE_INSTRUCTIONS:
                self.registers.execute(cmd, *args)
                for hook in self._registers_change_hooks:
                    await hook(self.registers)

            if cmd in CONDITIONAL_JUMPS:
                a, b = args
                if CONDITIONAL_JUMPS[cmd](a):
                    b = b[1:-1]
                    pos = self._labels[b] - 1
                    for hook in self._position_change_hooks:
                        await hook(pos)
            elif cmd == "jmp":
                (a,) = args
                a = a[1:-1]
                pos = self._labels[a] - 1
                for hook in self._position_change_hooks:
                    await hook(pos)
            elif cmd == "pop":
                (a,) = args
                if self.stack.is_empty:
                    raise PopFromEmptyStackError("Cannot pop from empty stack")

                self.registers[a] = self.stack.pop()
                for hook in self._stack_change_hooks:
                    await hook(self.stack)

                for hook in self._registers_change_hooks:
                    await hook(self.registers)

            elif cmd == "push":
                (a,) = args
                self.stack.push(self.registers[a])
                for hook in self._stack_change_hooks:
                    await hook(self.stack)

            if timeout and time.perf_counter() - start > timeout:
                raise TimeoutExceededError(f"Timeout of {timeout} seconds exceeded")

            pos += 1
            for hook in self._position_change_hooks:
                await hook(pos)

            if self.delay:
                await asyncio.sleep(self.delay)

    def _check_reg(self, arg: str) -> bool:
        """
        Check if arg is a valid register
        :param arg: argument to check
        :return: True if arg is a valid register, False otherwise
        """
        return arg in self.registers

    def _check_num(self, arg: str) -> bool:
        """
        Check if arg is a valid number
        :param arg: argument to check
        :return: True if arg is a valid number, False otherwise
        """
        return arg in self.VALID_NUMBERS

    def _check_reg_or_num(self, arg: str) -> bool:
        """
        Check if arg is a valid register or number
        :param arg: argument to check
        :return: True if arg is a valid register or number, False otherwise
        """
        return self._check_reg(arg) or self._check_num(arg)

    def _check_label(self, arg: str) -> bool:
        """
        Check if arg is a valid label
        :param arg: argument to check
        :return: True if arg is a valid label, False otherwise
        """
        return arg[0] == arg[-1] == '"'

    def _compile(self, code: str):
        """
        Compile code to instructions
        :param code: code to compile
        :return: None
        """

        def process_conditional_jump(cmd: str, a: str, b: str):
            nonlocal used_labels
            b = b[1:-1]
            used_labels.add(b)
            self.instructions.append((cmd, a, b))
            self._labels[b] = len(self.instructions)

        def process_basic_jump(cmd: str, a: str):
            nonlocal used_labels
            a = a[1:-1]
            used_labels.add(a)
            self.instructions.append((cmd, a, None))
            self._labels[a] = len(self.instructions)

        SCHEMA = {
            "add": {"mask": (self._check_reg, self._check_reg_or_num)},
            "sub": {"mask": (self._check_reg, self._check_reg_or_num)},
            "mul": {"mask": (self._check_reg, self._check_reg_or_num)},
            "div": {"mask": (self._check_reg, self._check_reg_or_num)},
            "mod": {"mask": (self._check_reg, self._check_reg_or_num)},
            "pop": {"mask": (self._check_reg,)},
            "push": {"mask": (self._check_reg_or_num,)},
            "mov": {"mask": (self._check_reg, self._check_reg_or_num)},
            "je": {
                "mask": (self._check_reg, self._check_label),
                "custom_hook": process_conditional_jump,
            },
            "jg": {
                "mask": (self._check_reg, self._check_label),
                "custom_hook": process_conditional_jump,
            },
            "jl": {
                "mask": (self._check_reg, self._check_label),
                "custom_hook": process_conditional_jump,
            },
            "jmp": {
                "mask": (self._check_label,),
                "custom_hook": process_basic_jump,
            },
        }

        self._labels = {}
        self.instructions = []

        defines = {}
        defines_count = {}
        used_labels = set()

        lines = deque(line.strip() for line in code.splitlines())
        while lines:
            if len(self.instructions) > self.MAX_CODE_SIZE:
                raise CodeTooBigError(
                    f"Code size is {len(self.instructions)} while max is"
                    f" {self.MAX_CODE_SIZE}"
                )

            line = lines.popleft().lower().strip()
            if not line or line.startswith("//"):
                continue

            if line.endswith("!"):  # Call macro
                name = line[:-1]
                if not (content := defines.get(name)):
                    raise UndefinedMacroError(f"Macro {name} is not defined")

                label_prefix = f"{name}-{defines_count[name]}#"
                for line_ in content:
                    if line_.endswith(":"):
                        line_ = label_prefix + line_
                    elif "{}" in line_:
                        if line_.count("{}") > 1:
                            raise InvalidMacroError("Too many '{}' in macro")

                        line_ = line_.format(label_prefix)

                    lines.appendleft(line_)

                defines_count[name] += 1
            elif line.startswith("#define"):  # Define macro
                line = line.split()
                if len(line) != 2:
                    raise InvalidMacroError(f"Invalid macro definition: {line}")

                name = line[1]
                if name in defines:
                    raise MacroRedefinitionError(f"Macro {name} is already defined")

                content = []
                while lines:
                    n = lines.popleft()
                    if n == "#enddefine":
                        break

                    if n == f"{name}!":
                        raise VMSyntaxError("Recursive macro call detected")

                    content.append(n)

                defines[name] = list(reversed(content))
                defines_count[name] = 0
            elif line == "#enddefine":  # End macro definition
                raise VMSyntaxError("#enddefine used without #define")
            elif line.endswith(":"):  # Define label
                label = line[:-1]
                if len(label.split()) != 1:
                    raise InvalidLabelError()

                if label in self._labels:
                    raise LabelRedefinitionError(f"Label {label} is already defined")

                self._labels[label] = len(self.instructions)
            else:
                cmd, *args = line.split()
                if cmd not in SCHEMA:
                    raise InvalidInstructionError(f"Invalid instruction {cmd}")

                check = SCHEMA[cmd]["mask"]
                if len(args) != len(check):
                    raise InvalidArgError(f"Invalid number of arguments for {cmd}")

                for i, arg in enumerate(args):
                    if not check[i](arg):
                        raise InvalidArgError(f"Invalid argument {arg} for {cmd}")

                if "custom_hook" in check:
                    check["custom_hook"](cmd, *args)
                else:
                    self.instructions.append((cmd, *args))

        for label in used_labels:
            if label not in self._labels:
                raise UndefinedLabelError(f"Label {label} is not defined")
