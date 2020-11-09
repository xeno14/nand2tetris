import io
import enum
import collections
from typing import *


class CommandType(enum.Enum):

    ARITHMETIC = enum.auto(),
    PUSH = enum.auto(),
    POP = enum.auto(),
    LABEL = enum.auto(),
    GOTO = enum.auto(),
    IF = enum.auto(),
    FUNCTION = enum.auto(),
    RETURN = enum.auto(),
    CALL = enum.auto()


class Command(collections.namedtuple("Command", ["command", "op", "arg1", "arg2"])):

    ARITHMETIC_COMMANDS = set(
        ["add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"]
    )

    @classmethod
    def build(cls, pieces: List[str]) -> "Command":
        op = pieces[0]
        arg1, arg2 = None, None
        if op == "push":
            command = CommandType.PUSH
            arg1 = pieces[1]
            arg2 = int(pieces[2])
        elif op == "pop":
            command = CommandType.POP
            arg1 = pieces[1]
            arg2 = int(pieces[2])
        elif op in ["add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"]:
            command = CommandType.ARITHMETIC
        return Command(command, op, arg1, arg2)

    def __str__(self):
        arg1 = self.arg1 if self.arg1 else ""
        arg2 = self.arg2 if self.arg1 else ""
        return f"{self.command.name}\t{self.op} {arg1} {arg2}".strip()


class Parser:

    def __init__(self, f):
        self.f = f  # input file stream
        self.current_command = None
        self.eof = False

    def has_more_commands(self):
        return self.eof == False
    
    def advance(self):
        while self.has_more_commands():
            line = self.f.readline()
            self.eof = line == ""
            # break if EOF
            if self.eof:
                self.current_command = None
                break
            line = line.strip()
            # skip comment or empty line
            if line == "" or line.startswith("//"):
                continue

            # build current command
            pieces = line.split(" ")
            command = Command.build(pieces)
            self.current_command = command
            break

    def get_current_command(self):
        return self.current_command
    
    def close(self):
        self.f.close()


class CodeWriter(object):

    # predefined registers
    LOCAL_REGISTER = "local",
    ARGUMENT_REGISTER = "argument",
    THIS_REGISTER = "this",
    THAT_REGISTER = "that",
    TEMP_REGISTER = "temp",

    BINARY_OPERATORS = {
        "add", "sub", "eq", "gt", "lt", "and", "or"
    }

    SEGMENT_POINTERS  = {
        "local": "LCL",
        "argument": "ARG",
        "this": "THIS",
        "that": "THAT",
    }

    TEMP_OFFSET = 5

    def __init__(self, f):
        self.f = f
        self.count = 0
    
    @classmethod
    def _push(cls, register: str, index: int) -> str:
        """for local, argument, this, that
        """
        return f"""
@{register}
D=M
@{index}
A=D+A
D=M
@SP
A=M
M=D
@SP
M=M+1
"""

    @classmethod
    def _pop(cls, register: str, index: int) -> str:
        """for local, argument, this, that
        """
        return f"""
@{register}
D=M
@{index}
D=D+A
@{register}
M=D
@SP
M=M-1
A=M
D=M
@{register}
A=M
M=D
@{register}
D=M
@{index}
D=D-A
@{register}
M=D
"""

    @classmethod
    def _push_temp(cls, index: int) -> str:
        address = cls.TEMP_OFFSET + index
        return f"""
@{address}
D=M
@SP
A=M
M=D
@SP
M=M+1
"""

    @classmethod
    def _pop_temp(cls, index: int) -> str:
        address = cls.TEMP_OFFSET + index
        return f"""
@SP
M=M-1
A=M
D=M
@{address}
M=D
"""

    @classmethod
    def _push_constant(cls, value: int) -> str:
        return f"""
@{value}
D=A
@SP
A=M
M=D
@SP
M=M+1
"""

    @classmethod
    def _this_or_that(cls, index: int) -> str:
        ptr = "THIS" if index == 0 else "THAT" if index == 1 else None
        if ptr is None:
            raise RuntimeError(f"invalid index for pointer: {index}")
        return ptr

    @classmethod
    def _push_pointer(cls, index: int) -> str:
        ptr = cls._this_or_that(index)
        return f"""
@{ptr}
D=M
@SP
A=M
M=D
@SP
M=M+1
"""

    @classmethod
    def _pop_pointer(cls, index: int) -> str:
        ptr = cls._this_or_that(index)
        return f"""
@SP
M=M-1
A=M
D=M
@{ptr}
M=D
"""

    @classmethod
    def _push_static(cls, namespace: str, index: int) -> str:
        static = f"{namespace}.{index}"
        return f"""
@{static}
D=M
@SP
A=M
M=D
@SP
M=M+1
"""

    @classmethod
    def _pop_static(cls, namespace: str, index: int) -> str:
        static = f"{namespace}.{index}"
        return f"""
@SP
M=M-1
@SP
A=M
D=M
@{static}
M=D
"""

    def _pushpop(self, command: CommandType, segment: str, index: int):
        register = self.SEGMENT_POINTERS.get(segment, None)
        if register:
            if command == CommandType.PUSH:
                return self._push(register, index)
            elif command == CommandType.POP:
                return self._pop(register, index)
        elif segment == "temp":
            if command == CommandType.PUSH:
                return self._push_temp(index)
            elif command == CommandType.POP:
                return self._pop_temp(index)
        elif segment == "constant" and command == CommandType.PUSH:
            return self._push_constant(index)
        elif segment == "static":
            if command == CommandType.PUSH:
                return self._push_static("Foo", index)
            elif command == CommandType.POP:
                return self._pop_static("Foo", index)
        elif segment == "pointer":
            if command == CommandType.PUSH:
                return self._push_pointer(index)
            elif command == CommandType.POP:
                return self._pop_pointer(index)

        return "// %s %s %d NOT IMPLEMENTED \n" % (command, segment, index)

    def write_pushpop(self, command: CommandType, segment: str, index: int):
        comment = f"// {command.name} {segment} {index}\n"
        code = self._pushpop(command, segment, index)
        self.f.write(comment + code + "\n")

    @classmethod
    def _binary_arithmetic(cls, *operations) -> str:
        ops = "\n".join(operations)
        # D...arg1 M...arg2
        return f"""
@SP
M=M-1
A=M
D=M
@SP
M=M-1
A=M
{ops}
@SP
M=M+1
"""

    @classmethod
    def _unary_arithmetic(cls, *operations) -> str:
        ops = "\n".join(operations)
        # M ... arg
        return f"""
@SP
M=M-1
A=M
{ops}
@SP
M=M+1
"""

    @classmethod
    def _arithmetic(cls, op: str, count: int) -> str:
        if op in cls.BINARY_OPERATORS:
            # D...arg1, M...arg2
            if op == "add":
                return cls._binary_arithmetic("M=M+D")
            elif op == "sub":
                return cls._binary_arithmetic("M=M-D")
            elif op == "eq":
                return cls._binary_arithmetic(
                    f"""
D=M-D
@{count}.EQ.ELSE
D;JNE
D=-1
@{count}.EQ.END
0;JMP
({count}.EQ.ELSE)
D=0
({count}.EQ.END)
@SP
A=M
M=D
""".strip())
            elif op == "gt":
                return cls._binary_arithmetic(
                    f"""
D=M-D
@{count}.GT.ELSE
D;JLE
D=-1
@{count}.GT.END
0;JMP
({count}.GT.ELSE)
D=0
({count}.GT.END)
@SP
A=M
M=D
""".strip())
            elif op == "lt":
                return cls._binary_arithmetic(
                    f"""
D=M-D
@{count}.LT.ELSE
D;JGE
D=-1
@{count}.LT.END
0;JMP
({count}.LT.ELSE)
D=0
({count}.LT.END)
@SP
A=M
M=D
""".strip())
            elif op == "and":
                return cls._binary_arithmetic("M=M&D")
            elif op == "or":
                return cls._binary_arithmetic("M=M|D")
        # unary operations
        elif op == "neg":
            return cls._unary_arithmetic("M=-M")
        elif op == "not":
            return cls._unary_arithmetic("M=!M")

        return "// %s NOT IMPLEMENTED\n" % (op)

    def write_arithmetic(self, op: str):
        comment = f"// {op}\n"
        code = self._arithmetic(op, self.count)
        self.f.write(comment + code)
        self.count += 1

    
    def close(self):
        self.f.close()


def main():
    import sys
    import os.path

    # input and parser
    input_filename = sys.argv[1]
    input_file = open(input_filename, "r")
    parser = Parser(input_file)

    # output and writer
    basename = os.path.basename(input_filename)
    basename_wo_ext = os.path.splitext(basename)[0]
    output_filename = basename_wo_ext + ".asm"
    output_file = open(output_filename, "w")
    writer = CodeWriter(output_file)
    
    # main loop
    while True:
        parser.advance()
        if not parser.has_more_commands():
            break
        cmd = parser.get_current_command()
        print(cmd)
        if cmd.command == CommandType.PUSH or cmd.command == CommandType.POP:
            writer.write_pushpop(cmd.command, cmd.arg1, cmd.arg2)
        elif cmd.command == CommandType.ARITHMETIC:
            writer.write_arithmetic(cmd.op)
        else:
            raise NotImplementedError
    writer.close()


if __name__ == "__main__":
    main()