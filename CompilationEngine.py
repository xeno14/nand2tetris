from ParseTree import TreeNode, TreeNodeIterator
from VMWriter import VMWriter
from constants import *
from SymbolTable import SymbolTable

from typing import *


class Helper:

    @classmethod
    def is_token(self, node: TreeNode, expected_token_type: TokenType, expected_token: str=None) -> bool:
        type_ok = node.token_type == expected_token_type
        if expected_token is None:
            return type_ok
        else:
            return type_ok and expected_token == node.token

    @classmethod
    def is_keyword(cls, node: TreeNode, expected: Keyword=None) -> bool:
        type_ok = node.token_type == TokenType.KEYWORD
        if expected is None:
            return type_ok
        else:
            return type_ok and expected.is_same(node.name)
        
    @classmethod
    def is_nonterminal(cls, node: TreeNode, expected: NonTerminalType=None) -> bool:
        if expected is None:
            return not node.is_terminal()
        else:
            return not node.is_terminal() and expected.is_same(node.name)
    
    @classmethod
    def is_symbol(cls, node: TreeNode, expected: str=None) -> bool:
        return cls.is_token(node, TokenType.SYMBOL, expected)

    @classmethod
    def eat(cls, it: Iterator[TreeNode], expected_token_type: TokenType=None,
            expected_token: str=None):
        node = next(it)
        if expected_token_type is not None and expected_token_type != node.token_type:
            raise SyntaxError(f"expected token type {expected_token_type} but got {node.token_type}")
        if expected_token is not None and expected_token != node.token:
            raise SyntaxError(f"expected token {expected_token} but got {node.token}")
        return node

    @classmethod
    def eat_keyword(cls, it: Iterator[TreeNode], keyword: Keyword=None) -> TreeNode:
        return cls.eat(it, TokenType.KEYWORD, keyword.value if keyword is not None else None)

    @classmethod
    def eat_identifier(cls, it: Iterator[TreeNode]) -> TreeNode:
        return cls.eat(it, TokenType.IDENTIFIER)
    
    @classmethod
    def eat_symbol(cls, it: Iterator[TreeNode], symbol: str=None) -> TreeNode:
        return cls.eat(it, TokenType.SYMBOL, symbol)
    
    @classmethod
    def eat_nonterminal(cls, it: Iterator[TreeNode], expected_type: NonTerminalType) -> TreeNode:
        node = cls.eat(it, TokenType.NONTERMINAL)
        if not expected_type.is_same(node.name):
            raise SyntaxError(f"expected '{expected_type.value}' but got '{node.name}'")
        return node
    
    @classmethod
    def parameter_size(cls, node: TreeNode) -> int:
        if not NonTerminalType.PARAMETER_LIST.is_same(node.name):
            raise ValueError
        return len([c for c in node.children if c.token_type == TokenType.IDENTIFIER])

    @classmethod
    def expression_size(cls, node: TreeNode) -> int:
        if not NonTerminalType.EXPRESSION_LIST.is_same(node.name):
            raise ValueError
        return len([c for c in node.children if NonTerminalType.EXPRESSION.is_same(c.name)])

class Context(dict):
    """able to put any data
    """

    def __init__(self):
        super().__init__()
        self.global_symbols = SymbolTable()
        self.local_symbols = SymbolTable()

    
class CompilationEngine:

    def __init__(self, writer: VMWriter):
        self.writer = writer
        self.namespace = ""

    def compile_class(self, root: TreeNode):
        if not Helper.is_nonterminal(root, NonTerminalType.CLASS):
            raise SyntaxError(f"expect 'class' but got '{root.name}'")
    
        context = Context()

        it = root.get_iterator()
        # should be 'class' keyword
        _ = Helper.eat_keyword(it, Keyword.CLASS)
        # class name
        node = Helper.eat_identifier(it)
        context["class"] = node.token
        # {
        _ = Helper.eat_symbol(it, "{")

        # TODO field
        # TODO static
        # TODO constructor
        # TODO method
        while it.has_next():
            node = next(it)
            # print(node.name)
            self.compile_subroutine(node, context)
            break
        # }
    
    def compile_subroutine(self, root: TreeNode, context: Context):
        it = root.get_iterator()
        # expect 'constructor', 'function' or 'method
        node = Helper.eat_keyword(it)
        function_type = Keyword.from_str(node.token)

        return_type: TreeNode = Helper.eat(it)
        function_name = f"{context['class']}.{Helper.eat_identifier(it).token}"
        
        # skip symbol
        _ = Helper.eat_symbol(it, "(")

        # parameters
        parametert_list = Helper.eat_nonterminal(it, NonTerminalType.PARAMETER_LIST)
        nargs = Helper.parameter_size(parametert_list)

        # skip symbol
        _ = Helper.eat_symbol(it, ")")

        # compile function name
        self.writer.write_functions(function_name, nargs)

        # TODO push arguments 

        # subroutine body
        body = Helper.eat_nonterminal(it, NonTerminalType.SUBROUTINE_BODY)

        context["return_type"] = return_type.token
        
        self.compile_subroutine_body(body, context)
        
        # moved out of function. remove it!
        del context["return_type"]
    
    def compile_subroutine_body(self, root: TreeNode, context: Context):
        it = root.get_iterator()
        _ = Helper.eat_symbol(it, "{")

        # statements
        statements = Helper.eat_nonterminal(it, NonTerminalType.STATEMETNS)
        self.compile_statements(statements, context)

        _ = Helper.eat_symbol(it, "}")
    
    def compile_statements(self, root: TreeNode, context: Context):
        for statement in root.loop_children():
            if NonTerminalType.DO_STATEMENT.is_same(statement.name):
                self.compile_do_statement(statement, context)
            elif NonTerminalType.RETURN_STATEMENT.is_same(statement.name):
                self.compile_return_statement(statement, context)
            else:
                raise NotImplementedError(statement.name)
    
    def compile_do_statement(self, root: TreeNode, context: Context):
        """calls a function returning nothing
        """
        # need a symbol table here!
        it = root.get_iterator()
        _ = Helper.eat_keyword(it, Keyword.DO)

        # method call
        #   do foo(x, y)
        # static function call
        #   do Output.printInt(123)
        # method call
        #   do p1.dist(p2)
        # in any case, start with identifier
        identifier = Helper.eat_identifier(it)

        # local variable's method
        if context.local_symbols.has_name(identifier.token):
            raise NotImplementedError
        # static variable's method?
        if context.global_symbols.has_name(identifier.token):
            raise NotImplementedError
        # static function or method call
        else:
            node = next(it)
            # static function call
            if Helper.is_symbol(node, "."):
                function_name = f"{identifier.token}.{Helper.eat_identifier(it).token}"
            else:
                raise NotImplementedError
        _ = Helper.eat_symbol(it, "(")
        # parse expression list
        expression_list = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION_LIST)
        self.compile_expression_list(expression_list, context)
        _ = Helper.eat_symbol(it, ")")

        # call function
        nargs = Helper.expression_size(expression_list)
        self.writer.write_call(function_name, nargs)

        # remove dummy return value
        self.writer.write_pop(Segment.TEMP, 0)

    
    def compile_expression_list(self, root: TreeNode, context: Context):
        """<expression> (, <expression>)*
        """
        it = root.get_iterator()
        # empty list
        if not it.has_next():
            return
        # at least one expression
        expression = next(it)
        self.compile_expression(expression, context)
        # more expressions
        while it.has_next():
            _ = Helper.eat_symbol(it, ",")
            expression = next(it)
            self.compile_expression(expression, context)
    
    def compile_expression(self, root: TreeNode, context: Context):
        """term (op term)*
        x
        x + y
        x + (y * z)
        """
        it = root.get_iterator()
        term = Helper.eat(it)
        if not it.has_next():
            self.compile_term(term, context)
        else:
            symbol = Helper.eat_symbol(it)
            other = Helper.eat(it)
            self.compile_term(term, context)
            self.compile_term(other, context)
            # handle operation
            if symbol.token == "*":
                self.writer.write_call("Math.multiply", 2)
            elif symbol.token == "/":
                self.writer.write_call("Math.divide", 2)
            else:
                cmd = ArithmeticCommand.from_symbol(symbol.token)
                self.writer.write_arithmetic(cmd)
                

    def compile_term(self, root: TreeNode, context: Context):
        # TODO
        it = root.get_iterator()
        node = Helper.eat(it)
        if node.is_terminal() and node.token_type == TokenType.INT_CONST:
            value = int(node.token)
            self.writer.write_push(Segment.CONSTANT, value)
        elif Helper.is_symbol(node, "("):
            # start of new expression?
            expression = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION)
            self.compile_expression(expression, context)
            _ = Helper.eat_symbol(it, ")")
        else:
            raise NotImplementedError
    
    def compile_return_statement(self, root: TreeNode, context: Context):
        if context["return_type"] == "void":
            # push dummy
            self.writer.write_push(Segment.CONSTANT, 0)
        else:
            raise NotImplementedError
        self.writer.write_return()


def main():
    import sys
    from JackTokenizer import JackTokenizer
    from ParseTree import ParseTreeBuilder
    input_filename = sys.argv[1]
    input_file = open(input_filename, "r")
    tokenizer = JackTokenizer(input_file)

    output_filename = input_filename.replace(".jack", ".mine.vm")
    output_file = open(output_filename, "w")
    # output_file = sys.stdout
    writer = VMWriter(output_file)

    # analyze
    tree_builder = ParseTreeBuilder(tokenizer)
    tree = tree_builder.build()

    # compile
    compiler = CompilationEngine(writer)
    compiler.compile_class(tree)

    input_file.close()
    output_file.close()

    print(input_filename)
    print(output_filename)


if __name__ == "__main__":
    main()



    
            




