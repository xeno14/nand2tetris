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
            return type_ok and expected.is_same(node.token)
        
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
    
    @classmethod
    def count_variables(cls, node: TreeNode) -> int:
        if NonTerminalType.VAR_DEC.is_same(node.name) or NonTerminalType.CLASS_VAR_DEC.is_same(node.name):
            return sum(Helper.is_symbol(c, ",") for c in node.children) + 1
        else:
            raise ValueError
    
    @classmethod
    def symbol_kind_to_segment(cls, kind: SymbolKind) -> Segment:
        if kind == SymbolKind.VAR:
            return Segment.LOCAL
        elif kind == SymbolKind.FIELD:
            return Segment.THIS
        elif kind == SymbolKind.STATIC:
            return Segment.STATIC
        elif kind == SymbolKind.ARG:
            return Segment.ARGUMENT
        else:
            raise ValueError


class Context(dict):
    """able to put any data
    """

    def __init__(self):
        super().__init__()
        self.global_symbols = SymbolTable()
        self.local_symbols = SymbolTable()
        self.label_count = {
            Keyword.IF: 0,
            Keyword.WHILE: 0
        }
    
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

    def nlocals(self):
        return len(self.local_symbols.table)
    
    def next_label_count(self, keyword: Keyword):
        res = self.label_count[keyword]
        self.label_count[keyword] += 1
        return res
    

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
        context["nfields"] = 0
        # {
        _ = Helper.eat_symbol(it, "{")

        # TODO static
        # TODO constructor
        # TODO method

        while it.has_next():
            node = Helper.eat(it)

            # class variables
            if Helper.is_nonterminal(node, NonTerminalType.CLASS_VAR_DEC):
                context["nfields"] += Helper.count_variables(node)
                self.compile_class_var_decl(context, node)
                continue

            if Helper.is_symbol(node, "}"):
                break
            # print(node.name)
            self.compile_subroutine(context, node)
        # }
    
    def compile_subroutine(self, context: Context, root: TreeNode):
        """
        <function_type> <function_name>
        {
            (<var statement>)*
            <statements>
        }
        """
        context.clear_local_symbols()
        it = root.get_iterator()
        # expect 'constructor', 'function' or 'method
        node = Helper.eat_keyword(it)
        function_type = Keyword.from_str(node.token)
        context['function_type'] = function_type

        return_type: TreeNode = Helper.eat(it)
        context["return_type"] = return_type.token

        function_name = f"{context['class']}.{Helper.eat_identifier(it).token}"
        
        # skip symbol
        _ = Helper.eat_symbol(it, "(")

        # parameters
        parametert_list = Helper.eat_nonterminal(it, NonTerminalType.PARAMETER_LIST)
        nargs = Helper.parameter_size(parametert_list)
        self.compile_parameter_list(context, parametert_list)

        # skip symbol
        _ = Helper.eat_symbol(it, ")")

        # 'function' instruction needs the number of local variables.
        # delegate it to compiler of subroutine body.
        context["function_name"] = function_name

        # subroutine body
        body = Helper.eat_nonterminal(it, NonTerminalType.SUBROUTINE_BODY)
        self.compile_subroutine_body(context, body)
        
        # moved out of function. remove it!
        del context["function_name"]
        del context["function_type"]
        del context["return_type"]
        context.clear_local_symbols()
    
    def compile_subroutine_body(self, context: Context, root: TreeNode):
        it = root.get_iterator()
        _ = Helper.eat_symbol(it, "{")

        # variables
        variables = []
        nlocals = 0
        while it.has_next():
            node = Helper.eat(it) 
            if not NonTerminalType.VAR_DEC.is_same(node.name):
                break
            variables.append(node)
            nlocals += Helper.count_variables(node)
        
        self.writer.write_functions(context["function_name"], nlocals)

        if context["function_type"] == Keyword.CONSTRUCTOR:
            nfields = context["nfields"]
            self.writer.write_push(Segment.CONSTANT, nfields)
            self.writer.write_call("Memory.alloc", 1)
            self.writer.write_pop(Segment.POINTER, 0)

        for var in variables:
            self.compile_var_decl(context, var)

        self.compile_statements(context, node)
        _ = Helper.eat_symbol(it)
    
    def compile_parameter_list(self, context, root: TreeNode):
        """define arguments in local symbol table
        int x, int y
        """
        it = root.get_iterator()
        while it.has_next():
            type = Helper.eat(it).token
            name = Helper.eat(it).token
            context.local_symbols.define(name, type, SymbolKind.ARG)
            if it.has_next():
                _ = Helper.eat_symbol(it, ",")
            else:
                break
        
    def process_variable_decl(self, root: TreeNode, table: SymbolTable, kind: SymbolKind):
        it = root.get_iterator()
        _ = Helper.eat_keyword(it)
        type = Helper.eat(it).token
        # name
        while it.has_next():
            name = Helper.eat_identifier(it).token
            table.define(name, type, kind)

            symbol = Helper.eat_symbol(it)
            if symbol.token == ";":
                break
    
    def compile_class_var_decl(self, context: Context, root: TreeNode):
        # TODO static variable:
        self.process_variable_decl(root, context.global_symbols, SymbolKind.FIELD)

    def compile_var_decl(self, context: Context, root: TreeNode):
        """
        var int x, y;
        var Foo foo;
        """
        self.process_variable_decl(root, context.local_symbols, SymbolKind.VAR)
    
    def compile_statements(self, context: Context, root: TreeNode):
        for statement in root.loop_children():
            if NonTerminalType.DO_STATEMENT.is_same(statement.name):
                self.compile_do_statement(context, statement)
            elif NonTerminalType.RETURN_STATEMENT.is_same(statement.name):
                self.compile_return_statement(context, statement)
            elif NonTerminalType.LET_STATEMENT.is_same(statement.name):
                self.compile_let_statement(context, statement)
            elif NonTerminalType.WHILE_STATEMENT.is_same(statement.name):
                self.compile_while_statement(context, statement)
            elif NonTerminalType.IF_STATEMENT.is_same(statement.name):
                self.compile_if_statement(context, statement)
            else:
                print(statement.name)
                # raise NotImplementedError(statement.name)

    def compile_call(self, context: Context, it: Iterator[TreeNode]):
        """to be called by do-statement or let-statement
        """
        identifier = Helper.eat_identifier(it)

        # local variable's method
        push_this = False
        eat_left_paren = True
        if context.local_symbols.has_name(identifier.token):
            name = identifier.token
            symbol = context.local_symbols.get(name)

            _ = Helper.eat_symbol(it, ".")

            # function name
            type = symbol.type
            method_name = Helper.eat_identifier(it).token
            function_name = f"{type}.{method_name}"

            # push the variable as the first arugment
            segment = Helper.symbol_kind_to_segment(symbol.kind)
            self.writer.write_push(segment, symbol.index)
            push_this = True
        # static variable's method?
        elif context.global_symbols.has_name(identifier.token):
            raise NotImplementedError
        # static function or method call
        else:
            node = next(it)
            # static function call
            if Helper.is_symbol(node, "."):
                function_name = f"{identifier.token}.{Helper.eat_identifier(it).token}"
            # method call
            else:
                method_name = identifier.token
                function_name = f"{context['class']}.{method_name}"

                # push THIS as the first arugment
                self.writer.write_push(Segment.POINTER, 0)
                push_this = True
                eat_left_paren = False
        if eat_left_paren:
            _ = Helper.eat_symbol(it, "(")
        # parse expression list
        expression_list = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION_LIST)
        self.compile_expression_list(context, expression_list)

        _ = Helper.eat_symbol(it, ")")

        # call function
        nargs = Helper.expression_size(expression_list) + push_this
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
        segment = Helper.symbol_kind_to_segment(symbol.kind)
        self.writer.write_pop(segment, symbol.index)
    
    def compile_while_statement(self, context:Context, root: TreeNode):
        it = root.get_iterator()

        label_count = context.next_label_count(Keyword.WHILE)
        exp_label = f"WHILE_EXP{label_count}"
        end_label = f"WHILE_END{label_count}"

        self.writer.write_label(exp_label)
        _ = Helper.eat_keyword(it, Keyword.WHILE)

        # expression
        _ = Helper.eat_symbol(it, "(")
        expression = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION)
        self.compile_expression(context, expression)
        _ = Helper.eat_symbol(it, ")")

        # check end condition
        self.writer.write_arithmetic(ArithmeticCommand.NOT)
        self.writer.write_if(end_label)

        # statements
        _ = Helper.eat_symbol(it, "{")
        statements = Helper.eat_nonterminal(it, NonTerminalType.STATEMETNS)
        self.compile_statements(context, statements)
        # loop top
        self.writer.write_goto(exp_label)
        _ = Helper.eat_symbol(it, "}")

        self.writer.write_label(end_label)
    
    def compile_if_statement(self, context: Context, root: TreeNode):
        """
        <expr>
        if-goto IFTRUE
        goto IFFLASE
        label IFTRUE
        <statements>
        goto IFEND
        label IFFALSE (else)
        <statements>
        label IFEND
        """
        it = root.get_iterator()
        
        # labels
        n = context.next_label_count(Keyword.IF)
        if_true_label = f"IF_TRUE{n}"
        if_false_label = f"IF_FALSE{n}"
        if_end_label = f"IF_END{n}"

        # if (expr)
        _ = Helper.eat_keyword(it, Keyword.IF)
        _ = Helper.eat_symbol(it, "(")
        expr = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION)
        self.compile_expression(context, expr)
        _ = Helper.eat_symbol(it, ")")
        
        # jump
        self.writer.write_if(if_true_label)     # if-statement
        self.writer.write_goto(if_false_label)  # else-statement

        # if true statements
        self.writer.write_label(if_true_label)
        _ = Helper.eat_symbol(it, "{")
        statements = Helper.eat_nonterminal(it, NonTerminalType.STATEMETNS)
        self.compile_statements(context, statements)
        self.writer.write_goto(if_end_label)
        _ = Helper.eat_symbol(it, "}")

        # else statement (optional)
        self.writer.write_label(if_false_label)
        if it.has_next():
            _ = Helper.eat_keyword(it, Keyword.ELSE)
            _ = Helper.eat_symbol(it, "{")
            statements = Helper.eat_nonterminal(it, NonTerminalType.STATEMETNS)
            self.compile_statements(context, statements)
            _ = Helper.eat_symbol(it, "}")
        # end label
        self.writer.write_label(if_end_label)

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
                # to avoid confusion with neg
                if symbol.token == "-":
                    cmd = ArithmeticCommand.SUB
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
        elif Helper.is_symbol(node, "~"):
            term = Helper.eat_nonterminal(it, NonTerminalType.TERM)
            self.compile_term(context, term)
            self.writer.write_arithmetic(ArithmeticCommand.NOT)
        # boolean
        elif Helper.is_keyword(node, Keyword.TRUE):
            # push -1
            self.writer.write_push(Segment.CONSTANT, 0)
            self.writer.write_arithmetic(ArithmeticCommand.NOT)
        elif Helper.is_keyword(node, Keyword.FALSE):
            self.writer.write_push(Segment.CONSTANT, 0)
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
                segment = Helper.symbol_kind_to_segment(symbol.kind)
                self.writer.write_push(segment, symbol.index)
    
    def compile_return_statement(self, context: Context, root: TreeNode):
        it = root.get_iterator()
        _ = Helper.eat_keyword(it)
        if context["return_type"] == "void":
            # push dummy
            self.writer.write_push(Segment.CONSTANT, 0)
        elif context["function_type"] == Keyword.CONSTRUCTOR:
            # expect return this;
            expr = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION)
            term = Helper.eat_nonterminal(expr.get_iterator(), NonTerminalType.TERM)
            _ = Helper.eat_keyword(term.get_iterator(), Keyword.THIS)
            self.writer.write_push(Segment.POINTER, 0)
        else:
            expr = Helper.eat_nonterminal(it, NonTerminalType.EXPRESSION)
            self.compile_expression(context, expr)
        self.writer.write_return()


def main():
    import sys
    from JackTokenizer import JackTokenizer
    from ParseTree import ParseTreeBuilder
    input_filename = sys.argv[1]
    input_file = open(input_filename, "r")
    tokenizer = JackTokenizer(input_file)

    output_filename = input_filename.replace(".jack", ".vm")
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