from typing import List, Tuple
from enum import Enum


class SymbolTable(object):

    def __init__(self):
        self.symbols = {
            # predefined symbols
            "SCREEN": 16384,
            "KBD": 24576,
            "SP": 0,
            "LCL": 1,
            "ARG": 2,
            "THIS": 3,
            "THAT": 4,
        }
        # registers
        for i in range(16):
            self.symbols["R%d" % i] = i

        self.variable_address = 16

    def add_symbol(self, symbol: str, line: int):
        # don't overwrite
        if symbol in self.symbols:
            return
        self.symbols[symbol] = line

    def resolve(self, symbol: str) -> int:
        """look up the symbol table and returns the corresponding line.
        if the symbol is missing in the current table, assume the symbol as a variable and add it to the table.
        returns the number if the given symbol is a number.
        """
        if symbol.isdigit():
            return int(symbol)
        if symbol not in self.symbols:
            self.add_symbol(symbol, self.variable_address)
            self.variable_address += 1
        return self.symbols[symbol]


def sanitize_line(line: str) -> str:
    if "//" in line:
        line = line.split("//")[0]
    line = line.strip()
    return line


def preprocess(lines: List[str]) -> List[str]:
    """Resolve all the symbols in A-instruction.
    """
    preprocessed = []    
    table = SymbolTable()
    line_count = 0

    # first pass - find loop declarations
    for line in lines:
        line = sanitize_line(line)
        # skip empty line
        if line == "":
            continue
        
        # is loop declaration?
        if line.startswith("(") and line.endswith(")"):
            table.add_symbol(line[1:-1], line_count)
        else:
            preprocessed.append(line)
            line_count += 1

    # second pass - resolve symbols
    for i, line in enumerate(preprocessed):
        # skip if not A-instuction
        if not line.startswith("@"):
            continue
        symbol = line[1:]
        address = table.resolve(symbol)
        new_line = "@" + str(address)
        preprocessed[i] = new_line

    return preprocessed


class CInstruction(object):

    def __init__(self, dest: str, comp: str, jump: str):
        self.dest = dest
        self.comp = comp
        self.jump = jump
    
    @staticmethod
    def parse(expr: str) -> "CInstruction":
        # parse jump
        jump = ""    
        if ";" in expr:
            [expr, jump] = expr.split(";")
        
        # parse destination
        dest = ""
        if "=" in expr:
            [dest, expr] = expr.split("=")
        
        comp = expr
        return CInstruction(dest, comp, jump)


class Code(object):
    """compile C instruction
    """

    COMP_C_CODE = {
        "0":    "101010",
        "1":    "111111",
        "-1":   "111010",
        "D":    "001100",
        "A":    "110000",
        "M":    "110000",
        "!D":   "001101",
        "!A":   "110001",
        "!M":   "110001",
        "-D":   "001111",
        "-A":   "110011",
        "-M":   "110011",
        "D+1":  "011111",
        "A+1":  "110111",
        "M+1":  "110111",
        "D-1":  "001110",
        "A-1":  "110010",
        "M-1":  "110010",
        "D+A":  "000010",
        "D+M":  "000010",
        "D-A":  "010011",
        "D-M":  "010011",
        "A-D":  "000111",
        "M-D":  "000111",
        "D&A":  "000000",
        "D&M":  "000000",
        "D|A":  "010101",
        "D|M":  "010101",
    }

    JUMP_CODE = {
        "": "000",
        "JGT": "001",
        "JEQ": "010",
        "JGE": "011",
        "JLT": "100",
        "JNE": "101",
        "JLE": "110",
        "JMP": "111",
    }

    @classmethod
    def comp(cls, comp: str) -> str:
        a = "1" if "M" in comp else "0"
        cc = cls.COMP_C_CODE[comp]
        return a + cc

    @classmethod
    def dest(cls, dest: str) -> str:
        d1 = "1" if "A" in dest else "0"
        d2 = "1" if "D" in dest else "0"
        d3 = "1" if "M" in dest else "0"
        return d1 + d2 + d3
    
    @classmethod
    def jump(cls, jump: str) -> str:
        return cls.JUMP_CODE[jump]

    @classmethod
    def compile(cls, comp: str, dest: str, jump: str) -> str:
        cc = cls.comp(comp)
        dd = cls.dest(dest)
        jj = cls.jump(jump)
        return "111" + cc + dd + jj


def compile(lines: List[str]) -> List[str]:
    """Precondition: lines are preprocessed (no empty line, no symbols, not comments)
    """
    compiled = []
    for line in lines:
        if line.startswith("@"):
            val = int(line[1:])
            code = "0{:0>15b}".format(val)
            compiled.append(code)
        else:
            cinst = CInstruction.parse(line)
            code = Code.compile(cinst.comp, cinst.dest, cinst.jump)
            compiled.append(code)
    return compiled


def main():
    # test preprocess
    import sys
    filename = sys.argv[1]
    with open(filename) as f:
        lines = f.readlines()
    preprocessed = preprocess(lines)

    print("----- PREPROCESSED -----")
    print("\n".join(preprocessed))
    print()

    compiled = compile(preprocessed)

    print("----- COMPILED -----")
    print("\n".join(compiled))

    import os.path
    basename = os.path.basename(filename)
    basename_wo_ext = os.path.splitext(basename)[0]
    compined_filename = basename_wo_ext + ".hack"
    with open(compined_filename, "w") as f:
        f.write("\n".join(compiled))


if __name__ == "__main__":
    main()