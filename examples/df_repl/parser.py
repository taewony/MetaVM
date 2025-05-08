# parser.py
from lark import Lark, Transformer, v_args, Token
import operator

# Load the grammar from the .lark file
try:
    with open("minilang.lark", "r", encoding="utf-8") as f:
        grammar = f.read()
except FileNotFoundError:
    print("Error: minilang_user_fixed.lark not found. Please create it with the grammar content.")
    exit()
except Exception as e:
    print(f"Error reading grammar file: {e}")
    exit()

class MiniLangExecutor(Transformer):
    def __init__(self):
        self.env = {}  # Environment for storing variables
        # Define built-in functions
        self.functions = {
            "load_csv": lambda path_arg: f"MockDataFrame loaded from '{path_arg}' (argument type: {type(path_arg).__name__})"
            # Add other MiniLang functions here
            # e.g., "stats": lambda df, ops: f"Calculating stats for {df} with {ops}"
        }
        # Add functions to the environment so they can be looked up like variables
        # when determining if a NAME is a callable function.
        self.env.update(self.functions)

    # --- Helper to convert token string value to Python number (int or float) ---
    def _to_python_number(self, token_value_str):
        if '.' in token_value_str or 'e' in token_value_str or 'E' in token_value_str:
            return float(token_value_str)
        return int(token_value_str)

    # --- Literal Handling ---
    @v_args(inline=True)
    def string_literal(self, string_token):
        # string_token is an ESCAPED_STRING Token
        # Remove quotes and unescape sequences
        return string_token.value[1:-1].encode('utf-8').decode('unicode_escape')

    @v_args(inline=True)
    def number_literal(self, number_token):
        # number_token is a NUMBER Token (comes from SIGNED_NUMBER)
        return self._to_python_number(number_token.value)

    # The v_args decorator unpacks the children, so 'items' will be the evaluated expressions.
    # If no expressions, items will be empty.
    def list_literal(self, items):
        return list(items)
    
    # --- Variable and Assignment Handling ---
    @v_args(inline=True) # Inlines children: let_token, name_token, eq_token, value_node
    def let_stmt(self, name_token, value): # We only care about name_token and the evaluated value
        var_name = name_token.value
        self.env[var_name] = value
        print(f"LET: {var_name} = {repr(value)}") # Output for tracing execution
        return None # Assignment statement itself doesn't produce a value to be used further

    @v_args(inline=True)
    def var_lookup(self, name_token):
        var_name = name_token.value
        if var_name in self.env:
            return self.env[var_name]
        else:
            raise NameError(f"Variable or function '{var_name}' is not defined.")

    # --- Expression and Operator Handling ---
    def _process_binary_operation_list(self, items):
        # items will be like: [operand1, operator_token1, operand2, operator_token2, operand3, ...]
        # e.g. for "1 + 2 - 3", items would be [1, Token(ADD,'+'), 2, Token(SUB,'-'), 3]
        # (assuming operands are already transformed to their Python values)
        
        # print(f"Processing binary op list: {items}") # For debugging
        
        current_result = items[0] # First item is the initial operand
        
        # Iterate through the rest of the items, two at a time (operator, operand)
        for i in range(1, len(items), 2):
            operator_token = items[i]
            op_symbol = operator_token.value # e.g., "+", "-"
            right_operand = items[i+1]
            
            if op_symbol == '+':
                current_result = operator.add(current_result, right_operand)
            elif op_symbol == '-':
                current_result = operator.sub(current_result, right_operand)
            elif op_symbol == '*':
                current_result = operator.mul(current_result, right_operand)
            elif op_symbol == '/':
                if right_operand == 0:
                    raise ZeroDivisionError("Cannot divide by zero.")
                current_result = operator.truediv(current_result, right_operand)
            # Add other operators like '%' or '**' if they are defined in the grammar
            else:
                raise ValueError(f"Unknown operator: {op_symbol}")
        return current_result

    def binary_op_expr(self, items): # Handles rules like: term ((ADD | SUB) term)*
        return self._process_binary_operation_list(items)

    def binary_op_term(self, items): # Handles rules like: factor ((MUL | DIV) factor)*
        return self._process_binary_operation_list(items)

    # For rules like: "(" expr ")" or if factor directly resolves to a primaria
    # v_args(inline=True) means 'item_or_expr' will be the already transformed child.
    @v_args(inline=True)
    def factor(self, item_or_expr):
        return item_or_expr

    # Primaria items (number, var, string, call, list) are already transformed by their specific rules.
    # This method just passes the transformed child up.
    def primaria(self, items): 
        return items[0]

    # --- Function Call Handling ---
    # func_name_token is the NAME token for the function.
    # args_node is the result of transforming the 'args' rule, or None if no arguments.
    @v_args(inline=True) 
    def func_call(self, func_name_token, args_node=None):
        func_name = func_name_token.value
        
        if func_name not in self.env or not callable(self.env[func_name]):
            raise NameError(f"Function '{func_name}' is not defined or is not callable.")
        
        target_function = self.env[func_name]
        
        positional_args = []
        keyword_args = {}

        if args_node: # args_node is the list returned by the 'args' transformer method
            for arg_item in args_node:
                if isinstance(arg_item, tuple) and arg_item[0] == '__kw__': # Check for our keyword arg marker
                    keyword_args[arg_item[1]] = arg_item[2]
                else:
                    positional_args.append(arg_item)
        
        # print(f"Calling: {func_name}(pos_args={positional_args}, kw_args={keyword_args})") # For debugging
        return target_function(*positional_args, **keyword_args)

    # 'items' here are the already transformed arguments (expressions or kw_arg tuples)
    def args(self, items): 
        return items

    # name_token is the NAME token for the keyword, value is the transformed expression.
    @v_args(inline=True)
    def kw_arg(self, name_token, value):
        # Return a special tuple to mark this as a keyword argument for func_call to process.
        return ('__kw__', name_token.value, value)

    # --- Statement Handling ---
    @v_args(inline=True) # value is the transformed result of the expression inside print()
    def print_stmt(self, value):
        print(f"PRINT: {repr(value)}") # Use repr for clearer output of types and string quotes
        return None # print statement itself doesn't yield a value

    @v_args(inline=True) # value is the transformed result of the expression
    def eval_stmt(self, value):
        # This handles expressions used as statements (e.g., a function call for its side effects).
        # The result of such an expression is typically not used further.
        # print(f"EVAL_STMT result (usually ignored): {repr(value)}") # For debugging
        return None 

    # The 'start' rule in the grammar is `(_NL? stmt (_NL | EOS))+ _NL?`
    # The transformer will receive a list of results from processing each 'stmt'.
    # Many statements (let, print, eval_stmt) return None intentionally.
    def start(self, items):
        # print(f"Start rule processed items: {items}") # For debugging
        # For a script execution, we often don't have a single "return value" for the whole script.
        # The side effects (assignments, prints) are what matter.
        # We can return a list of non-None results if any statement were to produce one.
        return [item for item in items if item is not None]


if __name__ == "__main__":
    # Create the LALR parser instance with the grammar and the transformer
    # Using lexer='standard' is a good default for non-contextual lexing.
    try:
        minilang_parser = Lark(grammar, start='start', parser='lalr', lexer='contextual')
        executor_transformer = MiniLangExecutor()
    except Exception as e:
        print(f"🔥 Error creating parser or transformer: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        exit()

    # Sample MiniLang code you want to parse and execute
    sample_code = """
    let x = 42
    let data_path_string = "data.csv" 
    let data = load_csv(data_path_string) // Calling load_csv with a string argument
    print(data)
    print(x + 8) // Test arithmetic in print
    """

    print("--- Parsing and Executing Sample Code ---")
    try:
        # 1. Parse the code to get an Abstract Syntax Tree (AST)
        parse_tree = minilang_parser.parse(sample_code)
        
        # Optional: Print the tree for debugging grammar issues
        # print("\n--- Parse Tree (for debugging) ---")
        # print(parse_tree.pretty())
        
        print("\n--- Execution Output (from Transformer) ---")
        # 2. Transform the AST to execute the code
        # The transformer methods will print output and modify self.env
        execution_result = executor_transformer.transform(parse_tree)
        
        # Optional: Print the final result from the 'start' rule transformation
        # print("\n--- Final Transformed Result (from start rule) ---")
        # print(execution_result) # This will likely be an empty list or list of Nones

    except Exception as e:
        print(f"\n🔥 Critical Error during parsing or execution: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()

