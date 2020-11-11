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

    ARITHMETIC_COMMANDS = {
        "add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"
    }

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
        elif op in cls.ARITHMETIC_COMMANDS:
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



class CodeBuilder(object):

    def __init__(self, count: int = 0):
        self.lines = []
        self.count = count
    
    def append(self, text: str):
        self.lines.append(text)
        # if not text.startswith("//") and not text.startswith("(") and not text.strip() == "":
        #     self.count += 1
    
    def comment(self, cmt: str):
        self.append("//" + cmt)

    def build(self) -> str:
        return "\n".join(self.lines)

    def inc(self, a: str):
        """MEM[a]++
        """
        self.append("@"+a)
        self.append("M=M+1")

    def dec(self, a: str):
        """MEM[a]--
        """
        self.append("@"+a)
        self.append("M=M-1")
    
    def add_mi(self, a: str, i: int):
        """add memory from immediate: MEM[a]=MEM[a] + i
        """
        self.append(f"@{a}")
        self.append(f"D=M")
        self.append(f"@{i}")
        self.append(f"D=D+A")
        self.append(f"@{a}")
        self.append(f"M=D")
    
    def sub_mi(self, a: str, i: int):
        """sum memory from immediate: D=MEM[a] - i
        """
        self.append(f"@{a}")
        self.append(f"D=M")
        self.append(f"@{i}")
        self.append(f"D=D-A")
        self.append(f"@{a}")
        self.append(f"M=D")
    
    def mov_pp(self, l: str, r:str):
        """pointer from pointer: *MEM[l]= *MEM[r]
        """
        self.append(f"@{r}")
        self.append(f"A=M")
        self.append(f"D=M")  # D=*MEM[r]
        self.append(f"@{l}")
        self.append(f"A=M")
        self.append(f"M=D")
    
    def mov_pm(self, l: str, r: str):
        """pointer from memory: *MEM[l] = MEM[r]
        """
        self.mov_rm("D", r)
        self.append(f"@{l}")
        self.append(f"A=M")
        self.append(f"M=D")

    def mov_mp(self, l: str, r: str):
        """memory from pointer: MEM[l] = *MEM[r]
        """
        self.mov_rp("D", r)
        self.append(f"@{l}")
        self.append(f"M=D")
    
    def mov_pi(self, l: str, i: int):
        """pointer from immediate: *MEM[l] = i
        """
        self.append(f"@{i}")
        self.append(f"D=A")
        self.append(f"@{l}")
        self.append(f"A=M")
        self.append(f"M=D")

    def mov_rp(self, l: str, r: str):
        """register = *MEM[r]
        """
        if l not in ["D", "A"]:
            raise ValueError(f"Invalid register {l}")
        self.append(f"@{r}")
        self.append(f"A=M")
        self.append(f"{l}=M")
    
    def mov_pr(self, l: str, r: str):
        """*MEM[r] = register
        """
        if r not in ["D", "A"]:
            raise ValueError(f"Invalid register {r}")
        if r == "A":
            # move value of A as it will be replaced later
            self.append(f"D=A")
        self.append(f"@{l}")
        self.append(f"A=M")
        self.append(f"M=D")

    def mov_rm(self, l: str, r: str):
        """register = MEM[r]
        """
        if l not in ["D", "A"]:
            raise ValueError(f"Invalid register {l}")
        self.append(f"@{r}")
        self.append(f"{l}=M")

    def mov_mr(self, l: str, r: str):
        """MEM[r] = register
        """
        if r not in ["D", "A"]:
            raise ValueError(f"Invalid register {r}")
        self.append(f"@{r}")
        self.append(f"M={l}")
    

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
    def _push(cls, segment: str, index: int) -> str:
        """for local, argument, this, that
        addr = segmentPointer + i; *SP = *addr; SP++
        """
        builder = CodeBuilder()
        builder.add_mi(segment, index)  # addr: MEM[segment] += index
        builder.mov_pp("SP", segment)   # *SP = *addr
        builder.inc("SP")               # SP++
        builder.sub_mi(segment, index)  # MEM[addr] -= index
        return builder.build()

    @classmethod
    def _pop(cls, segment: str, index: int) -> str:
        """for local, argument, this, that
        addr = segmentPointer + i;  SP--; *addr = *SP
        """
        builder = CodeBuilder()
        builder.add_mi(segment, index)  # addr: MEM[segment] += index
        builder.dec("SP")
        builder.mov_pp(segment, "SP")   # *SP = *addr
        builder.sub_mi(segment, index)  # MEM[addr] -= index
        return builder.build()

    @classmethod
    def _push_temp(cls, index: int) -> str:
        """addr = 5+i, *SP=*addr, SP++
        """
        address = cls.TEMP_OFFSET + index

        builder = CodeBuilder()
        builder.mov_pm("SP", address)
        builder.inc("SP")
        return builder.build()

    @classmethod
    def _pop_temp(cls, index: int) -> str:
        """addr = 5+i, *addr=*SP, SP--
        """
        address = cls.TEMP_OFFSET + index

        builder = CodeBuilder()
        builder.dec("SP")
        builder.mov_mp(address, "SP")
        return builder.build()

    @classmethod
    def _push_constant(cls, value: int) -> str:
        """*SP = i; SP++
        """
        builder = CodeBuilder()
        builder.mov_pi("SP", value)
        builder.inc("SP")
        return builder.build()

    @classmethod
    def _this_or_that(cls, index: int) -> str:
        ptr = "THIS" if index == 0 else "THAT" if index == 1 else None
        if ptr is None:
            raise RuntimeError(f"invalid index for pointer: {index}")
        return ptr

    @classmethod
    def _push_pointer(cls, index: int) -> str:
        """*SP = THIS/THAT, SP++
        """
        addr = cls._this_or_that(index)
        
        builder = CodeBuilder()
        builder.mov_pm("SP", addr)
        builder.inc("SP")
        return builder.build()

    @classmethod
    def _pop_pointer(cls, index: int) -> str:
        """SP--, THIS/THAT = *SP
        """
        addr = cls._this_or_that(index)
        
        builder = CodeBuilder()
        builder.dec("SP")
        builder.mov_mp(addr, "SP")
        return builder.build()

    @classmethod
    def _push_static(cls, namespace: str, index: int) -> str:
        static = f"{namespace}.{index}"

        builder = CodeBuilder()
        builder.mov_pm("SP", static)
        builder.inc("SP")
        return builder.build()

    @classmethod
    def _pop_static(cls, namespace: str, index: int) -> str:
        static = f"{namespace}.{index}"

        builder = CodeBuilder()
        builder.dec("SP")
        builder.mov_mp(static, "SP")
        return builder.build()

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
    def _simple_binary_arithmetic(cls, expr: str) -> str:
        """apply simple binary arithmetic that ALU can execute.

        A = arg1, D = arg2
        """
        builder = CodeBuilder()
        # pop twice 
        builder.dec("SP")
        builder.mov_rp("D", "SP")
        builder.dec("SP")
        builder.mov_rp("A", "SP")
        # apply expr
        builder.append(expr)
        # push the result
        builder.mov_pr("SP", "D")
        builder.inc("SP")
        return builder.build()

    @classmethod
    def _simple_unary_arithmetic(cls, expr: str) -> str:
        """apply simple unary arithmetic that ALU can execute.

        D = arg1
        """
        builder = CodeBuilder()
        # pop
        builder.dec("SP")
        builder.mov_rp("D", "SP")
        # apply expr
        builder.append(expr)
        # push
        builder.mov_pr("SP", "D")
        builder.inc("SP")
        return builder.build()
    
    @classmethod
    def _binary_arithmetic(cls, *operations) -> CodeBuilder:
        """D=arg1, A=arg2 
        """
        # TODO remove me later
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
        builder = CodeBuilder(count)
        # unary operations
        if op == "neg":
            return cls._simple_binary_arithmetic("D=-D")
        elif op == "not":
            return cls._simple_binary_arithmetic("D=!D")
        # binary operations
        elif op in cls.BINARY_OPERATORS:
            # A...arg1, D...arg2
            if op == "add":
                return cls._simple_binary_arithmetic("D=A+D")
            elif op == "sub":
                return cls._simple_binary_arithmetic("D=A-D")
            elif op == "and":
                return cls._simple_binary_arithmetic("D=A&D")
            elif op == "or":
                return cls._simple_binary_arithmetic("D=A|D")
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

    # input and parser
    input_filename = sys.argv[1]
    input_file = open(input_filename, "r")
    parser = Parser(input_file)

    # output and writer
    output_filename = input_filename.replace(".vm", ".asm")
    output_file = open(output_filename, "w")
    writer = CodeWriter(output_file)

    print("Input: " + input_filename)
    print("Output: " + output_filename)
    
    # main loop
    while True:
        parser.advance()
        if not parser.has_more_commands():
            break
        cmd = parser.get_current_command()
        # print(cmd)
        if cmd.command == CommandType.PUSH or cmd.command == CommandType.POP:
            writer.write_pushpop(cmd.command, cmd.arg1, cmd.arg2)
        elif cmd.command == CommandType.ARITHMETIC:
            writer.write_arithmetic(cmd.op)
        else:
            raise NotImplementedError
    writer.close()


if __name__ == "__main__":
    main()
