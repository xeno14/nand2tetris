from constants import Segment, ArithmeticCommand


class VMWriter:

    def __init__(self, f):
        self.f = f
    
    def writeln(self, s: str):
        self.f.write(s)
        self.f.write("\n")
    
    def write_push(self, segment: Segment, index: int):
        self.writeln(f"push {segment.value} {index}")
    
    def write_pop(self, segment: Segment, index: int):
        self.writeln(f"pop {segment.value} {index}")
    
    def write_arithmetic(self, arithmetic: ArithmeticCommand):
        self.writeln(f"{arithmetic.value}")
    
    def write_label(self, label: str):
        self.writeln(f"label {label}")
    
    def write_goto(self, label: str):
        self.writeln(f"goto {label}")
    
    def write_if(self, label: str):
        self.writeln(f"if-goto {label}")
    
    def write_call(self, name: str, nargs: int):
        self.writeln(f"call {name} {nargs}")
    
    def write_functions(self, name: str, nlocals: int):
        self.writeln(f"function {name} {nlocals}")
    
    def write_return(self):
        self.writeln(f"return")
    
    def close(self):
        self.close()


def _test():
    import sys
    writer = VMWriter(sys.stdout)
    writer.write_functions("Main.main", 0)
    # String.new(2)
    writer.write_push(Segment.CONSTANT, 2)
    writer.write_call("String.new", 1)
    writer.write_push(Segment.CONSTANT, 72)
    writer.write_call("String.appendChar", 2)
    writer.write_push(Segment.CONSTANT, 73)
    writer.write_call("String.appendChar", 2)
    writer.write_call("Output.printString", 1)
    # discards return value
    writer.write_pop(Segment.TEMP, 0)
    # push dummy return value
    writer.write_push(Segment.CONSTANT, 0)
    writer.write_return()



if __name__ == "__main__":
    _test()
    
