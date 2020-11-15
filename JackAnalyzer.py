from CompilationEngine import ParseTreeBuilder
from JackTokenizer import JackTokenizer


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
        print(f"Analyzing {input_filename}")

        output_filename = input_filename.replace(".jack", ".xml")
        output_file = open(output_filename, "w")

        tree_builder = ParseTreeBuilder(tokenizer)
        tree = tree_builder.build()
        tree.to_xml(output_file)

        input_file.close()
        output_file.close()

        print(f"Saved {input_filename}")



if __name__ == "__main__":
    main()
