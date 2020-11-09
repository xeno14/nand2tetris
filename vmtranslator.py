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
    # D...arg1 M...arg2
    BINARY_OP_TEMPLATE = """
@SP
M=M-1
A=M
D=M
@SP
M=M-1
A=M
{}
@SP
M=M+1
"""

    SEGMENT_POINTERS  = {
        "local": "LCL",
        "argument": "ARG",
        "this": "THIS",
        "that": "THAT",
    }

    TEMP_OFFSET = 5

    def __init__(self, f):
        self.f = f
    
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
    def _pushpop(cls, command: CommandType, segment: str, index: int):
        register = cls.SEGMENT_POINTERS.get(segment, None)
        if register:
            if command == CommandType.PUSH:
                return cls._push(register, index)
            elif command == CommandType.POP:
                return cls._pop(register, index)
        elif segment == "temp":
            if command == CommandType.PUSH:
                return cls._push_temp(index)
            elif command == CommandType.POP:
                return cls._pop_temp(index)
        elif segment == "constant" and command == CommandType.PUSH:
            return cls._push_constant(index)
        # TODO static
        # TODO pointer

        return "// %s %s %d NOT IMPLEMENTED \n" % (command, segment, index)

    def write_pushpop(self, command: CommandType, segment: str, index: int):
        comment = f"// {command.name} {segment} {index}\n"
        code = self._pushpop(command, segment, index)
        self.f.write(comment + code + "\n")

    @classmethod
    def _binary_arithmetic(cls, *operations) -> str:
        cmd = "\n".join(operations)
        return cls.BINARY_OP_TEMPLATE.format(cmd)

    @classmethod
    def _arithmetic(cls, op: str) -> str:
        if op in cls.BINARY_OPERATORS:
            # D...arg1, M...arg2
            if op == "add":
                return cls._binary_arithmetic("M=M+D")
            elif op == "sub":
                return cls._binary_arithmetic("M=M-D")
            elif op == "eq":
                # x=y
                # <=> x-y=0
                # <=> !(x-y != 0)
                # <=> !((x-y) | 0)
                return cls._binary_arithmetic(
                    "D=M-D",
                    "D=D|0",
                    "M=!D"
                    )
            elif op == "gt":
                pass
            # eq gt lt
            elif op == "and":
                return cls._binary_arithmetic("M=M&D")
            elif op == "or":
                return cls._binary_arithmetic("M=M|D")

        # unary operations
        elif op == "neg":
            pass
        elif op == "not":
            pass

        return "// %s NOT IMPLEMENTED\n" % (op)

    def write_arithmetic(self, op: str):
        comment = f"// {op}\n"
        code = self._arithmetic(op)
        self.f.write(comment + code)

    
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