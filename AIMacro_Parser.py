#!/usr/bin/env python3
"""
AIMacro Parser - Python-to-AILang Transpiler
Lightweight parser that translates Python-like syntax to AILang
Version: 4.0

Key Features:
- Python-compatible syntax without whitespace sensitivity
- Blocks delimited by : and end;
- Function mapping through external library
- Escape blocks for direct AILang/assembly code
"""

import re
import sys
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

class TokenType(Enum):
    # Keywords
    DEF = auto()
    FUNC = auto()
    END = auto()
    RETURN = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    FOR = auto()
    WHILE = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    PASS = auto()
    IMPORT = auto()
    FROM = auto()
    AS = auto()
    TRUE = auto()
    FALSE = auto()
    NONE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    IS = auto()
    LAMBDA = auto()
    CLASS = auto()
    TRY = auto()
    EXCEPT = auto()
    FINALLY = auto()
    WITH = auto()
    
    # Escape blocks
    AILANG = auto()
    ASM = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    POWER = auto()
    ASSIGN = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    PLUSEQ = auto()
    MINUSEQ = auto()
    MULTEQ = auto()
    DIVEQ = auto()
    
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    SEMICOLON = auto()
    ARROW = auto()
    
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    FSTRING = auto()
    
    # Special
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()
    COMMENT = auto()

@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int

class AIMacroLexer:
    """Tokenizer for AIMacro language"""
    
    KEYWORDS = {
        'def': TokenType.DEF,
        'func': TokenType.FUNC,
        'end': TokenType.END,
        'return': TokenType.RETURN,
        'if': TokenType.IF,
        'elif': TokenType.ELIF,
        'else': TokenType.ELSE,
        'for': TokenType.FOR,
        'while': TokenType.WHILE,
        'in': TokenType.IN,
        'break': TokenType.BREAK,
        'continue': TokenType.CONTINUE,
        'pass': TokenType.PASS,
        'import': TokenType.IMPORT,
        'from': TokenType.FROM,
        'as': TokenType.AS,
        'True': TokenType.TRUE,
        'False': TokenType.FALSE,
        'None': TokenType.NONE,
        'and': TokenType.AND,
        'or': TokenType.OR,
        'not': TokenType.NOT,
        'is': TokenType.IS,
        'lambda': TokenType.LAMBDA,
        'class': TokenType.CLASS,
        'try': TokenType.TRY,
        'except': TokenType.EXCEPT,
        'finally': TokenType.FINALLY,
        'with': TokenType.WITH,
        'ailang': TokenType.AILANG,
        'asm': TokenType.ASM,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        
    def tokenize(self) -> List[Token]:
        """Main tokenization loop"""
        while self.pos < len(self.source):
            self._skip_whitespace()
            
            if self.pos >= len(self.source):
                break
                
            # Comments
            if self._current() == '#':
                self._skip_comment()
                continue
            
            # String literals (including f-strings)
            if self._current() in ('"', "'") or (self._current() == 'f' and self._peek() in ('"', "'")):
                self._tokenize_string()
                continue
                
            # Numbers
            if self._current().isdigit() or (self._current() == '.' and self._peek().isdigit()):
                self._tokenize_number()
                continue
                
            # Identifiers and keywords
            if self._current().isalpha() or self._current() == '_':
                self._tokenize_identifier()
                continue
                
            # Operators and delimiters
            if not self._tokenize_operator():
                self._error(f"Unexpected character: {self._current()}")
                
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens
    
    def _current(self) -> str:
        """Get current character"""
        if self.pos < len(self.source):
            return self.source[self.pos]
        return ''
    
    def _peek(self, offset: int = 1) -> str:
        """Look ahead at next character"""
        pos = self.pos + offset
        if pos < len(self.source):
            return self.source[pos]
        return ''
    
    def _advance(self) -> str:
        """Move to next character"""
        char = self._current()
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def _skip_whitespace(self):
        """Skip spaces and tabs (but not newlines for now)"""
        while self._current() in (' ', '\t'):
            self._advance()
            
    def _skip_comment(self):
        """Skip comment line"""
        while self._current() != '\n' and self.pos < len(self.source):
            self._advance()
    
    def _tokenize_string(self):
        """Parse string literal, including f-strings"""
        start_col = self.column
        is_fstring = False
        
        if self._current() == 'f':
            is_fstring = True
            self._advance()
            
        quote = self._advance()  # " or '
        value = ''
        
        while self._current() != quote:
            if self._current() == '\\':
                self._advance()
                if self._current() in ('n', 't', 'r', '\\', quote):
                    value += self._advance()
                else:
                    value += self._current()
                    self._advance()
            else:
                value += self._advance()
                
            if self.pos >= len(self.source):
                self._error("Unterminated string")
                
        self._advance()  # closing quote
        
        token_type = TokenType.FSTRING if is_fstring else TokenType.STRING
        self.tokens.append(Token(token_type, value, self.line, start_col))
    
    def _tokenize_number(self):
        """Parse number literal"""
        start_col = self.column
        value = ''
        
        # Handle hex/binary prefixes
        if self._current() == '0' and self._peek() in ('x', 'X', 'b', 'B'):
            value += self._advance()
            value += self._advance()
            while self._current().isdigit() or self._current() in 'abcdefABCDEF':
                value += self._advance()
        else:
            # Regular number
            while self._current().isdigit():
                value += self._advance()
                
            # Handle decimal point
            if self._current() == '.' and self._peek().isdigit():
                value += self._advance()
                while self._current().isdigit():
                    value += self._advance()
                    
            # Handle scientific notation
            if self._current() in ('e', 'E'):
                value += self._advance()
                if self._current() in ('+', '-'):
                    value += self._advance()
                while self._current().isdigit():
                    value += self._advance()
                    
        self.tokens.append(Token(TokenType.NUMBER, value, self.line, start_col))
    
    def _tokenize_identifier(self):
        """Parse identifier or keyword"""
        start_col = self.column
        value = ''
        
        while self._current().isalnum() or self._current() == '_':
            value += self._advance()
            
        token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
        self.tokens.append(Token(token_type, value, self.line, start_col))
    
    def _tokenize_operator(self) -> bool:
        """Parse operator or delimiter"""
        start_col = self.column
        char = self._current()
        
        # Two-character operators
        if char == '=' and self._peek() == '=':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.EQ, '==', self.line, start_col))
            return True
        elif char == '!' and self._peek() == '=':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.NE, '!=', self.line, start_col))
            return True
        elif char == '<' and self._peek() == '=':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.LE, '<=', self.line, start_col))
            return True
        elif char == '>' and self._peek() == '=':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.GE, '>=', self.line, start_col))
            return True
        elif char == '+' and self._peek() == '=':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.PLUSEQ, '+=', self.line, start_col))
            return True
        elif char == '-' and self._peek() == '=':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.MINUSEQ, '-=', self.line, start_col))
            return True
        elif char == '*' and self._peek() == '*':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.POWER, '**', self.line, start_col))
            return True
        elif char == '*' and self._peek() == '=':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.MULTEQ, '*=', self.line, start_col))
            return True
        elif char == '/' and self._peek() == '=':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.DIVEQ, '/=', self.line, start_col))
            return True
        elif char == '-' and self._peek() == '>':
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenType.ARROW, '->', self.line, start_col))
            return True
            
        # Single-character operators and delimiters
        single_char_tokens = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.MULTIPLY,
            '/': TokenType.DIVIDE,
            '%': TokenType.MODULO,
            '=': TokenType.ASSIGN,
            '<': TokenType.LT,
            '>': TokenType.GT,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            ':': TokenType.COLON,
            ';': TokenType.SEMICOLON,
            '\n': TokenType.NEWLINE,
        }
        
        if char in single_char_tokens:
            self._advance()
            self.tokens.append(Token(single_char_tokens[char], char, self.line, start_col))
            return True
            
        return False
    
    def _error(self, msg: str):
        """Raise lexer error"""
        raise SyntaxError(f"Lexer error at line {self.line}, column {self.column}: {msg}")

class AIMacroParser:
    """Parser for AIMacro language - converts to AILang AST"""
    
    def __init__(self, tokens: List[Token], function_mapper=None):
        self.tokens = tokens
        self.pos = 0
        self.function_mapper = function_mapper or FunctionMapper()
        self.output = []
        self.indent_level = 0
        
    def parse(self) -> str:
        """Main parsing loop"""
        while not self._is_at_end():
            stmt = self._parse_statement()
            if stmt:
                self.output.append(stmt)
                
        return '\n'.join(self.output)
    
    def _current(self) -> Token:
        """Get current token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None, 0, 0)
    
    def _peek(self, offset: int = 1) -> Token:
        """Look ahead at next token"""
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return Token(TokenType.EOF, None, 0, 0)
    
    def _advance(self) -> Token:
        """Move to next token"""
        token = self._current()
        self.pos += 1
        return token
    
    def _match(self, *types: TokenType) -> bool:
        """Check if current token matches any of the given types"""
        return self._current().type in types
    
    def _consume(self, type: TokenType, message: str) -> Token:
        """Consume a token of the expected type or raise error"""
        if self._current().type == type:
            return self._advance()
        self._error(message)
    
    def _is_at_end(self) -> bool:
        """Check if we've reached end of tokens"""
        return self._current().type == TokenType.EOF
    
    def _skip_newlines(self):
        """Skip newline tokens"""
        while self._match(TokenType.NEWLINE):
            self._advance()
    
    def _parse_statement(self) -> Optional[str]:
        """Parse a single statement"""
        self._skip_newlines()
        
        # Function definition
        if self._match(TokenType.DEF, TokenType.FUNC):
            return self._parse_function()
        
        # Return statement
        if self._match(TokenType.RETURN):
            return self._parse_return()
        
        # If statement
        if self._match(TokenType.IF):
            return self._parse_if()
        
        # While loop
        if self._match(TokenType.WHILE):
            return self._parse_while()
        
        # For loop
        if self._match(TokenType.FOR):
            return self._parse_for()
        
        # Escape blocks
        if self._match(TokenType.AILANG):
            return self._parse_ailang_block()
        
        if self._match(TokenType.ASM):
            return self._parse_asm_block()
        
        # Assignment or expression statement
        if self._match(TokenType.IDENTIFIER):
            return self._parse_assignment_or_call()
        
        # End block marker
        if self._match(TokenType.END):
            self._advance()
            self._consume(TokenType.SEMICOLON, "Expected ';' after 'end'")
            return "}"
        
        # Skip empty statements
        if self._match(TokenType.SEMICOLON):
            self._advance()
            return None
            
        self._advance()  # Skip unknown tokens
        return None
    
    def _parse_function(self) -> str:
        """Parse function definition"""
        self._advance()  # consume 'def' or 'func'
        
        name = self._consume(TokenType.IDENTIFIER, "Expected function name").value
        self._consume(TokenType.LPAREN, "Expected '(' after function name")
        
        params = []
        while not self._match(TokenType.RPAREN):
            param = self._consume(TokenType.IDENTIFIER, "Expected parameter name").value
            params.append(param)
            
            if self._match(TokenType.COMMA):
                self._advance()
        
        self._consume(TokenType.RPAREN, "Expected ')' after parameters")
        self._consume(TokenType.COLON, "Expected ':' after function signature")
        self._skip_newlines()
        
        # Build AILang function
        result = [f"Function.{name} {{"]
        
        # Add parameters as Input
        for param in params:
            result.append(f"    Input: {param}: Integer")
        
        result.append("    Body: {")
        
        # Parse function body
        while not self._match(TokenType.END):
            stmt = self._parse_statement()
            if stmt:
                result.append(f"        {stmt}")
        
        self._consume(TokenType.END, "Expected 'end' to close function")
        self._consume(TokenType.SEMICOLON, "Expected ';' after 'end'")
        
        result.append("    }")
        result.append("}")
        
        return '\n'.join(result)
    
    def _parse_return(self) -> str:
        """Parse return statement"""
        self._advance()  # consume 'return'
        
        if self._match(TokenType.SEMICOLON, TokenType.NEWLINE):
            return "ReturnValue(0)"
        
        expr = self._parse_expression()
        
        if self._match(TokenType.SEMICOLON):
            self._advance()
            
        return f"ReturnValue({expr})"
    
    def _parse_if(self) -> str:
        """Parse if statement"""
        self._advance()  # consume 'if'
        
        condition = self._parse_expression()
        self._consume(TokenType.COLON, "Expected ':' after if condition")
        self._skip_newlines()
        
        # Build the if statement
        result = [f"IfCondition {condition} ThenBlock {{"]
        
        # Parse then block
        while not self._match(TokenType.ELIF, TokenType.ELSE, TokenType.END):
            stmt = self._parse_statement()
            if stmt:
                result.append(f"    {stmt}")
        
        # Handle elif/else
        if self._match(TokenType.ELSE):
            self._advance()
            self._consume(TokenType.COLON, "Expected ':' after else")
            self._skip_newlines()
            
            result.append("} ElseBlock {")
            
            while not self._match(TokenType.END):
                stmt = self._parse_statement()
                if stmt:
                    result.append(f"    {stmt}")
        
        self._consume(TokenType.END, "Expected 'end' to close if statement")
        self._consume(TokenType.SEMICOLON, "Expected ';' after 'end'")
        
        result.append("}")
        
        return '\n'.join(result)
    
    def _parse_while(self) -> str:
        """Parse while loop"""
        self._advance()  # consume 'while'
        
        condition = self._parse_expression()
        self._consume(TokenType.COLON, "Expected ':' after while condition")
        self._skip_newlines()
        
        result = [f"WhileLoop {condition} {{"]
        
        while not self._match(TokenType.END):
            stmt = self._parse_statement()
            if stmt:
                result.append(f"    {stmt}")
        
        self._consume(TokenType.END, "Expected 'end' to close while loop")
        self._consume(TokenType.SEMICOLON, "Expected ';' after 'end'")
        
        result.append("}")
        
        return '\n'.join(result)
    
    def _parse_for(self) -> str:
        """Parse for loop"""
        self._advance()  # consume 'for'
        
        var = self._consume(TokenType.IDENTIFIER, "Expected loop variable").value
        self._consume(TokenType.IN, "Expected 'in' in for loop")
        
        collection = self._parse_expression()
        self._consume(TokenType.COLON, "Expected ':' after for loop header")
        self._skip_newlines()
        
        result = [f"ForEvery {var} in {collection} {{"]
        
        while not self._match(TokenType.END):
            stmt = self._parse_statement()
            if stmt:
                result.append(f"    {stmt}")
        
        self._consume(TokenType.END, "Expected 'end' to close for loop")
        self._consume(TokenType.SEMICOLON, "Expected ';' after 'end'")
        
        result.append("}")
        
        return '\n'.join(result)
    
    def _parse_ailang_block(self) -> str:
        """Parse ailang escape block"""
        self._advance()  # consume 'ailang'
        self._consume(TokenType.LBRACE, "Expected '{' after 'ailang'")
        
        # Capture everything until closing brace
        content = []
        depth = 1
        
        while depth > 0:
            token = self._advance()
            if token.type == TokenType.LBRACE:
                depth += 1
                content.append('{')
            elif token.type == TokenType.RBRACE:
                depth -= 1
                if depth > 0:
                    content.append('}')
            elif token.type == TokenType.EOF:
                self._error("Unterminated ailang block")
            else:
                if token.value:
                    content.append(str(token.value))
                    
        if self._match(TokenType.SEMICOLON):
            self._advance()
        
        return ''.join(content)
    
    def _parse_asm_block(self) -> str:
        """Parse assembly escape block"""
        self._advance()  # consume 'asm'
        self._consume(TokenType.LBRACE, "Expected '{' after 'asm'")
        
        result = ["InlineAssembly {"]
        depth = 1
        
        while depth > 0:
            token = self._advance()
            if token.type == TokenType.LBRACE:
                depth += 1
            elif token.type == TokenType.RBRACE:
                depth -= 1
                if depth > 0:
                    result.append('}')
            elif token.type == TokenType.EOF:
                self._error("Unterminated asm block")
            else:
                if token.value:
                    result.append(f"    {token.value}")
        
        result.append("}")
        
        if self._match(TokenType.SEMICOLON):
            self._advance()
            
        return '\n'.join(result)
    
    def _parse_assignment_or_call(self) -> str:
        """Parse assignment or function call"""
        identifier = self._current().value
        self._advance()
        
        # Assignment
        if self._match(TokenType.ASSIGN):
            self._advance()
            expr = self._parse_expression()
            
            if self._match(TokenType.SEMICOLON):
                self._advance()
                
            return f"{identifier} = {expr}"
        
        # Function call
        elif self._match(TokenType.LPAREN):
            return self._parse_function_call(identifier)
        
        # Just an identifier
        return identifier
    
    def _parse_function_call(self, name: str) -> str:
        """Parse function call"""
        self._consume(TokenType.LPAREN, "Expected '('")
        
        args = []
        while not self._match(TokenType.RPAREN):
            args.append(self._parse_expression())
            
            if self._match(TokenType.COMMA):
                self._advance()
        
        self._consume(TokenType.RPAREN, "Expected ')'")
        
        # Check if we need to map this function
        mapped = self.function_mapper.map_function(name, args)
        
        if self._match(TokenType.SEMICOLON):
            self._advance()
            
        return mapped
    
    def _parse_expression(self) -> str:
        """Parse expression (simplified for now)"""
        return self._parse_or()
    
    def _parse_or(self) -> str:
        """Parse logical OR expression"""
        left = self._parse_and()
        
        while self._match(TokenType.OR):
            self._advance()
            right = self._parse_and()
            left = f"Or({left}, {right})"
            
        return left
    
    def _parse_and(self) -> str:
        """Parse logical AND expression"""
        left = self._parse_comparison()
        
        while self._match(TokenType.AND):
            self._advance()
            right = self._parse_comparison()
            left = f"And({left}, {right})"
            
        return left
    
    def _parse_comparison(self) -> str:
        """Parse comparison expression"""
        left = self._parse_addition()
        
        if self._match(TokenType.EQ):
            self._advance()
            right = self._parse_addition()
            return f"EqualTo({left}, {right})"
        elif self._match(TokenType.NE):
            self._advance()
            right = self._parse_addition()
            return f"NotEqual({left}, {right})"
        elif self._match(TokenType.LT):
            self._advance()
            right = self._parse_addition()
            return f"LessThan({left}, {right})"
        elif self._match(TokenType.LE):
            self._advance()
            right = self._parse_addition()
            return f"LessEqual({left}, {right})"
        elif self._match(TokenType.GT):
            self._advance()
            right = self._parse_addition()
            return f"GreaterThan({left}, {right})"
        elif self._match(TokenType.GE):
            self._advance()
            right = self._parse_addition()
            return f"GreaterEqual({left}, {right})"
            
        return left
    
    def _parse_addition(self) -> str:
        """Parse addition/subtraction expression"""
        left = self._parse_multiplication()
        
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op = self._advance().type
            right = self._parse_multiplication()
            
            if op == TokenType.PLUS:
                left = f"Add({left}, {right})"
            else:
                left = f"Subtract({left}, {right})"
                
        return left
    
    def _parse_multiplication(self) -> str:
        """Parse multiplication/division expression"""
        left = self._parse_unary()
        
        while self._match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op = self._advance().type
            right = self._parse_unary()
            
            if op == TokenType.MULTIPLY:
                left = f"Multiply({left}, {right})"
            elif op == TokenType.DIVIDE:
                left = f"Divide({left}, {right})"
            else:
                left = f"Modulo({left}, {right})"
                
        return left
    
    def _parse_unary(self) -> str:
        """Parse unary expression"""
        if self._match(TokenType.NOT):
            self._advance()
            return f"Not({self._parse_unary()})"
        elif self._match(TokenType.MINUS):
            self._advance()
            return f"Negate({self._parse_unary()})"
            
        return self._parse_primary()
    
    def _parse_primary(self) -> str:
        """Parse primary expression"""
        # Literals
        if self._match(TokenType.TRUE):
            self._advance()
            return "True"
        
        if self._match(TokenType.FALSE):
            self._advance()
            return "False"
        
        if self._match(TokenType.NONE):
            self._advance()
            return "0"
        
        if self._match(TokenType.NUMBER):
            value = self._advance().value
            return str(value)
        
        if self._match(TokenType.STRING):
            value = self._advance().value
            return f'"{value}"'
        
        if self._match(TokenType.FSTRING):
            value = self._advance().value
            # Simple f-string handling - would need more complex parsing for real interpolation
            return f'StringFormat("{value}")'
        
        # Parenthesized expression
        if self._match(TokenType.LPAREN):
            self._advance()
            if self._match(TokenType.RPAREN):
                # Empty parens - might be a tuple or empty call
                self._advance()
                return "()"
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Expected ')' after expression")
            return f"({expr})"
        
        # Identifier (variable or function call)
        if self._match(TokenType.IDENTIFIER):
            name = self._advance().value
            
            # Function call
            if self._match(TokenType.LPAREN):
                return self._parse_function_call(name)
            
            # List/array access
            if self._match(TokenType.LBRACKET):
                self._advance()
                index = self._parse_expression()
                self._consume(TokenType.RBRACKET, "Expected ']'")
                return f"ArrayGet({name}, {index})"
            
            return name
        
        self._error(f"Unexpected token in expression: {self._current()}")
    
    def _error(self, msg: str):
        """Raise parser error"""
        token = self._current()
        raise SyntaxError(f"Parser error at line {token.line}, column {token.column}: {msg}")

class FunctionMapper:
    """Maps Python functions to AILang equivalents"""
    
    def __init__(self):
        # Core Python built-ins mapped to AILang
        self.mappings = {
            'print': 'PrintMessage',
            'len': 'ArrayLength',
            'range': 'AIMacro.range',
            'str': 'ToString',
            'int': 'ToInteger',
            'float': 'ToFloat',
            'abs': 'AbsoluteValue',
            'sum': 'AIMacro.sum',
            'min': 'AIMacro.min',
            'max': 'AIMacro.max',
            'input': 'AIMacro.input',
            'open': 'FileOpen',
            'sorted': 'AIMacro.sorted',
            'enumerate': 'AIMacro.enumerate',
            'zip': 'AIMacro.zip',
            'map': 'AIMacro.map',
            'filter': 'AIMacro.filter',
            'all': 'AIMacro.all',
            'any': 'AIMacro.any',
            'round': 'Round',
            'type': 'AIMacro.type',
            'isinstance': 'AIMacro.isinstance',
        }
    
    def map_function(self, name: str, args: List[str]) -> str:
        """Map a Python function call to AILang"""
        # Check for direct mapping
        if name in self.mappings:
            mapped_name = self.mappings[name]
            args_str = ', '.join(args)
            return f"{mapped_name}({args_str})"
        
        # Default: assume it's a user function or will be in AIMacro library
        args_str = ', '.join(args)
        return f"{name}({args_str})"

def compile_aimacro(source: str, output_file: str = None) -> str:
    """Main compilation function"""
    # Tokenize
    lexer = AIMacroLexer(source)
    tokens = lexer.tokenize()
    
    # Parse
    parser = AIMacroParser(tokens)
    ailang_code = parser.parse()
    
    # Add the Library.AIMacro import at the top
    final_code = "// Generated from AIMacro source\n"
    final_code += "LibraryImport Library.AIMacro\n\n"
    final_code += ailang_code
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write(final_code)
    
    return final_code

# Example usage
if __name__ == "__main__":
    example = """
# Example AIMacro program
def calculate(x, y):
    result = x + y;
    print(f"Result: {result}");
    return result;
end;

def main():
    numbers = range(10);
    total = 0;
    
    for num in numbers:
        total = total + num;
    end;
    
    print(f"Total: {total}");
    
    # Use AILang directly when needed
    ailang {
        buffer = Allocate(1024)
        StoreByte(buffer, 65)
    };
    
    return 0;
end;
"""
    
    try:
        output = compile_aimacro(example)
        print("=== Generated AILang Code ===")
        print(output)
    except SyntaxError as e:
        print(f"Compilation error: {e}")
