import io
import enum
import collections
from typing import *
import os.path


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
    def sanitize_piece(cls, piece: str) -> str:
        if "//" in piece:
            piece = piece.split("//")[0]
        return piece.strip()

    @classmethod
    def build(cls, pieces: List[str]) -> "Command":
        # remove whitespace and comments
        pieces = [cls.sanitize_piece(p) for p in pieces]

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
        elif op == "label":
            command = CommandType.LABEL
            arg1 = pieces[1]
        elif op == "goto":
            command = CommandType.GOTO
            arg1 = pieces[1]
        elif op == "if-goto":
            command = CommandType.IF
            arg1 = pieces[1]
        elif op == "call":
            command = CommandType.CALL
            arg1 = pieces[1]
            arg2 = int(pieces[2])
        elif op == "function":
            command = CommandType.FUNCTION
            arg1 = pieces[1]
            arg2 = int(pieces[2])
        elif op == "return":
            command = CommandType.RETURN
        else:
            raise NotImplementedError(op)
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
    """Builder class that allows to build assembly code via human-friendly interface.
    """

    def __init__(self):
        self.lines = []
    
    def append(self, text: str):
        """append a line of assembly code
        """
        self.lines.append(text)
    
    def comment(self, cmt: str):
        self.append("//" + cmt)

    def build(self) -> str:
        return "\n".join(self.lines) + "\n"

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
    
    def mov_mi(self, l: str, i: int):
        """memory from immediate: MEM[l] = i
        """
        self.append(f"@{i}")
        self.append("D=A")
        self.append(f"@{l}")
        self.append("M=D")
    
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
    
    def mov_mm(self, l: str, r: str):
        """MEM[l] = MEM[r]
        """
        self.append(f"@{r}")
        self.append(f"D=M")
        self.append(f"@{l}")
        self.append(f"M=D")
    
    def label(self, label: str):
        """set a label
        """
        self.append(f"({label})")

    def goto(self, label: str):
        """unconditional jump to a label
        """
        self.append(f"@{label}")
        self.append("0;JMP")

    def goto_m(self, addr: str):
        """unconditional jump to a value in memory
        """
        self.append(f"@{addr}")
        self.append("A=M")
        self.append("0;JMP")

    def goto_if(self, register: str, cond: str, label: str):
        """conditional jump to a label

        cond = EQ, NE, LT, GT, LE, GE
        """
        self.append(f"@{label}")
        self.append(f"{register};J{cond.upper()}")


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
        self.namespace: str = ""
    
    def set_namespace(self, namespace: str):
        self.namespace = namespace
    
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
                return self._push_static(self.namespace, index)
            elif command == CommandType.POP:
                return self._pop_static(self.namespace, index)
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
    def _logical_binary_arithmetic(cls, cond: str, prefix: str) -> str:
        """if arg1-arg2 satisfies the given condition, push -1 (true) otherwise 0 (false)
        """
        cond = cond.upper()
        NOT_COND = {
            "GT": "LE",
            "EQ": "NE",
            "LT": "GE",
        }
        not_cond = NOT_COND[cond]
        prefix = prefix + "." + cond
        else_label = f"{prefix}.ELSE"
        end_label = f"{prefix}.END"

        builder = CodeBuilder()
        # pop twice 
        builder.dec("SP")
        builder.mov_rp("D", "SP")
        builder.dec("SP")
        builder.mov_rp("A", "SP")
        # jump to else-statement
        builder.append("D=A-D")
        builder.goto_if("D", not_cond, f"{else_label}")
        # start if-statement
        builder.append("D=-1")  # true
        builder.goto(end_label)
        # start else-statement
        builder.label(else_label)
        builder.append("D=0")   # false
        # push the result
        builder.label(end_label)
        builder.mov_pr("SP", "D")
        builder.inc("SP")
        return builder.build()

    @classmethod
    def _arithmetic(cls, op: str, prefix) -> str:
        # unary operations
        if op == "neg":
            return cls._simple_unary_arithmetic("D=-D")
        elif op == "not":
            return cls._simple_unary_arithmetic("D=!D")
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
                return cls._logical_binary_arithmetic("EQ", prefix)
            elif op == "gt":
                return cls._logical_binary_arithmetic("GT", prefix)
            elif op == "lt":
                return cls._logical_binary_arithmetic("LT", prefix)

        return "// %s NOT IMPLEMENTED\n" % (op)

    def write_arithmetic(self, op: str):
        comment = f"// {op}\n"
        prefix = f"{self.namespace}.{self.count}"
        code = self._arithmetic(op, prefix)
        self.f.write(comment + code)
        self.count += 1
    
    def _get_prefixed_label(self, label: str) -> str:
        """returns prefixed label to make it unique
        """
        return f"{self.namespace}.{label}"
    
    def write_label(self, label: str):
        """label
        """
        comment = f"// label {label}\n"
        label = self._get_prefixed_label(label)
        builder = CodeBuilder()
        builder.label(label)
        code = builder.build()
        self.f.write(comment + code)
        self.count += 1
    
    def write_if(self, label: str):
        """conditional jump
        """
        comment = f"// goto-if {label}\n"
        label = self._get_prefixed_label(label)
        builder = CodeBuilder()
        # pop
        builder.dec("SP")
        builder.mov_rp("D", "SP")
        builder.goto_if("D", "NE", label)
        code = builder.build()
        self.f.write(comment + code)
        self.count += 1
    
    def write_goto(self, label: str):
        """unconditional jump
        """
        label = self._get_prefixed_label(label)
        builder = CodeBuilder()
        builder.comment(f"goto {label}")
        builder.goto(label)
        code = builder.build()
        self.f.write(code)
        self.count += 1
    
    def write_functions(self, function: str, nvars: int):
        builder = CodeBuilder()
        builder.comment(f"function {function} {nvars}")
        # declare label
        builder.label(function)
        # allocate local variables onto the stack
        for _ in range(nvars):
            builder.mov_pi("SP", 0)
            builder.inc("SP")
        code = builder.build()
        self.f.write(code)
        self.count += 1
    
    def write_return(self):
        builder = CodeBuilder()
        builder.comment("return")

        # TODO use R13-R15 for temporal values
        FRAME = "13"
        RETADDR = "14"

        builder.mov_mm(FRAME, "LCL")
        # return address
        builder.sub_mi(FRAME, 5)
        builder.mov_mp(RETADDR, FRAME)
        builder.add_mi(FRAME, 5)
        # *ARG = pop()
        # set *ARG to return value
        builder.dec("SP")
        builder.mov_pp("ARG", "SP")
        # SP = ARG+1
        builder.mov_mm("SP", "ARG")
        builder.add_mi("SP", 1)
        # restore stack frame
        for segment in ["THAT", "THIS", "ARG", "LCL"]:
            builder.sub_mi(FRAME, 1)
            builder.mov_mp(segment, FRAME)
        # goto retAddr = *(LCL-5)
        builder.goto_m(RETADDR)

        code = builder.build()
        self.f.write(code)
        self.count += 1
    
    def write_call(self, function: str, nargs: int):
        return_address = f"{self.namespace}.{function}.{self.count}"

        builder = CodeBuilder()
        builder.comment(f"call {function} {nargs}")
        # push returnAddress
        builder.mov_pi("SP", return_address)
        builder.inc("SP")
        # save current stack frame
        for segment in ["LCL", "ARG", "THIS", "THAT"]:
            builder.mov_pm("SP", segment)
            builder.inc("SP")
        # ARG = SP-5-nargs
        builder.mov_mm("ARG", "SP")
        builder.sub_mi("ARG", 5+nargs)
        # LCL = SP
        builder.mov_mm("LCL", "SP")
        # goto function
        builder.goto(function)
        # declare return address
        builder.label(return_address)

        code = builder.build()
        self.f.write(code)
        self.count += 1
    
    def write_init(self):
        builder = CodeBuilder()
        builder.mov_mi("SP", 256)
        code = builder.build()
        self.f.write(code)
        self.write_call("Sys.init", 0)

    def close(self):
        self.f.close()


class Main:

    def __init__(self, input_path: str):
        import glob

        # input
        self.input_path = input_path
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(self.input_path)
        if input_path.endswith(".vm"):
            self.input_files = [input_path]
            self.is_directory = False
        else:
            self.input_files = list(glob.glob(os.path.join(input_path, "*.vm")))
            self.is_directory = True

    @classmethod
    def get_namespace(cls, input_filename: str) -> str:
        basename = os.path.basename(input_filename)
        namespace = os.path.splitext(basename)[0]
        return namespace
    
    def translate(self):
        if self.is_directory:
            basename = os.path.basename(self.input_path.rstrip(os.path.sep))
            output_filename = os.path.join(self.input_path, basename + ".asm")
        else:
            output_filename = self.input_path.replace(".vm", ".asm")
        output_file = open(output_filename, "w")
        writer = CodeWriter(output_file)

        if self.is_directory:
            writer.write_init()

        for input_filename in self.input_files:
            input_file = open(input_filename, "r")
            parser = Parser(input_file)
            namespace = self.get_namespace(input_filename)
            writer.set_namespace(namespace)

            print("Input: " + input_filename)
            
            # main loop
            while True:
                parser.advance()
                if not parser.has_more_commands():
                    break
                cmd = parser.get_current_command()
                if cmd.command == CommandType.PUSH or cmd.command == CommandType.POP:
                    writer.write_pushpop(cmd.command, cmd.arg1, cmd.arg2)
                elif cmd.command == CommandType.ARITHMETIC:
                    writer.write_arithmetic(cmd.op)
                elif cmd.command == CommandType.LABEL:
                    writer.write_label(cmd.arg1)
                elif cmd.command == CommandType.IF:
                    writer.write_if(cmd.arg1)
                elif cmd.command == CommandType.GOTO:
                    writer.write_goto(cmd.arg1)
                elif cmd.command == CommandType.FUNCTION:
                    writer.write_functions(cmd.arg1, cmd.arg2)
                elif cmd.command == CommandType.RETURN:
                    writer.write_return()
                elif cmd.command == CommandType.CALL:
                    writer.write_call(cmd.arg1, cmd.arg2)
                else:
                    raise NotImplementedError
        writer.close()
        print("Output: " + output_filename)
    
    @staticmethod
    def main():
        import sys
        this = Main(sys.argv[1])
        this.translate()


if __name__ == "__main__":
    Main.main()
