#!/usr/bin/env python3
"""
AIMacro Parser Test Suite
Tests all major features of the AIMacro to AILang transpiler
"""

import unittest
from aimacro_parser import AIMacroLexer, AIMacroParser, compile_aimacro, TokenType

class TestAIMacroLexer(unittest.TestCase):
    """Test the lexer/tokenizer"""
    
    def test_basic_tokens(self):
        """Test basic token recognition"""
        source = "def func end return if else while for"
        lexer = AIMacroLexer(source)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.DEF, TokenType.FUNC, TokenType.END,
            TokenType.RETURN, TokenType.IF, TokenType.ELSE,
            TokenType.WHILE, TokenType.FOR, TokenType.EOF
        ]
        
        self.assertEqual([t.type for t in tokens], expected_types)
    
    def test_operators(self):
        """Test operator tokenization"""
        source = "+ - * / == != < <= > >= = += -= **"
        lexer = AIMacroLexer(source)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY,
            TokenType.DIVIDE, TokenType.EQ, TokenType.NE,
            TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE,
            TokenType.ASSIGN, TokenType.PLUSEQ, TokenType.MINUSEQ,
            TokenType.POWER, TokenType.EOF
        ]
        
        self.assertEqual([t.type for t in tokens], expected_types)
    
    def test_string_literals(self):
        """Test string and f-string tokenization"""
        source = '''
        "hello world"
        'single quotes'
        f"formatted {value}"
        '''
        lexer = AIMacroLexer(source)
        tokens = lexer.tokenize()
        
        # Filter out newlines
        tokens = [t for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
        
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "hello world")
        self.assertEqual(tokens[1].type, TokenType.STRING)
        self.assertEqual(tokens[1].value, "single quotes")
        self.assertEqual(tokens[2].type, TokenType.FSTRING)
    
    def test_number_literals(self):
        """Test various number formats"""
        source = "42 3.14 0xFF 0b1010 1.5e-3"
        lexer = AIMacroLexer(source)
        tokens = lexer.tokenize()
        
        # Filter to just numbers
        numbers = [t for t in tokens if t.type == TokenType.NUMBER]
        
        self.assertEqual(numbers[0].value, "42")
        self.assertEqual(numbers[1].value, "3.14")
        self.assertEqual(numbers[2].value, "0xFF")
        self.assertEqual(numbers[3].value, "0b1010")
        self.assertEqual(numbers[4].value, "1.5e-3")

class TestAIMacroParser(unittest.TestCase):
    """Test the parser"""
    
    def parse_source(self, source):
        """Helper to parse source code"""
        lexer = AIMacroLexer(source)
        tokens = lexer.tokenize()
        parser = AIMacroParser(tokens)
        return parser.parse()
    
    def test_simple_function(self):
        """Test basic function definition"""
        source = """
def add(x, y):
    result = x + y;
    return result;
end;
"""
        output = self.parse_source(source)
        
        # Check for proper function structure
        self.assertIn("Function.add", output)
        self.assertIn("Input: x: Integer", output)
        self.assertIn("Input: y: Integer", output)
        self.assertIn("result = Add(x, y)", output)
        self.assertIn("ReturnValue(result)", output)
    
    def test_if_statement(self):
        """Test if-else statement"""
        source = """
def check(x):
    if x > 0:
        return 1;
    else:
        return -1;
    end;
end;
"""
        output = self.parse_source(source)
        
        self.assertIn("IfCondition GreaterThan(x, 0) ThenBlock", output)
        self.assertIn("ElseBlock", output)
        self.assertIn("ReturnValue(1)", output)
        self.assertIn("ReturnValue(-1)", output)
    
    def test_while_loop(self):
        """Test while loop"""
        source = """
def count():
    i = 0;
    while i < 10:
        i = i + 1;
    end;
    return i;
end;
"""
        output = self.parse_source(source)
        
        self.assertIn("WhileLoop LessThan(i, 10)", output)
        self.assertIn("i = Add(i, 1)", output)
    
    def test_for_loop(self):
        """Test for loop"""
        source = """
def sum_range():
    total = 0;
    for num in range(10):
        total = total + num;
    end;
    return total;
end;
"""
        output = self.parse_source(source)
        
        self.assertIn("ForEvery num in AIMacro.range(10)", output)
        self.assertIn("total = Add(total, num)", output)
    
    def test_function_calls(self):
        """Test Python built-in function mapping"""
        source = """
def test():
    x = len(array);
    print(x);
    y = sum(numbers);
    z = max(values);
    return min(results);
end;
"""
        output = self.parse_source(source)
        
        self.assertIn("ArrayLength(array)", output)
        self.assertIn("PrintMessage(x)", output)
        self.assertIn("AIMacro.sum(numbers)", output)
        self.assertIn("AIMacro.max(values)", output)
        self.assertIn("AIMacro.min(results)", output)
    
    def test_escape_blocks(self):
        """Test ailang and asm escape blocks"""
        source = """
def optimize():
    ailang {
        buffer = Allocate(1024)
        StoreByte(buffer, 65)
    };
    
    asm {
        MOV RAX, 60
        XOR RDI, RDI
        SYSCALL
    };
    
    return 0;
end;
"""
        output = self.parse_source(source)
        
        self.assertIn("buffer = Allocate(1024)", output)
        self.assertIn("StoreByte(buffer, 65)", output)
        self.assertIn("InlineAssembly", output)
        self.assertIn("MOV RAX, 60", output)
    
    def test_complex_expressions(self):
        """Test complex expression parsing"""
        source = """
def calculate():
    result = (a + b) * (c - d) / 2;
    condition = x > 5 and y < 10 or z == 0;
    return result;
end;
"""
        output = self.parse_source(source)
        
        # Check for proper nesting of operations
        self.assertIn("Multiply(Add(a, b), Subtract(c, d))", output)
        self.assertIn("Or(And(GreaterThan(x, 5), LessThan(y, 10)), EqualTo(z, 0))", output)

class TestFullPrograms(unittest.TestCase):
    """Test complete AIMacro programs"""
    
    def test_fibonacci(self):
        """Test Fibonacci implementation"""
        source = """
def fibonacci(n):
    if n <= 1:
        return n;
    end;
    
    a = 0;
    b = 1;
    i = 2;
    
    while i <= n:
        temp = a + b;
        a = b;
        b = temp;
        i = i + 1;
    end;
    
    return b;
end;

def main():
    result = fibonacci(10);
    print(result);
    return 0;
end;
"""
        output = compile_aimacro(source)
        
        # Check for proper structure
        self.assertIn("Function.fibonacci", output)
        self.assertIn("Function.main", output)
        self.assertIn("LibraryImport Library.AIMacro", output)
    
    def test_list_processing(self):
        """Test list/array operations"""
        source = """
def process_list():
    numbers = range(10);
    doubled = [];
    
    for num in numbers:
        doubled = doubled + [num * 2];
    end;
    
    total = sum(doubled);
    print(f"Total: {total}");
    
    return total;
end;
"""
        output = compile_aimacro(source)
        
        self.assertIn("AIMacro.range(10)", output)
        self.assertIn("ForEvery num in", output)
        self.assertIn("AIMacro.sum(doubled)", output)
    
    def test_mixed_syntax(self):
        """Test mixing Python and AILang syntax"""
        source = """
def hybrid():
    # Python-style operations
    x = 10;
    y = 20;
    result = x + y;
    
    # Direct AILang when needed
    ailang {
        buffer = Allocate(result)
        FillMemory(buffer, 0, result)
    };
    
    # Back to Python style
    print(f"Allocated {result} bytes");
    
    return buffer;
end;
"""
        output = compile_aimacro(source)
        
        self.assertIn("Add(x, y)", output)
        self.assertIn("Allocate(result)", output)
        self.assertIn("FillMemory(buffer, 0, result)", output)

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_empty_function(self):
        """Test empty function body"""
        source = """
def empty():
    pass;
end;
"""
        # Should parse without errors
        output = compile_aimacro(source)
        self.assertIn("Function.empty", output)
    
    def test_nested_blocks(self):
        """Test deeply nested control structures"""
        source = """
def nested():
    for i in range(3):
        for j in range(3):
            if i == j:
                print(i);
            else:
                if i > j:
                    print("greater");
                else:
                    print("less");
                end;
            end;
        end;
    end;
end;
"""
        output = compile_aimacro(source)
        
        # Should have proper nesting
        self.assertIn("ForEvery i", output)
        self.assertIn("ForEvery j", output)
        self.assertIn("IfCondition", output)
    
    def test_no_semicolons(self):
        """Test that semicolons are optional"""
        source = """
def no_semi():
    x = 10
    y = 20
    result = x + y
    return result
end;
"""
        # Should parse even without semicolons on statements
        output = compile_aimacro(source)
        self.assertIn("Add(x, y)", output)
    
    def test_mixed_indentation(self):
        """Test that mixed tabs/spaces don't break parsing"""
        source = """
def mixed():
	x = 10;  # tab
    y = 20;  # spaces
	return x + y;  # tab again
end;
"""
        # Should handle mixed indentation (the whole point of AIMacro!)
        output = compile_aimacro(source)
        self.assertIn("Function.mixed", output)

class TestRegressionSuite(unittest.TestCase):
    """Regression tests for specific bugs found"""
    
    def test_if_then_compatibility(self):
        """Test that recent IfThen changes work"""
        source = """
def test_if():
    x = 5;
    if x > 0:
        result = "positive";
    elif x < 0:
        result = "negative";
    else:
        result = "zero";
    end;
    return result;
end;
"""
        output = compile_aimacro(source)
        
        # Should use IfCondition ThenBlock syntax
        self.assertIn("IfCondition GreaterThan(x, 0) ThenBlock", output)
    
    def test_flow_control_keywords(self):
        """Test all flow control patterns work"""
        source = """
def flow_test():
    i = 0;
    while i < 10:
        if i == 5:
            break;
        end;
        if i == 3:
            continue;
        end;
        i = i + 1;
    end;
    return i;
end;
"""
        output = compile_aimacro(source)
        
        self.assertIn("WhileLoop LessThan(i, 10)", output)
        # Note: break/continue might need special handling
    
    def test_function_call_in_condition(self):
        """Test function calls as conditions"""
        source = """
def test():
    if len(array) > 0:
        return 1;
    end;
    return 0;
end;
"""
        output = compile_aimacro(source)
        
        self.assertIn("GreaterThan(ArrayLength(array), 0)", output)

def run_test_suite():
    """Run the complete test suite"""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAIMacroLexer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAIMacroParser))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFullPrograms))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRegressionSuite))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFailed tests:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    # Run the test suite
    success = run_test_suite()
    
    if success:
        print("\n✅ All tests passed! The AIMacro parser is working correctly.")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
    
    # Also run a demo
    print("\n" + "="*70)
    print("DEMO: Sample AIMacro to AILang Compilation")
    print("="*70)
    
    demo_source = """
# Demo: Python-like code without whitespace issues
def calculate_average(numbers):
    total = sum(numbers);
    count = len(numbers);
    
    if count == 0:
        return 0;
    end;
    
    average = total / count;
    return average;
end;

def main():
    # Create test data
    values = range(1, 11);  # 1 to 10
    
    # Calculate and display
    avg = calculate_average(values);
    print(f"Average: {avg}");
    
    # Direct AILang for performance
    ailang {
        HighPerformanceOperation(avg)
    };
    
    return 0;
end;
"""
    
    print("\nInput AIMacro code:")
    print("-" * 40)
    print(demo_source)
    
    print("\nOutput AILang code:")
    print("-" * 40)
    
    try:
        output = compile_aimacro(demo_source)
        print(output)
    except Exception as e:
        print(f"Error during compilation: {e}")
