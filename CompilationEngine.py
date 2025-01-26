import os
from JackTokenizer import JackTokenizer  # from your Project 10
from SymbolTable import SymbolTable  # from your Project 11
from typing import Optional
from VMWriter import VMWriter


class CompilationEngine:
    """
    A reference compilation engine for Jack -> VM code.
    It parses the .jack file (via a JackTokenizer) and writes .vm code.
    """

    def __init__(self, input_file_path: str, output_vm_path: str):
        """
        Creates a new compilation engine with:
          - a tokenizer (initialized on input_file_path)
          - a symbol table
          - a VMWriter (writing to output_vm_path)
        """
        # Initialize tokenizer
        self.tokenizer = JackTokenizer(input_file_path)
        self.symbol_table = SymbolTable()
        self.vm_writer = VMWriter(output_vm_path)

        self.class_name = None

        # We'll keep counters for generating unique labels in if/while statements.
        self.if_label_counter = 0
        self.while_label_counter = 0

        # Prime the tokenizer if needed:
        # (Depending on your tokenizer, you might need to self.tokenizer.advance() here.)
        # If your tokenizer auto-advances, skip this.

    def close(self):
        """ Close the VMWriter output. """
        self.vm_writer.close()

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def kind_to_segment(self, kind: Optional[str]) -> Optional[str]:
        """
        Convert a symbol table 'kind' to a VM segment name.
        Returns None if not applicable.
        """
        if kind == 'static':
            return 'static'
        elif kind == 'field':
            return 'this'
        elif kind == 'arg':
            return 'argument'
        elif kind == 'var':
            return 'local'
        return None

    def eat(self, token_value=None):
        """
        Utility method: Check the current token and advance.
        If token_value is given, optionally validate the current token is what we expect.
        Adjust as needed for your own error handling or debugging.
        """
        # e.g. if token_value is '(' and the current token isn't '(' => raise error
        # or just skip checks to keep minimal
        self.tokenizer.advance()

    def get_identifier(self) -> str:
        """ Return the current token as an identifier string, then advance. """
        name = self.tokenizer.identifier()
        self.tokenizer.advance()
        return name

    # ---------------------------------------------------------
    # 1) compileClass
    # ---------------------------------------------------------
    def compile_class(self):
        """
        Compiles a complete class:
          'class' className '{' classVarDec* subroutineDec* '}'
        """
        # current token should be 'class'
        self.eat()  # skip 'class'

        # className
        self.class_name = self.tokenizer.currentToken
        self.eat()  # skip className

        # '{'
        self.eat()  # skip '{'

        # classVarDec*  (static | field)
        while self.tokenizer.token_type() == 'KEYWORD' and \
                self.tokenizer.keyWord() in ['static', 'field']:
            self.compile_class_var_dec()

        # subroutineDec* (constructor | function | method)
        while self.tokenizer.token_type() == 'KEYWORD' and \
                self.tokenizer.keyWord() in ['constructor', 'function', 'method']:
            self.compile_subroutine()

        # '}'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '}':
            self.eat()  # skip '}'

    # ---------------------------------------------------------
    # 2) compileClassVarDec
    # ---------------------------------------------------------
    def compile_class_var_dec(self):
        """
        Compiles a static or field declaration:
          ('static' | 'field') type varName (',' varName)* ';'
        """
        kind = self.tokenizer.keyWord()  # 'static' or 'field'
        self.eat()  # skip the keyword

        var_type = self.tokenizer.currentToken  # e.g. 'int', 'boolean', 'Point', etc.
        self.eat()  # skip type

        # now parse one or more varNames
        while True:
            var_name = self.tokenizer.currentToken
            self.symbol_table.define(var_name, var_type, kind)
            self.eat()  # skip varName

            # if next token is ',', keep going
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ',':
                self.eat()  # skip ','
            else:
                break

        # semicolon
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';':
            self.eat()

    # ---------------------------------------------------------
    # 3) compileSubroutine
    # ---------------------------------------------------------
    def compile_subroutine(self):
        """
        Compiles a complete subroutine:
          ('constructor' | 'function' | 'method')
          ('void' | type) subroutineName '(' parameterList ')' subroutineBody
        """
        # Clear the subroutine scope
        self.symbol_table.startSubroutine()

        subroutine_type = self.tokenizer.keyWord()  # constructor|function|method
        self.eat()  # skip it

        # return type (void or type)
        self.eat()  # skip return type

        # subroutine name
        subroutine_name = self.tokenizer.currentToken
        self.eat()  # skip subroutineName

        # If it's a method, the hidden "this" is arg 0
        if subroutine_type == 'method':
            self.symbol_table.define("this", self.class_name, "arg")

        # '('
        self.eat()  # skip '('
        # parameterList
        self.compile_parameter_list()
        # ')'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')':
            self.eat()

        # subroutineBody
        self.compile_subroutine_body(subroutine_type, subroutine_name)

    def compile_parameter_list(self):
        """
        Compiles a (possibly empty) parameter list.
        (type varName) (',' type varName)* ?
        """
        # Keep reading until we see ')'
        while not (self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')'):
            var_type = self.tokenizer.currentToken
            self.eat()  # skip type

            var_name = self.tokenizer.currentToken
            self.symbol_table.define(var_name, var_type, 'arg')
            self.eat()  # skip varName

            # if comma, keep going
            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ',':
                self.eat()
            else:
                break

    def compile_subroutine_body(self, subroutine_type: str, subroutine_name: str):
        """
        Compiles the subroutine body: '{' varDec* statements '}'
        Also handles function/method/constructor initial code generation.
        """
        # '{'
        self.eat()  # skip '{'

        # varDec*
        while self.tokenizer.token_type() == 'KEYWORD' and self.tokenizer.keyWord() == 'var':
            self.compile_var_dec()

        # Now we know how many local variables
        n_locals = self.symbol_table.varCount("var")
        full_name = f"{self.class_name}.{subroutine_name}"
        # Write function label
        self.vm_writer.writeFunction(full_name, n_locals)

        # If constructor => allocate memory for fields
        if subroutine_type == 'constructor':
            n_fields = self.symbol_table.varCount('field')
            self.vm_writer.writePush("constant", n_fields)
            self.vm_writer.writeCall("Memory.alloc", 1)
            # pop that pointer into pointer 0 => 'this'
            self.vm_writer.writePop("pointer", 0)

        # If method => set pointer 0 to argument 0
        if subroutine_type == 'method':
            self.vm_writer.writePush("argument", 0)
            self.vm_writer.writePop("pointer", 0)

        # compile statements
        self.compile_statements()

        # '}'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '}':
            self.eat()

    # ---------------------------------------------------------
    # 4) compileVarDec
    # ---------------------------------------------------------
    def compile_var_dec(self):
        """
        'var' type varName (',' varName)* ';'
        """
        self.eat()  # skip 'var'

        var_type = self.tokenizer.currentToken
        self.eat()  # skip type

        while True:
            var_name = self.tokenizer.currentToken
            self.symbol_table.define(var_name, var_type, 'var')
            self.eat()  # skip varName

            if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ',':
                self.eat()  # skip comma
            else:
                break

        # semicolon
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';':
            self.eat()

    # ---------------------------------------------------------
    # 5) compileStatements
    # ---------------------------------------------------------
    def compile_statements(self):
        """
        Possible statements: let, if, while, do, return
        """
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

    # ---------------------------------------------------------
    # 6) compileLet
    # ---------------------------------------------------------
    def compile_let(self):
        """
        let varName ('[' expression ']')? = expression ;
        """
        self.eat()  # skip 'let'

        var_name = self.tokenizer.currentToken
        kind = self.symbol_table.kindOf(var_name)
        index = self.symbol_table.indexOf(var_name)
        segment = self.kind_to_segment(kind)

        self.eat()  # skip varName

        array_access = False
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '[':
            array_access = True
            # handle array => we push base address + index
            self.eat()  # skip '['
            self.compile_expression()  # pushes index expression
            self.eat()  # skip ']'
            # now push var_name's base address
            self.vm_writer.writePush(segment, index)
            # add
            self.vm_writer.writeArithmetic("add")

        # skip '='
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '=':
            self.eat()

        self.compile_expression()  # push expression's value on stack

        # skip ';'
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';':
            self.eat()

        if array_access:
            # For array assignment:
            # top of stack is value, second on stack is address
            # pop temp 0
            self.vm_writer.writePop("temp", 0)
            # pop pointer 1
            self.vm_writer.writePop("pointer", 1)
            # push temp 0
            self.vm_writer.writePush("temp", 0)
            # pop that 0
            self.vm_writer.writePop("that", 0)
        else:
            # normal var assignment
            self.vm_writer.writePop(segment, index)

    # ---------------------------------------------------------
    # 7) compileIf
    # ---------------------------------------------------------
    def compile_if(self):
        """
        if ( expression ) { statements } ( else { statements } )?
        """
        self.eat()  # skip 'if'
        # skip '('
        self.eat()

        # compile expression => pushes result (true=>-1, false=>0)
        self.compile_expression()

        # skip ')'
        self.eat()

        label_false = f"IF_FALSE{self.if_label_counter}"
        label_end = f"IF_END{self.if_label_counter}"
        self.if_label_counter += 1

        # We want to jump to IF_FALSE if expression == false
        # expression==true => top of stack is non-zero => "if-goto" jumps if not 0
        self.vm_writer.writeArithmetic("not")  # not the value => 0 if true
        self.vm_writer.writeIf(label_false)

        # skip '{'
        self.eat()
        self.compile_statements()
        # skip '}'
        self.eat()

        # optional else
        if self.tokenizer.token_type() == 'KEYWORD' and self.tokenizer.keyWord() == 'else':
            # if true, jump to label_end
            self.vm_writer.writeGoto(label_end)

            # place label_false
            self.vm_writer.writeLabel(label_false)

            self.eat()  # skip 'else'
            # skip '{'
            self.eat()
            self.compile_statements()
            # skip '}'
            self.eat()

            # label_end
            self.vm_writer.writeLabel(label_end)
        else:
            # no else => just place label_false
            self.vm_writer.writeLabel(label_false)

    # ---------------------------------------------------------
    # 8) compileWhile
    # ---------------------------------------------------------
    def compile_while(self):
        """
        while ( expression ) { statements }
        """
        self.eat()  # skip 'while'

        label_exp = f"WHILE_EXP{self.while_label_counter}"
        label_end = f"WHILE_END{self.while_label_counter}"
        self.while_label_counter += 1

        # write label_exp
        self.vm_writer.writeLabel(label_exp)

        # skip '('
        self.eat()
        self.compile_expression()
        # skip ')'
        self.eat()

        # not the top => if-goto label_end if expression == false
        self.vm_writer.writeArithmetic("not")
        self.vm_writer.writeIf(label_end)

        # skip '{'
        self.eat()
        self.compile_statements()
        # skip '}'
        self.eat()

        # goto label_exp
        self.vm_writer.writeGoto(label_exp)
        # label_end
        self.vm_writer.writeLabel(label_end)

    # ---------------------------------------------------------
    # 9) compileDo
    # ---------------------------------------------------------
    def compile_do(self):
        """
        do subroutineCall ;
        """
        self.eat()  # skip 'do'

        self.compile_subroutine_call()

        # we get return value on stack => discard
        self.vm_writer.writePop("temp", 0)

        # skip ';'
        self.eat()

    def compile_subroutine_call(self):
        """
        subroutineCall => (className|varName|subroutineName)
                          ('.' subroutineName)? '(' expressionList ')'
        We must figure out if the first identifier is an object, the class name, or a subroutine in the same class.
        """
        identifier = self.tokenizer.currentToken
        self.eat()  # skip the identifier

        num_args = 0

        # check if identifier is a variable in symbol table
        kind = self.symbol_table.kindOf(identifier)
        if kind is not None:
            # it's a variable => method call on some object
            # push that object reference
            segment = self.kind_to_segment(kind)
            index = self.symbol_table.indexOf(identifier)
            self.vm_writer.writePush(segment, index)
            # the fullName we call will be TypeOfVar.subName
            obj_type = self.symbol_table.typeOf(identifier)
            is_method_call = True
        else:
            # might be a function in the same class or some other class
            obj_type = identifier
            is_method_call = False

        subroutine_name = None

        # if next token is '.', we have a name. e.g. "Circle.new"
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '.':
            self.eat()  # skip '.'
            subroutine_name = self.tokenizer.currentToken
            self.eat()  # skip subroutineName
        else:
            # no '.', so it's "identifier(...)"
            # means subroutine is in *this* class
            subroutine_name = identifier
            is_method_call = True
            # we also want to push 'this' as arg0 for method calls in the same class
            self.vm_writer.writePush("pointer", 0)

        # '('
        self.eat()  # skip '('
        # compile expressionList => returns number of arguments
        n_expressions = self.compile_expression_list()
        # ')'
        self.eat()

        # If it's a method call, either we found a varName or it's an implicit this
        if is_method_call:
            n_expressions += 1  # account for object reference as arg0

        full_call_name = ""
        if kind is not None:
            # varName.subroutine =>  TypeOfVar.subroutine
            full_call_name = f"{obj_type}.{subroutine_name}"
        elif is_method_call:
            # same class method
            full_call_name = f"{self.class_name}.{subroutine_name}"
        else:
            # className.functionName
            full_call_name = f"{obj_type}.{subroutine_name}"

        # now call
        self.vm_writer.writeCall(full_call_name, n_expressions)

    # ---------------------------------------------------------
    # 10) compileReturn
    # ---------------------------------------------------------
    def compile_return(self):
        """
        return expression? ;
        """
        self.eat()  # skip 'return'

        # if next token isn't ';', compile expression
        if not (self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ';'):
            self.compile_expression()
        else:
            # push constant 0 as a dummy
            self.vm_writer.writePush("constant", 0)

        # skip ';'
        self.eat()

        self.vm_writer.writeReturn()

    # ---------------------------------------------------------
    # 11) compileExpression
    # ---------------------------------------------------------
    def compile_expression(self):
        """
        expression => term (op term)*
        """
        self.compile_term()

        # while next token is an operator
        while (self.tokenizer.token_type() == 'SYMBOL'
               and self.tokenizer.symbol() in ['+', '-', '*', '/', '&', '|', '<', '>', '=']):
            op = self.tokenizer.symbol()
            self.eat()  # skip the operator
            self.compile_term()

            # handle the operator
            if op == '+':
                self.vm_writer.writeArithmetic("add")
            elif op == '-':
                self.vm_writer.writeArithmetic("sub")
            elif op == '*':
                self.vm_writer.writeCall("Math.multiply", 2)
            elif op == '/':
                self.vm_writer.writeCall("Math.divide", 2)
            elif op == '&':
                self.vm_writer.writeArithmetic("and")
            elif op == '|':
                self.vm_writer.writeArithmetic("or")
            elif op == '<':
                self.vm_writer.writeArithmetic("lt")
            elif op == '>':
                self.vm_writer.writeArithmetic("gt")
            elif op == '=':
                self.vm_writer.writeArithmetic("eq")

    # ---------------------------------------------------------
    # 12) compileTerm
    # ---------------------------------------------------------
    def compile_term(self):
        """
        term => integerConstant | stringConstant | keywordConstant
              | varName | varName '[' expression ']'
              | subroutineCall
              | '(' expression ')'
              | unaryOp term
        """
        token_type = self.tokenizer.token_type()

        if token_type == 'INT_CONST':
            val = self.tokenizer.intVal()
            self.vm_writer.writePush("constant", val)
            self.eat()
        elif token_type == 'STRING_CONST':
            string_val = self.tokenizer.stringVal()
            self.compile_string_constant(string_val)
            self.eat()
        elif token_type == 'KEYWORD':
            # could be true, false, null, this
            kw = self.tokenizer.keyWord()
            if kw == 'true':
                self.vm_writer.writePush("constant", 0)
                self.vm_writer.writeArithmetic("not")  # true => -1
            elif kw in ['false', 'null']:
                self.vm_writer.writePush("constant", 0)
            elif kw == 'this':
                self.vm_writer.writePush("pointer", 0)
            self.eat()
        elif token_type == 'SYMBOL':
            # '(' expression ')' or unaryOp term
            sym = self.tokenizer.symbol()
            if sym == '(':
                self.eat()  # skip '('
                self.compile_expression()
                self.eat()  # skip ')'
            elif sym in ['-', '~']:
                # unary op
                unary_op = sym
                self.eat()
                self.compile_term()
                if unary_op == '-':
                    self.vm_writer.writeArithmetic("neg")
                else:  # '~'
                    self.vm_writer.writeArithmetic("not")
        elif token_type == 'IDENTIFIER':
            # Could be varName, array access, or subroutine call
            # We'll do a mini-check
            name = self.tokenizer.currentToken
            self.eat()  # skip identifier

            if self.tokenizer.token_type() == 'SYMBOL':
                sym = self.tokenizer.symbol()
                if sym == '[':
                    # array access
                    kind = self.symbol_table.kindOf(name)
                    index = self.symbol_table.indexOf(name)
                    segment = self.kind_to_segment(kind)

                    # push base address
                    self.vm_writer.writePush(segment, index)
                    self.eat()  # skip '['
                    self.compile_expression()
                    self.eat()  # skip ']'
                    self.vm_writer.writeArithmetic("add")
                    # pop pointer 1, then push that 0
                    self.vm_writer.writePop("pointer", 1)
                    self.vm_writer.writePush("that", 0)
                elif sym in ['(', '.']:
                    # subroutine call: we already consumed 'name'
                    # put it back somehow, or handle carefully
                    # simplest approach: we do a small hack: re-inject
                    self._compile_subroutine_call_after_first(name)
                else:
                    # just a varName
                    kind = self.symbol_table.kindOf(name)
                    index = self.symbol_table.indexOf(name)
                    seg = self.kind_to_segment(kind)
                    self.vm_writer.writePush(seg, index)
            else:
                # just a varName
                kind = self.symbol_table.kindOf(name)
                index = self.symbol_table.indexOf(name)
                seg = self.kind_to_segment(kind)
                self.vm_writer.writePush(seg, index)

    def _compile_subroutine_call_after_first(self, first_identifier):
        """
        Helper for the situation where we recognized 'identifier' but next token is '(' or '.'.
        We'll replicate the logic from compile_subroutine_call but we already have first_identifier.
        """
        num_args = 0
        kind = self.symbol_table.kindOf(first_identifier)
        if kind is not None:
            # it's a variable => method call on that object
            segment = self.kind_to_segment(kind)
            index = self.symbol_table.indexOf(first_identifier)
            self.vm_writer.writePush(segment, index)
            obj_type = self.symbol_table.typeOf(first_identifier)
            is_method_call = True
        else:
            # might be a function in same class or other class
            obj_type = first_identifier
            is_method_call = False

        subroutine_name = None
        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '.':
            self.eat()  # skip '.'
            subroutine_name = self.tokenizer.currentToken
            self.eat()
        else:
            # no '.', so it's a method call on 'this'
            subroutine_name = first_identifier
            is_method_call = True
            # push 'this'
            self.vm_writer.writePush("pointer", 0)

        if self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == '(':
            self.eat()  # skip '('
            n_expr = self.compile_expression_list()
            self.eat()  # skip ')'
        else:
            n_expr = 0

        if is_method_call:
            n_expr += 1  # for the object reference

        if kind is not None:
            full_name = f"{obj_type}.{subroutine_name}"
        elif is_method_call:
            full_name = f"{self.class_name}.{subroutine_name}"
        else:
            full_name = f"{obj_type}.{subroutine_name}"

        self.vm_writer.writeCall(full_name, n_expr)

    # ---------------------------------------------------------
    # 13) compileExpressionList
    # ---------------------------------------------------------
    def compile_expression_list(self) -> int:
        """
        Compiles a possibly empty comma-separated list of expressions.
        Returns the number of expressions compiled.
        """
        count = 0
        # if next token isn't ')', we have at least one expression
        if not (self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ')'):
            self.compile_expression()
            count += 1

            # while comma, compile next expression
            while self.tokenizer.token_type() == 'SYMBOL' and self.tokenizer.symbol() == ',':
                self.eat()  # skip ','
                self.compile_expression()
                count += 1

        return count

    # ---------------------------------------------------------
    # Utility for string constants
    # ---------------------------------------------------------
    def compile_string_constant(self, string_val: str):
        """
        For a string "Hello", we do:
          push length
          call String.new 1
          then for each character c:
              push c's ascii
              call String.appendChar 2
        """
        length = len(string_val)
        # push length
        self.vm_writer.writePush("constant", length)
        # call String.new 1
        self.vm_writer.writeCall("String.new", 1)

        # for each character
        for ch in string_val:
            self.vm_writer.writePush("constant", ord(ch))  # ASCII code
            self.vm_writer.writeCall("String.appendChar", 2)
