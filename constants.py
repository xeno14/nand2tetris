"""defines constants and enum types
"""
import enum

# string constants
CATEGORY = "category"


class StringEnum(enum.Enum):

    @classmethod
    def from_str(cls, s: str) -> "StringEnum":
        for e in cls:
            if e.value == s:
                return e
        raise ValueError(f"{s} is not defined in {cls.__name__}")

    @classmethod
    def has_value(cls, value: str) -> bool:
        return any(value == e.value for e in cls)

    def to_str(self):
        return self.value


# ----------------------------------------------------------------
# VM
# ----------------------------------------------------------------
class Segment(StringEnum):
    """memory segments in VM
    """

    CONSTANT = "constant"
    ARGUMENT = "argument"
    LOCAL = "local"
    THIS = "this"
    THAT = "that"
    TEMP = "temp"
    STATIC = "static"


class ArithmeticCommand(StringEnum):

    ADD = "add"
    SUB = "sub"
    NEG = "neg"
    EQ = "eq"
    GT = "gt"
    LT = "lt"
    AND = "and"
    OR = "or"
    NOT = "not"


# ----------------------------------------------------------------
# Jack language
# ----------------------------------------------------------------
class TokenType(StringEnum):

    UNKNOWN = "unknown"
    # termianl
    KEYWORD = "keyword"
    SYMBOL = "symbol"
    IDENTIFIER = "identifier"
    INT_CONST = "integerConstant"
    STRING_CONST = "stringConstant"
    RETURN = "return"
    
    NONTERMINAL = "nonterminal"


class Keyword(StringEnum):

    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"
    CONSTRUCTOR = "constructor"
    INT = "int"
    BOOLEAN = "boolean"
    CHAR = "char"
    VOID = "void"
    VAR = "var"
    STATIC = "static"
    FIELD = "field"
    LET = "let"
    DO = "do"
    IF = "if"
    ELSE = "else"
    WHILE = "while"
    RETURN = "return"
    TRUE = "true"
    FALSE = "false"
    NULL = "null"
    THIS = "this"


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