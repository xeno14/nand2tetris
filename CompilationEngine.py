from ParseTree import TreeNode, TreeNodeIterator
from VMWriter import VMWriter
from constants import *
from SymbolTable import SymbolTable, Symbol

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
    def is_identifier(cls, node: TreeNode) -> bool:
        return cls.is_token(node, TokenType.IDENTIFIER)

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
    def eat_nonterminal(cls, it: Iterator[TreeNode], expected_type: NonTerminalType=None) -> TreeNode:
        node = cls.eat(it, TokenType.NONTERMINAL)
        if expected_type is not None and not expected_type.is_same(node.name):
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
    
    def clear_local_symbols(self):
        self.local_symbols = SymbolTable()
    
    def lookup_symbol(self, name: str) -> Symbol:
        """look up a symbol in local then global
        """
        if name in self.local_symbols.table:
            return self.local_symbols.table[name]
        elif name in self.global_symbols.table:
            return self.global_symbols.table[name]
        else:
            raise KeyError(f"undefined variable {name}")

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
            self.compile_subroutine(context, node)
            break
        # }
    
    def compile_subroutine(self, context: Context, root: TreeNode):
        """
        <function_type> <function_name>
        {
            (<var statement>)*
            <statements>
        }
        """
        it = root.get_iterator()
        # expect 'constructor', 'function' or 'method
        node = Helper.eat_keyword(it)
        function_type = Keyword.from_str(node.token)

        return_type: TreeNode = Helper.eat(it)
        context["return_type"] = return_type.token

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
        self.compile_subroutine_body(context, body)
        
        # moved out of function. remove it!
        del context["return_type"]
        context.clear_local_symbols()
    
    def compile_subroutine_body(self, context: Context, root: TreeNode):
        it = root.get_iterator()
        _ = Helper.eat_symbol(it, "{")

        while it.has_next():
            node = Helper.eat(it) 
            if Helper.is_symbol(node, "}"):
                break
            if NonTerminalType.STATEMETNS.is_same(node.name):
                self.compile_statements(context, node)
            elif NonTerminalType.VAR_DEC.is_same(node.name):
                self.compile_var_decl(context, node)
            else:
                print(node)
                # raise SyntaxError("Unexpected {node.name}")
    
    def compile_var_decl(self, context: Context, root: TreeNode):
        """
        var int x, y;
        var Foo foo;
        """
        it = root.get_iterator()
        # var
        _ = Helper.eat_keyword(it, Keyword.VAR)
        # type
        type = Helper.eat(it).token
        # name
        while it.has_next():
            name = Helper.eat_identifier(it).token
            context.local_symbols.define(name, type, SymbolKind.VAR)

            symbol = Helper.eat_symbol(it)
            if symbol.token == ";":
                break
    
    def compile_statements(self, context: Context, root: TreeNode):
        for statement in root.loop_children():
            if NonTerminalType.DO_STATEMENT.is_same(statement.name):
                self.compile_do_statement(context, statement)
            elif NonTerminalType.RETURN_STATEMENT.is_same(statement.name):
                self.compile_return_statement(context, statement)
            elif NonTerminalType.LET_STATEMENT.is_same(statement.name):
                self.compile_let_statement(context, statement)
            else:
                print(statement.name)
                # raise NotImplementedError(statement.name)

    def compile_call(self, context: Context, it: Iterator[TreeNode]):
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
        self.compile_expression_list(context, expression_list)
        _ = Helper.eat_symbol(it, ")")

        # call function
        nargs = Helper.expression_size(expression_list)
        self.writer.write_call(function_name, nargs)

    def compile_do_statement(self, context: Context, root: TreeNode):
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
        self.compile_call(context, it)

        # remove dummy return value
        self.writer.write_pop(Segment.TEMP, 0)

    def compile_let_statement(self, context: Context, root: TreeNode):
        it = root.get_iterator()
        _ = Helper.eat_keyword(it, Keyword.LET)
        # variable
        identifier = Helper.eat_identifier(it)
        name = identifier.token

        _ = Helper.eat_symbol(it, "=")
        expression = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION)
        self.compile_expression(context, expression)
        # pop the stack top to the variable
        symbol = context.lookup_symbol(name)
        if symbol.kind == SymbolKind.VAR:
            self.writer.write_pop(Segment.LOCAL, symbol.index)
        elif symbol.kind == SymbolKind.FIELD:
            self.writer.write_pop(Segment.THIS, symbol.index)
        elif symbol.kind == SymbolKind.STATIC:
            self.writer.write_pop(Segment.STATIC, symbol.index)
        else:
            raise NotImplementedError
    
    def compile_expression_list(self, context: Context, root: TreeNode):
        """<expression> (, <expression>)*
        """
        it = root.get_iterator()
        # empty list
        if not it.has_next():
            return
        # at least one expression
        expression = next(it)
        self.compile_expression(context, expression)
        # more expressions
        while it.has_next():
            _ = Helper.eat_symbol(it, ",")
            expression = next(it)
            self.compile_expression(context, expression)
    
    def compile_expression(self, context: Context, root: TreeNode):
        """term (op term)*
        x
        x + y
        x + (y * z)
        """
        it = root.get_iterator()
        term = Helper.eat(it)
        if not it.has_next():
            self.compile_term(context, term)
        else:
            symbol = Helper.eat_symbol(it)
            other = Helper.eat(it)
            self.compile_term(context, term)
            self.compile_term(context, other)
            # handle operation
            if symbol.token == "*":
                self.writer.write_call("Math.multiply", 2)
            elif symbol.token == "/":
                self.writer.write_call("Math.divide", 2)
            else:
                cmd = ArithmeticCommand.from_symbol(symbol.token)
                self.writer.write_arithmetic(cmd)
                

    def compile_term(self, context: Context, root: TreeNode):
        """
        x
        -x
        ((x+y)*2)
        Memory.peek(8000)
        variable
        """
        it = root.get_iterator()
        node = Helper.eat(it)
        # integer constant
        if node.is_terminal() and node.token_type == TokenType.INT_CONST:
            value = int(node.token)
            self.writer.write_push(Segment.CONSTANT, value)
        # unary operation
        elif Helper.is_symbol(node, "-"):
            term = Helper.eat_nonterminal(it, NonTerminalType.TERM)
            self.compile_term(context, term)
            self.writer.write_arithmetic(ArithmeticCommand.NEG)
        # expression enclosed by parentheses
        elif Helper.is_symbol(node, "("):
            expression = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION)
            self.compile_expression(context, expression)
            _ = Helper.eat_symbol(it, ")")
        elif Helper.is_identifier(node):
            # function call or variable
            if it.has_next():
                self.compile_call(context, root.get_iterator())
            else:
                name = node.token
                symbol = context.lookup_symbol(name)
                if symbol.kind == SymbolKind.VAR:
                    self.writer.write_push(Segment.LOCAL, symbol.index)
                elif symbol.kind == SymbolKind.STATIC:
                    self.writer.write_push(Segment.STATIC, symbol.index)
                elif symbol.kind == SymbolKind.FIELD:
                    self.writer.write_push(Segment.THIS, symbol.index)
                else:
                    raise NotImplementedError
            # print(node)
            # raise NotImplementedError
    
    def compile_return_statement(self, context: Context, root: TreeNode):
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



    
            




