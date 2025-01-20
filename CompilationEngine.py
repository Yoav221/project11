from JackTokenizer import JackTokenizer  # <-- your tokenizer from Project 10
from symboltable import SymbolTable      # import the SymbolTable above

class CompilationEngine:
    def __init__(self, input_file_path, output_path):
        """
        Initialize the compilation engine:
         1) create a tokenizer for the .jack input
         2) create an output .xml file
         3) create a symbol table
        """
        self.indent_level = 0
        try:
            self.tokenizer = JackTokenizer(input_file_path)
            if self.tokenizer.tokenLength == 0:
                raise Exception(f"Input file {input_file_path} is empty or invalid")
        except Exception as e:
            raise Exception(f"Failed to initialize tokenizer: {str(e)}")

        try:
            self.output = open(output_path, "w+")
        except Exception as e:
            raise Exception(f"Failed to open output file {output_path}: {str(e)}")

        # Create the symbol table
        self.symbol_table = SymbolTable()

    def close(self):
        """Close the output file when done."""
        if hasattr(self, 'output') and self.output:
            self.output.flush()
            self.output.close()

    # -------------------------------------------------
    #  Utility methods for writing XML
    # -------------------------------------------------

    def write_element(self, tag, value):
        """Write a single-line element <tag> value </tag> with indentation."""
        indent = '  ' * self.indent_level
        self.output.write(f"{indent}<{tag}> {value} </{tag}>\n")
        self.output.flush()

    def write_xml_tag(self, tag):
        """Write an opening or closing XML tag with indentation."""
        if tag.startswith('/'):  # closing tag
            self.indent_level -= 1
            indent = '  ' * self.indent_level
            self.output.write(f"{indent}<{tag}>\n")
        else:
            indent = '  ' * self.indent_level
            self.output.write(f"{indent}<{tag}>\n")
            self.indent_level += 1
        self.output.flush()

    def write_annotated_identifier(self, name, usage="used", kind=None):
        """
        Writes <identifier ...> with symbol table info, if any.
         usage = "declared" or "used"
         kind  = "static", "field", "arg", "var", or None
        """
        if kind is None:
            # Try to look up in symbol table
            kind = self.symbol_table.kindOf(name)
        index = None
        if kind in ("static", "field", "arg", "var"):
            index = self.symbol_table.indexOf(name)

        # Compose the XML line
        indent = '  ' * self.indent_level
        kind_str = kind if kind else "UNKNOWN"
        idx_str = str(index) if index is not None else ""
        self.output.write(
            f'{indent}<identifier category="{kind_str}" index="{idx_str}" usage="{usage}"> {name} </identifier>\n'
        )
        self.output.flush()

    def write_current_token(self):
        """
        Helper method to write the current token **without** symbol table annotation.
        Used for keywords, symbols, int/string constants.
        """
        token_type = self.tokenizer.token_type()
        if token_type == 'KEYWORD':
            self.write_element('keyword', self.tokenizer.keyWord())
        elif token_type == 'SYMBOL':
            symbol = self.tokenizer.symbol()
            # Escape special XML
            if symbol == '<':
                symbol = '&lt;'
            elif symbol == '>':
                symbol = '&gt;'
            elif symbol == '&':
                symbol = '&amp;'
            self.write_element('symbol', symbol)
        elif token_type == 'IDENTIFIER':
            # If we get here, we do NOT do annotated output, but in project 11,
            # you'll normally do it in compileXxx methods directly.
            self.write_element('identifier', self.tokenizer.identifier())
        elif token_type == 'INT_CONST':
            self.write_element('integerConstant', str(self.tokenizer.intVal()))
        elif token_type == 'STRING_CONST':
            self.write_element('stringConstant', self.tokenizer.stringVal())

    # -------------------------------------------------
    #  Compilation methods
    # -------------------------------------------------

    def compile_class(self):
        """
        Compiles a complete class:
          'class' className '{' classVarDec* subroutineDec* '}'
        """
        # Expect 'class'
        if self.tokenizer.token_type() == 'KEYWORD' and self.tokenizer.keyWord() == 'class':
            self.write_xml_tag('class')
            self.write_current_token()  # 'class'
            self.tokenizer.advance()

            # className
            class_name = self.tokenizer.currentToken
            self.write_annotated_identifier(class_name, usage="used", kind=None)  # class name not in symbol table
            self.tokenizer.advance()

            # '{'
            self.write_current_token()  # '{'
            self.tokenizer.advance()

            # Now compile zero or more classVarDec
            while self.tokenizer.token_type() == 'KEYWORD' and \
                  self.tokenizer.keyWord() in ['static', 'field']:
                self.compile_class_var_dec()

            # Then compile zero or more subroutineDec
            while self.tokenizer.token_type() == 'KEYWORD' and \
                  self.tokenizer.keyWord() in ['constructor', 'function', 'method']:
                self.compile_subroutine()

            # '}'
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '}':
                self.write_current_token()

            self.write_xml_tag('/class')

    def compile_class_var_dec(self):
        """
        Compiles a static variable declaration or a field declaration.
        Syntax:
            ('static' | 'field') type varName (',' varName)* ';'
        """
        self.write_xml_tag('classVarDec')

        kind = self.tokenizer.keyWord()  # 'static' or 'field'
        self.write_current_token()       # write <keyword>static</keyword> or <keyword>field</keyword>
        self.tokenizer.advance()

        var_type = self.tokenizer.currentToken  # e.g. 'int', 'boolean', 'Point', etc.
        self.write_current_token()
        self.tokenizer.advance()

        # Now we can have multiple varNames
        while True:
            var_name = self.tokenizer.currentToken
            # Define in symbol table
            self.symbol_table.define(var_name, var_type, kind)
            # Annotated identifier: usage="declared"
            self.write_annotated_identifier(var_name, usage="declared", kind=kind)
            self.tokenizer.advance()

            # If next token is ',', we have more variable names
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ',':
                self.write_current_token()  # write ','
                self.tokenizer.advance()
            else:
                break

        # Semicolon
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';':
            self.write_current_token()
            self.tokenizer.advance()

        self.write_xml_tag('/classVarDec')

    def compile_subroutine(self):
        """
        Compiles a complete subroutine: constructor, function, or method.
        Syntax:
          ('constructor' | 'function' | 'method')
          ('void' | type) subroutineName
          '(' parameterList ')' subroutineBody
        """
        self.write_xml_tag('subroutineDec')

        # Reset subroutine scope
        self.symbol_table.startSubroutine()

        # constructor / function / method
        self.write_current_token()
        self.tokenizer.advance()

        # return type (void or type)
        self.write_current_token()
        self.tokenizer.advance()

        # subroutine name (not in table the same way, treat as used)
        subroutine_name = self.tokenizer.currentToken
        self.write_annotated_identifier(subroutine_name, usage="used", kind=None)
        self.tokenizer.advance()

        # '('
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '(':
            self.write_current_token()
            self.tokenizer.advance()

            # parameterList
            self.compile_parameter_list()

            # ')'
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')':
                self.write_current_token()
                self.tokenizer.advance()

        # subroutineBody
        self.compile_subroutine_body()

        self.write_xml_tag('/subroutineDec')

    def compile_parameter_list(self):
        """
        Compiles a (possibly empty) parameter list.
        Syntax:
          ((type varName) (',' type varName)*)?
        """
        self.write_xml_tag('parameterList')

        # Keep reading until we hit ')'
        while not (self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')'):
            param_type = self.tokenizer.currentToken  # e.g. 'int'
            self.write_current_token()
            self.tokenizer.advance()

            param_name = self.tokenizer.currentToken
            # define param as 'arg'
            self.symbol_table.define(param_name, param_type, "arg")
            self.write_annotated_identifier(param_name, usage="declared", kind="arg")
            self.tokenizer.advance()

            # If comma, continue
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ',':
                self.write_current_token()  # comma
                self.tokenizer.advance()
            else:
                break

        self.write_xml_tag('/parameterList')

    def compile_subroutine_body(self):
        """
        Compiles the subroutine body:
          '{' varDec* statements '}'
        """
        self.write_xml_tag('subroutineBody')

        # '{'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '{':
            self.write_current_token()
            self.tokenizer.advance()

            # varDec*
            while self.tokenizer.token_type() == 'KEYWORD' and self.tokenizer.keyWord() == 'var':
                self.compile_var_dec()

            # statements
            self.compile_statements()

            # '}'
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '}':
                self.write_current_token()
                self.tokenizer.advance()

        self.write_xml_tag('/subroutineBody')

    def compile_var_dec(self):
        """
        Compiles a var declaration:
          var type varName (',' varName)* ';'
        """
        self.write_xml_tag('varDec')

        # 'var'
        self.write_current_token()
        self.tokenizer.advance()

        var_type = self.tokenizer.currentToken
        self.write_current_token()
        self.tokenizer.advance()

        while True:
            var_name = self.tokenizer.currentToken
            # define as 'var'
            self.symbol_table.define(var_name, var_type, "var")
            self.write_annotated_identifier(var_name, usage="declared", kind="var")
            self.tokenizer.advance()

            # comma means more varNames
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ',':
                self.write_current_token()
                self.tokenizer.advance()
            else:
                break

        # semicolon
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';':
            self.write_current_token()
            self.tokenizer.advance()

        self.write_xml_tag('/varDec')

    def compile_statements(self):
        """
        Compiles a sequence of statements.
          letStatement | ifStatement | whileStatement | doStatement | returnStatement
        """
        self.write_xml_tag('statements')

        while self.tokenizer.token_type() == 'KEYWORD':
            kw = self.tokenizer.keyWord()
            if kw == 'let':
                self.compile_let()
            elif kw == 'if':
                self.compile_if()
            elif kw == 'while':
                self.compile_while()
            elif kw == 'do':
                self.compile_do()
            elif kw == 'return':
                self.compile_return()
            else:
                break

        self.write_xml_tag('/statements')

    def compile_let(self):
        """
        Compiles a let statement:
          let varName ('[' expression ']')? = expression ;
        """
        self.write_xml_tag('letStatement')

        # 'let'
        self.write_current_token()
        self.tokenizer.advance()

        # varName
        var_name = self.tokenizer.currentToken
        # usage="used", we look up kind/index in symbol table
        self.write_annotated_identifier(var_name, usage="used")
        self.tokenizer.advance()

        # array access?
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '[':
            self.write_current_token()
            self.tokenizer.advance()

            self.compile_expression()

            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ']':
                self.write_current_token()
                self.tokenizer.advance()

        # '='
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '=':
            self.write_current_token()
            self.tokenizer.advance()

        # expression
        self.compile_expression()

        # ';'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';':
            self.write_current_token()
            self.tokenizer.advance()

        self.write_xml_tag('/letStatement')

    def compile_if(self):
        """
        Compiles an if statement:
          if ( expression ) { statements } (else { statements })?
        """
        self.write_xml_tag('ifStatement')

        # 'if'
        self.write_current_token()
        self.tokenizer.advance()

        # '('
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '(':
            self.write_current_token()
            self.tokenizer.advance()

        self.compile_expression()

        # ')'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')':
            self.write_current_token()
            self.tokenizer.advance()

        # '{'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '{':
            self.write_current_token()
            self.tokenizer.advance()

        self.compile_statements()

        # '}'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '}':
            self.write_current_token()
            self.tokenizer.advance()

        # optional else
        if self.tokenizer.token_type() == 'KEYWORD' and self.tokenizer.keyWord() == 'else':
            self.write_current_token()
            self.tokenizer.advance()

            # '{'
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '{':
                self.write_current_token()
                self.tokenizer.advance()

            self.compile_statements()

            # '}'
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '}':
                self.write_current_token()
                self.tokenizer.advance()

        self.write_xml_tag('/ifStatement')

    def compile_while(self):
        """
        Compiles a while statement:
          while ( expression ) { statements }
        """
        self.write_xml_tag('whileStatement')

        # 'while'
        self.write_current_token()
        self.tokenizer.advance()

        # '('
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '(':
            self.write_current_token()
            self.tokenizer.advance()

        self.compile_expression()

        # ')'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')':
            self.write_current_token()
            self.tokenizer.advance()

        # '{'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '{':
            self.write_current_token()
            self.tokenizer.advance()

        self.compile_statements()

        # '}'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '}':
            self.write_current_token()
            self.tokenizer.advance()

        self.write_xml_tag('/whileStatement')

    def compile_do(self):
        """
        Compiles a do statement:
          do subroutineCall ;
        """
        self.write_xml_tag('doStatement')

        # 'do'
        self.write_current_token()
        self.tokenizer.advance()

        # subroutineCall => identifier [( '.' identifier )] '(' expressionList ')'
        self.compile_subroutine_call()

        # ';'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';':
            self.write_current_token()
            self.tokenizer.advance()

        self.write_xml_tag('/doStatement')

    def compile_return(self):
        """
        Compiles a return statement:
          return expression? ;
        """
        self.write_xml_tag('returnStatement')

        # 'return'
        self.write_current_token()
        self.tokenizer.advance()

        # Optional expression
        if not (self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';'):
            self.compile_expression()

        # ';'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';':
            self.write_current_token()
            self.tokenizer.advance()

        self.write_xml_tag('/returnStatement')

    def compile_expression(self):
        """
        Compiles an expression:
          term (op term)*
        """
        self.write_xml_tag('expression')

        self.compile_term()

        # While next token is an operator
        while (self.tokenizer.token_type() == 'SYMBOL' and
               self.tokenizer.symbol() in ['+', '-', '*', '/', '&', '|', '<', '>', '=']):
            self.write_current_token()  # operator
            self.tokenizer.advance()
            self.compile_term()

        self.write_xml_tag('/expression')

    def compile_term(self):
        """
        Compiles a term. This can be:
          integerConstant | stringConstant | keywordConstant
          | varName
          | varName '[' expression ']'
          | subroutineCall
          | '(' expression ')'
          | unaryOp term
        """
        self.write_xml_tag('term')

        token_type = self.tokenizer.token_type()

        if token_type == 'INT_CONST':
            self.write_current_token()
            self.tokenizer.advance()
        elif token_type == 'STRING_CONST':
            self.write_current_token()
            self.tokenizer.advance()
        elif token_type == 'KEYWORD' and self.tokenizer.keyWord() in ['true', 'false', 'null', 'this']:
            self.write_current_token()
            self.tokenizer.advance()
        elif token_type == 'IDENTIFIER':
            # Could be varName or subroutineCall or array access
            # Let's peek the next token to decide
            name = self.tokenizer.currentToken
            self.tokenizer.advance()

            # If next token is '[' => array access
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '[':
                # varName usage=used
                self.write_annotated_identifier(name, usage="used")
                self.write_current_token()  # '['
                self.tokenizer.advance()

                self.compile_expression()

                # ']'
                if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ']':
                    self.write_current_token()
                    self.tokenizer.advance()
            # If next token is '(' or '.', it's a subroutine call
            elif self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() in ['(', '.']:
                # We jumped one token ahead, so let's handle that
                self.write_annotated_identifier(name, usage="used")
                self.compile_subroutine_call_continuation()
            else:
                # It's just a varName
                self.write_annotated_identifier(name, usage="used")
                # No more to do

        elif token_type == 'SYMBOL':
            symbol_ = self.tokenizer.symbol()
            if symbol_ == '(':
                self.write_current_token()  # '('
                self.tokenizer.advance()
                self.compile_expression()
                if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')':
                    self.write_current_token()
                    self.tokenizer.advance()
            elif symbol_ in ['-', '~']:
                # unaryOp
                self.write_current_token()
                self.tokenizer.advance()
                self.compile_term()

        self.write_xml_tag('/term')

    def compile_subroutine_call(self):
        """
        For a do-statement or anywhere a subroutineCall appears:
           subroutineCall => identifier ( '.' identifier )? '(' expressionList ')'
        """
        first_identifier = self.tokenizer.currentToken
        self.tokenizer.advance()

        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() in ['(', '.']:
            # We do annotated write for the first identifier here
            self.write_annotated_identifier(first_identifier, usage="used")
            self.compile_subroutine_call_continuation()
        else:
            # It's just an identifier that wasn't followed by '(' or '.'
            # (Rare, but let's handle gracefully)
            self.write_annotated_identifier(first_identifier, usage="used")

    def compile_subroutine_call_continuation(self):
        """
        Handles the part after we see an identifier, then either a '.' or '('
        => '.' identifier '(' expressionList ')' or '(' expressionList ')'
        """
        # If it's '.', we expect another identifier for method name
        if self.tokenizer.symbol() == '.':
            self.write_current_token()  # '.'
            self.tokenizer.advance()
            if self.tokenizer.token_type() == 'IDENTIFIER':
                method_name = self.tokenizer.currentToken
                # usage=used (could be a subroutineName)
                self.write_annotated_identifier(method_name, usage="used", kind=None)
                self.tokenizer.advance()

        # Now we expect '('
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '(':
            self.write_current_token()
            self.tokenizer.advance()

            self.compile_expression_list()

            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')':
                self.write_current_token()
                self.tokenizer.advance()

    def compile_expression_list(self):
        """
        compiles a (possibly empty) comma-separated list of expressions.
        """
        self.write_xml_tag('expressionList')

        # if next token isn't ')', compile an expression
        if not (self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')'):
            self.compile_expression()

            # while comma, compile next expression
            while self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ',':
                self.write_current_token()
                self.tokenizer.advance()
                self.compile_expression()

        self.write_xml_tag('/expressionList')
