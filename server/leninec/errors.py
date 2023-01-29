class VMError(Exception):
    """Base class for all VM errors"""


class StackOverflowError(VMError):
    """Raised when stack size exceeds MAX_STACK_SIZE"""


class ValueOverflowError(VMError):
    """Raised when value exceeds MAX_VALUE"""


class InvalidInstructionError(VMError):
    """Raised when instruction is not valid"""


class InvalidMacroError(VMError):
    """Raised when macro is not valid"""


class TimeoutExceededError(VMError):
    """Raised when timeout is exceeded"""


class PopFromEmptyStackError(VMError):
    """Raised when trying to pop from empty stack"""


class CodeTooBigError(VMError):
    """Raised when code size exceeds MAX_CODE_SIZE"""


class UndefinedMacroError(VMError):
    """Raised when trying to use undefined macro"""


class MacroRedefinitionError(VMError):
    """Raised when trying to redefine macro"""


class VMSyntaxError(VMError):
    """Raised when VM code has syntax error"""


class InvalidLabelError(VMError):
    """Raised when label is not valid"""


class LabelRedefinitionError(VMError):
    """Raised when trying to redefine label"""


class InvalidArgError(VMError):
    """Raised when argument is not valid"""


class UndefinedLabelError(VMError):
    """Raised when trying to use undefined label"""
