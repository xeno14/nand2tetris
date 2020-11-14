from JackTokenizer import JackTokenizer, TokenType, Keyword, StringEnum
from typing import List, Tuple
import io


class NonTerminalType(StringEnum):

    CLASS = "class"
    CLASS_VAR_DEC = "classVarDec"
    SUBROUTINE_DEC = "subroutineDec"
    PARAMETER_LIST = "parameterList"
    SUBROUTINE_BODY = "subroutineBody"
    VAR_DEC = "varDec"
    STATEMETNS = "statements"
    LET_STATEMENT = "letStatement"
    IF_STATEMENT = "ifStatement"
    WHILE_STATEMENT = "whileStatement"
    DO_STATEMENT = "doStatement"
    RETURN_STATEMENT = "returnStatement"
    EXPRESSION = "expression"
    TERM = "term"
    EXPRESSION_LIST = "expressionList"


class TreeNode:

    def __init__(self, token_type: TokenType, token: str="", children: List["TreeNode"]=None):
        if children is None:
            children = []
        self.children = children
        self.token_type = token_type
        self.token = token

    @property
    def name(self):
        return self.token_type.value
    
    def is_leaf(self):
        return len(self.children) == 0
    
    def has_child(self):
        return not self.is_leaf()
    
    def add(self, *childlen):
        for child in childlen:
            self.children.append(child)
    
    def to_xml(self, fout, depth=0):
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.name}> {self.token} </{self.name}>"

    def __str__(self):
        with io.StringIO() as f:
            self.to_xml(f)
            return f.getvalue()


class TerminalNode(TreeNode):

    def __init__(self, token_type: TokenType, token: str):
        super().__init__(token_type, token)
    
    def add(self):
        raise NotImplementedError("never call 'add'")

    def to_xml(self, fout, depth=0):
        from xml.sax import saxutils
        indent = "  " * depth
        tag = f"<{self.name}> {saxutils.escape(self.token)} </{self.name}>"
        fout.write(indent + tag + "\n")
    

class NonTerminalNode(TreeNode):

    def __init__(self, nodetype: NonTerminalType):
        super().__init__(TokenType.NONTERMINAL, nodetype.value)
        self._nodetype = nodetype

    @property
    def nodetype(self) -> NonTerminalType:
        return self._nodetype

    @property
    def name(self) -> str:
        return self.nodetype.value

    def to_xml(self, fout, depth=0):
        indent = "  " * depth
        opentag = f"<{self.name}>"
        closetag = f"</{self.name}>"
        fout.write(indent + opentag + "\n")
        for child in self.children:
            child.to_xml(fout, depth+1)
        fout.write(indent + closetag + "\n")
    
    def add_symbol(self, symbol: str):
        assert symbol in JackTokenizer.SYMBOLS
        self.add(
            TerminalNode(TokenType.SYMBOL, symbol)
        )


class CompilationEngine:

    def __init__(self, tokenizer: JackTokenizer, fout):
        self.tokenizer = tokenizer
        self.fout = fout
        self.tokenizer.advance()
        self.root: TreeNode = None
        self.depth = 0

    def eat(self) -> Tuple[TokenType, str]:
        """returns the current token and advance
        """
        token_type = self.tokenizer.token_type()
        token = self.tokenizer.token()
        self.tokenizer.advance()
        return token_type, token
    
    def write(self):
        self.root.to_xml(self.fout)

    # ----------------------------------------------------------------
    # eat functions to build TreeNode
    # ----------------------------------------------------------------
    def eat_terminal(self, expected_token_type: TokenType=None, expected_token: str="") -> TerminalNode:
        token_type, token = self.eat()
        if expected_token_type is not None:
            assert token_type == expected_token_type
        if expected_token:
            assert token == expected_token
        return TerminalNode(token_type=token_type, token=token)
    
    def eat_identifier(self):
        return self.eat_terminal(TokenType.IDENTIFIER)

    def eat_keyword(self, keyword: Keyword=None) -> TerminalNode:
        if keyword is None:
            return self.eat_terminal(TokenType.KEYWORD)
        else:
            return self.eat_terminal(TokenType.KEYWORD, keyword.value)

    def eat_symbol(self, symbol: str="") -> TerminalNode:
        if not symbol == "":
            assert symbol in JackTokenizer.SYMBOLS
        return self.eat_terminal(TokenType.SYMBOL, symbol)

    def is_symbol(self, expected_symbol: str="") -> bool:
        type_ok = self.tokenizer.token_type() == TokenType.SYMBOL
        if len(expected_symbol) == 0:
            return type_ok
        else:
            return type_ok and self.tokenizer.symbol() == expected_symbol
    
    def is_keyword(self, expected_keyword: Keyword) -> bool:
        return self.tokenizer.token_type() == TokenType.KEYWORD and self.tokenizer.keyword() == expected_keyword
    
    # ----------------------------------------------------------------
    # functions to complie
    # ----------------------------------------------------------------
    def compile_class(self):
        """jack file always starts with 'class' keyword
        """
        assert self.is_keyword(Keyword.CLASS)
        self.root = NonTerminalNode(NonTerminalType.CLASS)
        self.root.add(
            self.eat_keyword(Keyword.CLASS),
            self.eat_identifier(),
            self.eat_symbol("{")
        )

        while self.tokenizer.has_more_tokens() and not self.is_symbol("}"):
            # for class, expect keywords only
            # classVarDec
            if self.is_keyword(Keyword.FIELD) or self.is_keyword(Keyword.STATIC):
                self.compile_class_var_dec(self.root)
            elif self.is_keyword(Keyword.CONSTRUCTOR) or self.is_keyword(Keyword.METHOD) or self.is_keyword(Keyword.FUNCTION):
                self.compile_subroutine(self.root)
            else:
                _ = self.eat()
        self.root.add(
            self.eat_symbol("}"))
                
    def compile_class_var_dec(self, parent: TreeNode):
        """
        field int x, y;
        """
        node = NonTerminalNode(NonTerminalType.CLASS_VAR_DEC)
        node.add(
            self.eat_keyword()
        )
        while self.tokenizer.has_more_tokens():
            if self.is_symbol(";"):
                node.add(
                    self.eat_symbol(";")
                )
                break
            # expect terminal nodes
            token_type, token = self.eat()
            child = TerminalNode(token_type, token)
            node.add(child)
        parent.add(node)

    def compile_subroutine(self, parent: TreeNode):
        """
        method void draw() {
            do Screen.setColor(x);
            do Screen.drawRectangle(x, y, x, y);
            return;
        }
        """
        node = NonTerminalNode(NonTerminalType.SUBROUTINE_DEC)
        node.add(
            self.eat_keyword(),     # 'method' or 'constructor' or 'function'
        )
        # return type is an identifier or void (keyword)
        if self.is_keyword(Keyword.VOID):
            node.add(self.eat_keyword(Keyword.VOID))
        else:
            node.add(self.eat_identifier())
        node.add(
            self.eat_identifier(),  # function name
            self.eat_symbol("(")
        )
        # parameter list
        self.compile_parameter_list(node)
        node.add(
            self.eat_symbol(")")
        )

        # subroutine body
        body = NonTerminalNode(NonTerminalType.SUBROUTINE_BODY)
        body.add(
            self.eat_symbol("{")
        )
        # optinally variable declarations
        while self.is_keyword(Keyword.VAR):
            self.compile_var_dec(body)
        # statement
        self.compile_statements(body)
        # end of body
        body.add(
            self.eat_symbol("}")
        )

        node.add(body)
        parent.add(node)
    
    def compile_parameter_list(self, parent: TreeNode):
        """
        ()
        (int x, int y)
        """
        node = NonTerminalNode(NonTerminalType.PARAMETER_LIST)
        while self.tokenizer.has_more_tokens():
            if self.is_symbol(")"):
                break
            # expect termianl expressions
            token_type, token = self.eat()
            child = TerminalNode(token_type, token)
            node.add(child)
        parent.add(node)
    
    def compile_statements(self, parent: TreeNode):
        """
        var int a;
        let a = 1;
        """
        node = NonTerminalNode(NonTerminalType.STATEMETNS)
        while self.tokenizer.has_more_tokens():
            if self.is_symbol("}"):
                break
            # let, do, return, if, while
            if self.is_keyword(Keyword.LET):
                self.compile_let(node)
            elif self.is_keyword(Keyword.DO):
                self.compile_do(node)
            elif self.is_keyword(Keyword.RETURN):
                self.compile_return(node)
            elif self.is_keyword(Keyword.IF):
                self.compile_if_statement(node)
            elif self.is_keyword(Keyword.WHILE):
                self.compile_while_statement(node)
            else:
                print(f"ignoring {self.eat()}")
        parent.add(node)
    
    def compile_var_dec(self, parent: TreeNode):
        """
        var int x, y;
        var int x;
        """
        node = NonTerminalNode(NonTerminalType.VAR_DEC)
        node.add(
            self.eat_keyword(Keyword.VAR),  # var
            self.eat_terminal()             # type can be keyword or identifier
        )
        while self.tokenizer.has_more_tokens():
            node.add(self.eat_identifier())
            if self.is_symbol(";"):
                break
            elif self.is_symbol(","):
                node.add(self.eat_symbol(","))
            else:
                raise SyntaxError(self.tokenizer.current_line())
        node.add(self.eat_symbol(";"))
        parent.add(node)
    
    def compile_let(self, parent: TreeNode):
        """
        let <lhs> = <expression>

        let a = 1;
        let a[i] = foo;
        let a = Foo.bar();
        """
        # let <identifier>
        node = NonTerminalNode(NonTerminalType.LET_STATEMENT)
        node.add(
            self.eat_keyword(Keyword.LET),
            self.eat_identifier()
        )
        # can be array
        if self.is_symbol("["):
            node.add(self.eat_symbol("["))
            self.compile_expression(node)
            node.add(self.eat_symbol("]"))

        # =
        node.add(
            self.eat_symbol("="),
        )
        # rhs is expression
        self.compile_expression(node)
        node.add(self.eat_symbol(";"))
        parent.add(node)

    def compile_do(self, parent: TreeNode):
        """
        do foo(<ExpressionList>)
        do Output.printInt(<ExpressionList>)
        """
        node = NonTerminalNode(NonTerminalType.DO_STATEMENT)
        node.add(
            self.eat_keyword(Keyword.DO))
        # continue until reaching (
        while self.tokenizer.has_more_tokens():
            if self.is_symbol("("):
                break
            # expect termianl expressions
            token_type, token = self.eat()
            child = TerminalNode(token_type, token)
            node.add(child)

        # expression list (arguments for the function call)
        node.add(self.eat_symbol("("))
        self.compile_expression_list(node)
        node.add(
            self.eat_symbol(")"),
            self.eat_symbol(";"))

        parent.add(node)

    def compile_expression(self, parent: TreeNode):
        """
        let a = <expr>;
        do foo(<expr>, <expr>)
        a[<expr>]
        """
        node = NonTerminalNode(NonTerminalType.EXPRESSION)
        self.compile_term(node)
        # termination
        if any(self.is_symbol(e) for e in ",;)]"):
            pass
        else:
            if self.is_symbol():
                # binary operation
                node.add(self.eat_symbol())
                self.compile_term(node)
            else:
                self.compile_term(node)
        parent.add(node)
    
    def compile_term(self, parent: TreeNode):
        """
        x
        a[i]
        foo.bar()
        "hogehoge"
        1
        (x+1) * (y+2)
        ~flag
        """
        node = NonTerminalNode(NonTerminalType.TERM)
        # start of another expression
        if self.is_symbol("("):
            node.add(self.eat_symbol("("))
            self.compile_expression(node)
            node.add(self.eat_symbol(")"))
        # unary operation
        elif self.is_symbol():
            # expect ~ or -
            symbol = self.tokenizer.symbol()
            if symbol not in "-~":
                raise SyntaxError(f"unexpected unary operator {symbol}")
            node.add(self.eat_symbol(symbol))
            if self.is_symbol("("):
                self.compile_term(node)
            # otherwise, an identifier should follow
            else:
                self.compile_term(node)
        # otherwise it must be an expression
        else:
            node.add(self.eat_terminal())

        # array
        if self.is_symbol("["):
            node.add(self.eat_symbol("["))
            self.compile_expression(node)
            node.add(self.eat_symbol("]"))
        # function call
        elif self.is_symbol("."):
            node.add(
                self.eat_symbol("."),
                self.eat_identifier(), # funcition name
                self.eat_symbol("(")
            )
            self.compile_expression_list(node)
            node.add(self.eat_symbol(")"))
        # member function call
        elif self.is_symbol("("):
            node.add(self.eat_symbol("("))
            self.compile_expression_list(node)
            node.add(self.eat_symbol(")"))

        parent.add(node)
    
    def compile_expression_list(self, parent: TreeNode):
        """
        ()
        (x)
        (x, y)
        """
        node = NonTerminalNode(NonTerminalType.EXPRESSION_LIST)
        while self.tokenizer.has_more_tokens() and not self.is_symbol(")"):
            self.compile_expression(node)
            if self.is_symbol(","):
                node.add(
                    self.eat_symbol(",")
                )
        parent.add(node)
    
    def compile_return(self, parent: TreeNode):
        """
        return x;
        return;
        return (x+y) - 2;
        """
        node = NonTerminalNode(NonTerminalType.RETURN_STATEMENT)
        node.add(self.eat_keyword(Keyword.RETURN))
        if not self.is_symbol(";"):
            self.compile_expression(node)
        node.add(self.eat_symbol(";"))
        parent.add(node)
    
    def compile_if_statement(self, parent: TreeNode):
        """
        if (<expression>) {
            <statements>
        }

        if (<expression>) {
            <statements>
        }
        else {
            <statements>
        }
        """
        node = NonTerminalNode(NonTerminalType.IF_STATEMENT)
        node.add(
            self.eat_keyword(Keyword.IF),
            self.eat_symbol("(")
        )
        self.compile_expression(node)
        node.add(
            self.eat_symbol(")"),
            self.eat_symbol("{"))
        self.compile_statements(node)
        node.add(
            self.eat_symbol("}")
        )
        # else-statement is optional
        if self.is_keyword(Keyword.ELSE):
            node.add(
                self.eat_keyword(Keyword.ELSE),
                self.eat_symbol("{")
            )
            self.compile_statements(node)
            node.add(
                self.eat_symbol("}")
            )
        parent.add(node)
    
    def compile_while_statement(self, parent: TreeNode):
        """
        while (<expression>) {
            <statements>
        }
        """
        node = NonTerminalNode(NonTerminalType.WHILE_STATEMENT)
        node.add(
            self.eat_keyword(Keyword.WHILE),
            self.eat_symbol("(")
        )
        self.compile_expression(node)
        node.add(
            self.eat_symbol(")"),
            self.eat_symbol("{"))
        self.compile_statements(node)
        node.add(
            self.eat_symbol("}")
        )
        parent.add(node)


def main():
    import sys
    input_filename = sys.argv[1]
    input_file = open(input_filename, "r")
    tokenizer = JackTokenizer(input_file)

    output_filename = input_filename.replace(".jack", ".mine.xml")
    output_file = open(output_filename, "w")
    # output_file = sys.stdout

    engine = CompilationEngine(tokenizer, output_file)
    engine.compile_class()
    engine.write()

    input_file.close()
    output_file.close()

    print(input_filename)
    print(output_filename)


if __name__ == "__main__":
    main()