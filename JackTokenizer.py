from constants import TokenType, Keyword


class Reader:
    """read a file ignoring leading spaces

    Example:
    if (x<0) {
        let state = "negative";
    }
    
    repeating word=reader.head_word() and reader.move(len(word)) until EOF yeilds:
    'if' '(x<0)' '{' 'let' 'state' '=' '"negative";' '}
    """

    def __init__(self, f):
        self.f = f
        self.line = ""
        self.lineno = 0
        self.eof =  False
        self.move_to_word()

    def is_eof(self):
        return self.eof

    def readline(self) -> bool:
        """read a line and strip, returns reached EOF or not
        """
        l = self.f.readline()
        if l == "":
            self.eof = True
            return False
        self.line = l.strip()
        self.lineno += 1
        return True

    def move_to_word(self):
        """read file until reaching a non empty string
        """
        while self.line == "":
            if not self.readline():
                return
    
    def head(self):
        return self.line[0]
    
    def startswith(self, s):
        return self.line.startswith(s)
    
    def contains(self, s):
        return s in self.line

    def skip(self, s: str):
        i = self.line.find(s)
        self.line = self.line[i+len(s):]

    def move(self, d: int):
        """move 'd' characters then skip blanks
        """
        while d > len(self.line):
            d -= len(self.line)
            if not self.readline():
                return
        self.line = self.line[d:].strip()
        self.move_to_word()
    
    def head_word(self):            
        self.move_to_word()
        i = self.line.find(" ")
        if i==-1:
            return self.line
        else:
            return self.line[:i]


class JackTokenizer:
    """Tokenizes Jack source code.

    Example:
    Source Code:
        if (x < 0) {
            let state = "negative";
        }

    Tokenizer output:
        <tokens>
            <keyword> if </keyword>
            <symbol> ( </symbol>
            <identifier> x </identifier>
            <symbol> &lt; </symbol>
            <integerConstant> 0 </integerConstant>
            <symbol> ) </symbol>
            <symbol> { </symbol>
            <keyword> let </keyword>
            <identifier> state </identifier>
            <symbol> = </symbol>
            <stringConstant> negative </stringConstant>
            <symbol> ; </symbol>
            <symbol> } </symbol>
        </tokens>
    """

    SYMBOLS = set("{}()[].,;+-*/&|<>=~")

    def __init__(self, f):
        self.reader = Reader(f)
        self.eof = False
        self.line = ""
        self._token_type: TokenType = TokenType.UNKNOWN
        self._raw_token: str = "" # raw expression of token e.g. "if", "123"

    def has_more_tokens(self) -> bool:
        return not self.reader.is_eof()
    
    def current_line(self) -> str:
        return self.reader.line

    def advance(self):
        """Gets the next token from the input and makes it the current token.
        This method should be called if has_more_tokens() is true. Initially
        There is no current token.
        """
        # read a word
        is_comment = False
        while True:
            word = self.reader.head_word()
            # handle multi-line comments
            # start multiline comment
            if word.startswith("/*"):
                i = self.reader.line.find("*/")
                # can be one line comment
                if i >= 0:
                    self.reader.move(i+2)
                # otherwise skip the line
                else:
                    is_comment = True
                    self.reader.readline()
                continue
            # middle of multiline comment
            elif is_comment:
                i = self.reader.line.find("*/")
                if i >= 0:
                    is_comment = False
                    self.reader.move(i+2)
                else:
                    self.reader.readline()
                continue
            # skip line comment
            if word.startswith("//"):
                self.reader.readline()
                continue
            if self.reader.is_eof():
                return
            break

        # Let's tokenize!

        # string constant
        if word[0] == '"':
            self._token_type = TokenType.STRING_CONST
            # string contant may contain whitespace hence can't rely on
            # reader's api. instread, directly read the line.
            s = self.reader.line[1:]
            # find the other double quote
            s = s[:s.find('"')]
            self._raw_token = s
            self.reader.move(len(s) + 2)
        # symbol
        elif word[0] in self.SYMBOLS:
            self._token_type = TokenType.SYMBOL
            self._raw_token = word[0]
            self.reader.move(1)
        # int const
        elif word[0].isdigit():
            self._token_type = TokenType.INT_CONST
            digit = ""
            for c in word:
                if c.isdigit():
                    digit += c
                else:
                    break
            self._raw_token = digit
            self.reader.move(len(digit))
        # symbol or identifier
        else:
            token = ""
            for c in word:
                if c.isalpha() or c == "_":
                    token += c
                else:
                    break
            self.reader.move(len(token))
            # symbol
            if Keyword.has_value(token):
                self._token_type = TokenType.KEYWORD
                self._raw_token = token
            # identifier
            else:
                self._token_type = TokenType.IDENTIFIER
                self._raw_token = token

    def token_type(self) -> TokenType:
        """Returns the type of the curren token
        """
        return self._token_type

    def keyword(self) -> Keyword:
        """Returns the keyword which is the current token. Should be called
        only when token_type() is KEYWORD.
        """
        assert self._token_type == TokenType.KEYWORD
        return Keyword.from_str(self._raw_token)
    
    def token(self) -> str:
        return self._raw_token

    def symbol(self) -> str:
        """Returns the charactor which is the current token. Should be called
        only when token_type() is SYMBOL.
        """
        assert self._token_type == TokenType.SYMBOL
        return self._raw_token

    def identifier(self) -> str:
        assert self._token_type == TokenType.IDENTIFIER
        return self._raw_token

    def int_val(self) -> int:
        assert self._token_type == TokenType.INT_CONST
        return int(self._raw_token)

    def string_val(self) -> str:
        assert self._token_type == TokenType.STRING_CONST
        return self._raw_token


def test_reader(f):
    reader = Reader(f)
    while not reader.is_eof():
        word = reader.head_word()
        if word.startswith("//") or word.startswith("/*"):
            reader.readline()
            continue
        print(word)
        reader.move(len(word))


def main():
    import sys
    from xml.sax import saxutils
    input_file = sys.argv[1]

    print("Tokenizing " + input_file)

    lines = []
    lines.append("<tokens>")
    with open(input_file, "r") as f:
        tokenizer = JackTokenizer(f)
        while tokenizer.has_more_tokens():
            tokenizer.advance()

            token_type = tokenizer.token_type()
            token = tokenizer._raw_token
            token_type_str = token_type.value

            if token_type == TokenType.SYMBOL:
                token = saxutils.escape(token)
            
            lines.append(f"<{token_type_str}> {token} </{token_type_str}>")

            if token.strip() == "":
                lines.append("!!! terminating for invalid token!!!")
                break
    lines.append("</tokens>")
    content = "\n".join(lines)

    output_file = input_file.replace(".jack", "T.mine.xml")
    assert input_file != output_file
    with open(output_file, "w") as f:
        f.write(content)
    print("Saved " + output_file)   


if __name__ == "__main__":
    main()

