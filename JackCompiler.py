from ParseTree import ParseTreeBuilder
from CompilationEngine import CompilationEngine
from JackTokenizer import JackTokenizer
from VMWriter import VMWriter


def main():
    import sys
    import os.path
    import glob
    input_path = sys.argv[1]
    if os.path.isdir(input_path):
        input_files = glob.glob(os.path.join(input_path, "*.jack"))
    elif input_path.endswith(".jack"):
        input_files = [input_path]
    else:
        raise ValueError("input is not a jack file")

    for input_filename in input_files:
        input_file = open(input_filename, "r")
        tokenizer = JackTokenizer(input_file)
        print(f"Compiling {input_filename}")

        # parse the input
        tree_builder = ParseTreeBuilder(tokenizer)
        tree = tree_builder.build()

        # compile
        output_filename = input_filename.replace(".jack", ".vm")
        output_file = open(output_filename, "w")
        writer = VMWriter(output_file)

        compiler = CompilationEngine(writer)
        compiler.compile_class(tree)

        input_file.close()
        output_file.close()

        print(f"Saved {input_filename}")


if __name__ == "__main__":
    main()
