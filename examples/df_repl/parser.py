# parser.py
from lark import Lark, Transformer, v_args, Token, LarkError, UnexpectedInput
import operator
import pandas as pd # For DataFrame operations

# --- MiniLangExecutor Class (Transformer) ---
class MiniLangExecutor(Transformer):
    def __init__(self, shared_env=None):
        self.env = shared_env or {}  # Environment for storing variables
        # Define built-in functions that perform actual operations
        self.functions = {
            "load_csv": self._load_csv,
            "stats": self._stats,
            "create_pivot": self._create_pivot,
            # Add other MiniLang functions here
        }
        # Add functions to the environment so they can be looked up like variables
        self.env.update(self.functions)

    # --- Built-in MiniLang Functions (with Pandas) ---
    def _load_csv(self, file_path_str):
        """Loads a CSV file into a pandas DataFrame."""
        if not isinstance(file_path_str, str):
            raise TypeError(f"load_csv expects a string file path, got {type(file_path_str).__name__}")
        try:
            print(f"Executing: load_csv('{file_path_str}')")
            df = pd.read_csv(file_path_str)
            return df
        except FileNotFoundError:
            # Instead of raising an error that stops the script, 
            # return a message or a specific error object if preferred for REPL
            print(f"Error: File not found at '{file_path_str}'")
            return f"Error: File not found '{file_path_str}'" # Or return None, or custom error object
        except Exception as e:
            print(f"Error loading CSV '{file_path_str}': {e}")
            return f"Error loading CSV: {e}"

    def _stats(self, dataframe, operations_list):
        """Calculates descriptive statistics on a DataFrame."""
        if not isinstance(dataframe, pd.DataFrame):
            # Allow string error messages from _load_csv to pass through
            if isinstance(dataframe, str) and dataframe.startswith("Error:"):
                return dataframe 
            raise TypeError(f"stats() first argument must be a DataFrame, got {type(dataframe).__name__}")
        if not isinstance(operations_list, list):
            raise TypeError(f"stats() second argument must be a list of operations, got {type(operations_list).__name__}")

        print(f"Executing: stats on DataFrame, operations: {operations_list}")
        try:
            # describe() can generate many common stats.
            # We can pick specific ones or allow users to pass describe()'s output.
            # For this example, let's try to match common stats.
            desc = dataframe.describe()
            results = {}
            for op in operations_list:
                if op == "mean":
                    results['mean'] = desc.loc['mean'].to_dict()
                elif op == "std":
                    results['std'] = desc.loc['std'].to_dict()
                elif op == "min":
                    results['min'] = desc.loc['min'].to_dict()
                elif op == "max":
                    results['max'] = desc.loc['max'].to_dict()
                elif op == "50%" or op == "median":
                    results['median'] = desc.loc['50%'].to_dict()
                elif op in ["25%", "75%"]:
                     results[op] = desc.loc[op].to_dict()
                elif op == "count":
                    results['count'] = desc.loc['count'].to_dict()
                else:
                    results[op] = f"Unsupported operation: {op}"
            return results if results else "No valid statistics generated."
        except Exception as e:
            print(f"Error calculating stats: {e}")
            return f"Error in stats: {e}"

    def _create_pivot(self, dataframe, index, columns, values, aggfunc='mean'):
        """Creates a pivot table from a DataFrame."""
        if not isinstance(dataframe, pd.DataFrame):
            if isinstance(dataframe, str) and dataframe.startswith("Error:"):
                return dataframe
            raise TypeError(f"create_pivot() first argument must be a DataFrame, got {type(dataframe).__name__}")
        
        print(f"Executing: create_pivot with index='{index}', columns='{columns}', values='{values}', aggfunc='{aggfunc}'")
        try:
            pivot_df = pd.pivot_table(dataframe, index=index, columns=columns, values=values, aggfunc=aggfunc)
            return pivot_df
        except Exception as e:
            print(f"Error creating pivot table: {e}")
            return f"Error in pivot_table: {e}"

    # --- Helper to convert token string value to Python number (int or float) ---
    def _to_python_number(self, token_value_str):
        if '.' in token_value_str or 'e' in token_value_str or 'E' in token_value_str:
            return float(token_value_str)
        return int(token_value_str)

    # --- Literal Handling ---
    @v_args(inline=True)
    def string_literal(self, string_token):
        return string_token.value[1:-1].encode('utf-8').decode('unicode_escape')

    @v_args(inline=True)
    def number_literal(self, number_token):
        return self._to_python_number(number_token.value)

    def list_literal(self, items):
        return list(items)
    
    # --- Variable and Assignment Handling ---
    @v_args(inline=True)
    def let_stmt(self, name_token, value):
        var_name = name_token.value
        self.env[var_name] = value
        print(f"LET: {var_name} = {repr(value)[:200]}") # Truncate long DataFrame reprs
        return None 

    @v_args(inline=True)
    def var_lookup(self, name_token):
        var_name = name_token.value
        if var_name in self.env:
            return self.env[var_name]
        else:
            raise NameError(f"Variable or function '{var_name}' is not defined.")

    # --- Expression and Operator Handling ---
    def _process_binary_operation_list(self, items):
        current_result = items[0]
        for i in range(1, len(items), 2):
            operator_token = items[i]
            op_symbol = operator_token.value
            right_operand = items[i+1]
            
            if op_symbol == '+': current_result = operator.add(current_result, right_operand)
            elif op_symbol == '-': current_result = operator.sub(current_result, right_operand)
            elif op_symbol == '*': current_result = operator.mul(current_result, right_operand)
            elif op_symbol == '/':
                if right_operand == 0: raise ZeroDivisionError("Cannot divide by zero.")
                current_result = operator.truediv(current_result, right_operand)
            else: raise ValueError(f"Unknown operator: {op_symbol}")
        return current_result

    def binary_op_expr(self, items): return self._process_binary_operation_list(items)
    def binary_op_term(self, items): return self._process_binary_operation_list(items)
    @v_args(inline=True)
    def factor(self, item_or_expr): return item_or_expr
    def primaria(self, items): return items[0]

    # --- Function Call Handling ---
    @v_args(inline=True) 
    def func_call(self, func_name_token, args_node=None):
        func_name = func_name_token.value
        if func_name not in self.env or not callable(self.env[func_name]):
            raise NameError(f"Function '{func_name}' is not defined or is not callable.")
        
        target_function = self.env[func_name]
        positional_args, keyword_args = [], {}
        if args_node:
            for arg_item in args_node:
                if isinstance(arg_item, tuple) and arg_item[0] == '__kw__':
                    keyword_args[arg_item[1]] = arg_item[2]
                else:
                    positional_args.append(arg_item)
        return target_function(*positional_args, **keyword_args)

    def args(self, items): return items
    @v_args(inline=True)
    def kw_arg(self, name_token, value): return ('__kw__', name_token.value, value)

    # --- Statement Handling ---
    @v_args(inline=True)
    def print_stmt(self, value):
        if isinstance(value, pd.DataFrame):
            print(f"PRINT DataFrame (first 5 rows):\n{value.head().to_string()}")
        else:
            print(f"PRINT: {repr(value)}")
        return None

    @v_args(inline=True)
    def eval_stmt(self, value): return None 

    def start(self, items):
        return [item for item in items if item is not None]

# --- REPL Helper Functions (for repl.py to use) ---
def load_parser(grammar_file_path="minilang.lark"):
    """Loads the MiniLang grammar and returns a Lark parser instance."""
    try:
        with open(grammar_file_path, "r", encoding="utf-8") as f:
            grammar = f.read()
        # For REPL, the transformer is usually applied per line/statement,
        # so we return the parser without a default transformer here.
        # The transformer instance will be managed by the REPL.
        return Lark(grammar, start='start', parser='lalr', lexer='contextual')
    except FileNotFoundError:
        print(f"Error: Grammar file '{grammar_file_path}' not found.")
        raise
    except Exception as e:
        print(f"Error loading grammar from '{grammar_file_path}': {e}")
        raise

def run_line(lark_parser, transformer_instance, line_of_code):
    """Parses and executes a single line/statement of MiniLang code."""
    try:
        # Ensure the line is treated as a complete mini-program segment
        # by the grammar's 'start' rule. Adding a newline is crucial.
        if not line_of_code.strip(): # Skip empty lines
            return None
        parse_tree = lark_parser.parse(line_of_code if line_of_code.endswith('\n') else line_of_code + "\n")
        result = transformer_instance.transform(parse_tree)
        return result
    except UnexpectedInput as e:
        print(f"Syntax Error (incomplete input?): {e.get_context(line_of_code)}")
        # For a REPL, you might want to buffer input here
        return "Syntax Error: Incomplete input or invalid syntax."
    except LarkError as e: # Catches other Lark parsing errors
        print(f"Syntax Error: {e}")
        return f"Syntax Error: {e}"
    except Exception as e: # Catches runtime errors from the transformer
        print(f"Runtime Error: {e}")
        # import traceback # For more detailed debugging
        # traceback.print_exc()
        return f"Runtime Error: {e}"


def run_script(lark_parser, transformer_instance, script_filename):
    """Reads and executes a MiniLang script file line by line."""
    print(f"📜 스크립트 실행: {script_filename}")
    results = []
    try:
        with open(script_filename, "r", encoding="utf-8") as f:
            # For simplicity here, we process line by line.
            # A more advanced script runner might parse the whole file at once.
            full_script_content = f.read()
            if full_script_content.strip():
                # Parse and transform the entire script content
                parse_tree = lark_parser.parse(full_script_content)
                transformer_instance.transform(parse_tree) # Side effects happen here
            else:
                print("Script is empty.")

    except FileNotFoundError:
        print(f"[오류] 파일을 찾을 수 없습니다: {script_filename}")
    except Exception as e:
        print(f"Error running script '{script_filename}': {e}")
        # import traceback
        # traceback.print_exc()


# --- Main block for testing parser.py functionalities ---
if __name__ == "__main__":
    # 0. Define the grammar file name
    grammar_file = "minilang.lark"

    # 1. Create a dummy titanic.csv for testing
    dummy_titanic_content = """PassengerId,Survived,Pclass,Name,Sex,Age,SibSp,Parch,Ticket,Fare,Cabin,Embarked
1,0,3,"Braund, Mr. Owen Harris",male,22,1,0,A/5 21171,7.25,,S
2,1,1,"Cumings, Mrs. John Bradley (Florence Briggs Thayer)",female,38,1,0,PC 17599,71.2833,C85,C
3,1,3,"Heikkinen, Miss. Laina",female,26,0,0,STON/O2. 3101282,7.925,,S
4,1,1,"Futrelle, Mrs. Jacques Heath (Lily May Peel)",female,35,1,0,113803,53.1,C123,S
5,0,3,"Allen, Mr. William Henry",male,35,0,0,373450,8.05,,S
892,0,3,"Kelly, Mr. James",male,34.5,0,0,330911,7.8292,,Q
"""
    try:
        with open("titanic.csv", "w", encoding="utf-8") as f:
            f.write(dummy_titanic_content)
        print("Dummy 'titanic.csv' created for testing.")
    except Exception as e:
        print(f"Could not create dummy titanic.csv: {e}")

    # 2. Load the parser
    try:
        minilang_parser_instance = load_parser(grammar_file)
        print(f"Parser loaded successfully using '{grammar_file}'.")
    except Exception as e:
        print(f"Failed to load parser. Exiting. Error: {e}")
        exit()

    # 3. Create a transformer instance (this will hold the state like 'env')
    executor = MiniLangExecutor()
    print("MiniLangExecutor instance created.")

    # 4. Test run_line
    print("\n--- Testing run_line ---")
    lines_to_test = [
        'let x = 42',
        'print(x + 8)',
        'let data_path = "titanic.csv"',
        'let df = load_csv(data_path)',
        'print(df)',
        'let stats_ops = ["mean", "std", "50%"]',
        'let df_stats = stats(df, stats_ops)',
        'print(df_stats)',
        '// This is a comment, should be ignored by grammar',
        'let p_table = create_pivot(df, index="Pclass", columns="Sex", values="Survived", aggfunc="mean")',
        'print(p_table)'
    ]
    for ml_line in lines_to_test:
        print(f"\nminilang> {ml_line}")
        run_line(minilang_parser_instance, executor, ml_line)
        
    # 5. Test run_script
    print("\n\n--- Testing run_script ---")
    dummy_script_content = """
// This is a test MiniLang script.
let script_var = 100
print(script_var * 2)

let titanic_data = load_csv("titanic.csv")
print("First few rows of titanic data from script:")
print(titanic_data)

let some_stats = stats(titanic_data, ["min", "max"])
print("Min/Max stats from script:")
print(some_stats)
"""
    script_file_name = "test_script.ml"
    try:
        with open(script_file_name, "w", encoding="utf-8") as f:
            f.write(dummy_script_content)
        print(f"Dummy script '{script_file_name}' created.")
        
        # For run_script, it's often better to create a fresh executor 
        # if you want isolated script environments, or reuse for continuous state.
        # Here we reuse the existing 'executor' to see if state from run_line persists (it should).
        run_script(minilang_parser_instance, executor, script_file_name)
        
        # Test if script_var is in the environment after running the script
        print("\nChecking environment after script:")
        if "script_var" in executor.env:
            print(f"script_var found in env: {executor.env['script_var']}")
        else:
            print("script_var NOT found in env.")

    except Exception as e:
        print(f"Error during script testing: {e}")

    print("\n--- parser.py tests finished ---")
