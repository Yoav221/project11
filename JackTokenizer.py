import re

class JackTokenizer:
    def __init__(self, input_file):
        self.input_file = input_file

        # 1) Build the token list
        self.listOfTokens = self.cleanAndTokenize(input_file)
        self.tokenLength = len(self.listOfTokens)

        # 2) Set up currentToken, currentTokenIndex
        if self.tokenLength == 0:
            self.currentToken = None
            self.currentTokenIndex = -1
        else:
            self.currentTokenIndex = 0
            self.currentToken = self.listOfTokens[0]

    def cleanAndTokenize(self, input_file):
        """
        Reads the file, removes comments, then returns a list of Jack tokens by
        scanning character-by-character.
        """
        text = self.remove_comments(input_file)
        return self.tokenize(text)

    def remove_comments(self, input_file):
        """
        Removes all // and /* */ comments, returning the cleaned text as a single string.
        """
        with open(input_file, 'r') as f:
            text = f.read()

        # 1) Remove all block comments (/* ... */) with a regex (non-greedy)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

        # 2) Remove everything after // in each line
        cleaned_lines = []
        for line in text.split('\n'):
            line = line.split('//')[0]
            cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)

        return text

    def tokenize(self, text):
        """
        Goes through the cleaned text character-by-character, splitting into tokens:
        - Symbols
        - String constants in quotes
        - Integers, keywords, and identifiers
        """
        symbols = set('{}()[].,;+-*/&|<>=~')
        tokens = []

        current_token = ''
        inside_string = False

        i = 0
        while i < len(text):
            char = text[i]

            if inside_string:
                # We are inside a string constant
                current_token += char
                if char == '"':
                    # End of string constant
                    tokens.append(current_token)
                    current_token = ''
                    inside_string = False
                i += 1
            else:
                # Not inside a string
                if char.isspace():
                    # Whitespace -> end the current token (if any)
                    if current_token:
                        tokens.append(current_token)
                        current_token = ''
                    i += 1

                elif char == '"':
                    # Start of a string constant
                    # If there's a token building, first finalize it
                    if current_token:
                        tokens.append(current_token)
                        current_token = ''
                    current_token = '"'
                    inside_string = True
                    i += 1

                elif char in symbols:
                    # Symbol is a separate token
                    if current_token:
                        tokens.append(current_token)
                        current_token = ''
                    tokens.append(char)  # the symbol itself
                    i += 1

                else:
                    # Building up an identifier, keyword, or integer
                    current_token += char
                    i += 1

        # If there's any leftover token after the loop
        if current_token:
            tokens.append(current_token)

        return tokens

    def hasMoreTokens(self):
        """
        Returns True if there is a next token, False otherwise.
        """
        return (self.currentTokenIndex + 1) < self.tokenLength

    def advance(self):
        """
        Moves to the next token, if it exists.
        """
        if self.hasMoreTokens():
            self.currentTokenIndex += 1
            self.currentToken = self.listOfTokens[self.currentTokenIndex]

    def token_type(self):
        """
        Returns: 'KEYWORD', 'SYMBOL', 'IDENTIFIER', 'INT_CONST', or 'STRING_CONST'
        """
        if self.currentToken is None:
            return None

        keywords = {
            'class', 'constructor', 'function', 'method', 'field', 'static',
            'var', 'int', 'char', 'boolean', 'void', 'true', 'false', 'null',
            'this', 'let', 'do', 'if', 'else', 'while', 'return'
        }
        symbols = set('{}()[].,;+-*/&|<>=~')

        token = self.currentToken
        if token in keywords:
            return 'KEYWORD'
        elif token in symbols:
            return 'SYMBOL'
        elif token.startswith('"') and token.endswith('"'):
            return 'STRING_CONST'
        elif token.isdigit():
            return 'INT_CONST'
        else:
            return 'IDENTIFIER'

    def keyWord(self):
        return self.currentToken  # valid only if token_type == 'KEYWORD'

    def symbol(self):
        return self.currentToken  # valid only if token_type == 'SYMBOL'

    def identifier(self):
        return self.currentToken  # valid only if token_type == 'IDENTIFIER'

    def intVal(self):
        return int(self.currentToken)  # valid only if token_type == 'INT_CONST'

    def stringVal(self):
        # Strip off the leading & trailing quotes
        return self.currentToken.strip('"')