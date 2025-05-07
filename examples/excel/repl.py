#!/usr/bin/env python3
import sys
import pandas as pd
from lark import Lark, Transformer, v_args, LarkError, Tree
import argparse
import os
import io

# 1) Lark 파서 초기화 (REPL 및 CLI 모드 모두에서 사용)
try:
    with open("minilang.lark", encoding="utf-8") as f:
        grammar = f.read()
    parser = Lark(grammar, parser="lalr", propagate_positions=True)
    print("MiniLang grammar loaded successfully.")
except FileNotFoundError:
    print("Error: 'minilang.lark' grammar file not found.", file=sys.stderr)
    sys.exit(1)
except LarkError as e:
     print(f"Error parsing 'minilang.lark' grammar file: {e}", file=sys.stderr)
     sys.exit(1)


# 2) Transformer 정의 (MiniLang 코드 실행 로직 포함)
@v_args(inline=True)
class MiniLangExec(Transformer):
    def __init__(self):
        super().__init__()
        self.env = {}
        self.last_result = None # REPL에서 마지막 결과 저장

    def let_stmt(self, name, value):
        self.env[name] = value
        return value

    # print_stmt 메소드는 문법 변경 후에도 동일하게 value 인자를 받습니다.
    # Lark의 v_args(inline=True)가 괄호를 플랫하게 만들어주기 때문입니다.
    def print_stmt(self, value):
        if isinstance(value, pd.DataFrame):
            print(value.to_string())
        else:
            print(value)
        return None

    def call_stmt(self, value):
        return value

    def var(self, name):
        name_str = str(name)
        if name_str not in self.env:
             raise NameError(f"Variable '{name_str}' is not defined.")
        return self.env[name_str]

    def number(self, tok):
        return float(tok)

    def string(self, tok):
        return tok[1:-1]

    def list(self, *items):
        return list(items)

    def dictionary(self, *key_value_pairs):
        d = {}
        for key, value in key_value_pairs:
             d[key] = value
        return d

    def key_value_pair(self, name, value):
        return (str(name), value)

    def keyword_argument(self, name, value):
        return (str(name), value)

    def args(self, *arguments):
        pos_args = []
        keyword_args = {}
        for arg in arguments:
            if isinstance(arg, tuple) and len(arg) == 2 and isinstance(arg[0], str):
                 keyword_args[arg[0]] = arg[1]
            else:
                 pos_args.append(arg)
        return (pos_args, keyword_args)

    def call(self, name, args_tuple=None):
        func = str(name)
        pos_args = []
        keyword_args = {}

        if args_tuple and isinstance(args_tuple, tuple) and len(args_tuple) == 2:
            pos_args, keyword_args = args_tuple
        elif args_tuple is not None:
             print(f"WARNING: Unexpected args_tuple format for function '{func}': {args_tuple}", file=sys.stderr)

        # --- 함수 구현 시작 ---
        if func == "load_csv":
            if not pos_args: raise RuntimeError("load_csv requires a file path.")
            path = pos_args[0]
            if not isinstance(path, str): raise RuntimeError(f"load_csv: expected string path, got {type(path)}")
            try: return pd.read_csv(path)
            except FileNotFoundError: raise RuntimeError(f"load_csv: File not found at '{path}'")
            except Exception as e: raise RuntimeError(f"load_csv: Error reading file '{path}': {e}")

        if func == "load_excel":
            if not pos_args: raise RuntimeError("load_excel requires a file path.")
            path = pos_args[0]
            if not isinstance(path, str): raise RuntimeError(f"load_excel: expected string path, got {type(path)}")
            try: return pd.read_excel(path)
            except FileNotFoundError: raise RuntimeError(f"load_excel: File not found at '{path}')")
            except Exception as e: raise RuntimeError(f"load_excel: Error reading file '{path}': {e}")

        if func == "concat_dataframes":
            if not pos_args or not isinstance(pos_args[0], list): raise RuntimeError("concat_dataframes requires a list of dataframes as the first positional argument.")
            dfs_list = pos_args[0]
            if not all(isinstance(df, pd.DataFrame) for df in dfs_list): raise RuntimeError("concat_dataframes: All items in the list must be DataFrames.")
            try: return pd.concat(dfs_list, ignore_index=True)
            except Exception as e: raise RuntimeError(f"concat_dataframes: Error during concatenation: {e}")

        if func == "create_pivot":
            if not pos_args: raise RuntimeError("create_pivot requires a dataframe as the first positional argument.")
            df = pos_args[0]
            if not isinstance(df, pd.DataFrame): raise RuntimeError(f"create_pivot: expected DataFrame, got {type(df)}")
            index_col = keyword_args.get('index')
            columns_col = keyword_args.get('columns')
            values_col = keyword_args.get('values')
            aggfunc = keyword_args.get('aggfunc', 'sum')
            if index_col is None or not isinstance(index_col, str): raise RuntimeError("create_pivot requires a string 'index' keyword argument.")
            if columns_col is not None and not isinstance(columns_col, (str, list)): raise RuntimeError("create_pivot 'columns' must be a string or list of strings.")
            if values_col is not None and not isinstance(values_col, (str, list)): raise RuntimeError("create_pivot 'values' must be a string or list of strings.")
            if not isinstance(aggfunc, str): raise RuntimeError("create_pivot 'aggfunc' must be a string.")
            cols_to_check = [index_col]
            if columns_col: cols_to_check.extend([columns_col] if isinstance(columns_col, str) else columns_col)
            if values_col: cols_to_check.extend([values_col] if isinstance(values_col, str) else values_col)
            cols_to_check_flat = []
            for col in cols_to_check:
                if isinstance(col, list): cols_to_check_flat.extend(col)
                else: cols_to_check_flat.append(col)
            missing_cols = [col for col in cols_to_check_flat if col not in df.columns]
            if missing_cols: raise RuntimeError(f"create_pivot: Columns not found in DataFrame: {missing_cols}")
            try:
                return pd.pivot_table( df, index=index_col, columns=columns_col, values=values_col, aggfunc=aggfunc )
            except Exception as e: raise RuntimeError(f"create_pivot: Error creating pivot table: {e}")

        if func == "visualize_pivot_stats":
            if not pos_args: raise RuntimeError("visualize_pivot_stats requires a pivot table.")
            pivot_df = pos_args[0]
            if not isinstance(pivot_df, pd.DataFrame): raise RuntimeError(f"visualize_pivot_stats: expected DataFrame (pivot table), got {type(pivot_df)}")
            print("\n--- Visualizing Pivot Table Statistics (Placeholder) ---")
            print(pivot_df.describe().to_string())
            print("\n-----------------------------------------------------")
            return None

        if func == "stats":
            if len(pos_args) < 2: raise RuntimeError("stats requires a dataframe and a list of metrics.")
            df = pos_args[0]
            metrics = pos_args[1]
            if not isinstance(df, pd.DataFrame): raise RuntimeError(f"stats: expected DataFrame, got {type(df)}")
            if not isinstance(metrics, list): raise RuntimeError(f"stats: expected list of metrics, got {type(metrics)}")
            desc = df.describe()
            missing = [m for m in metrics if m not in desc.index]
            if missing: raise RuntimeError(f"stats: unknown metrics {missing}")
            return desc.loc[metrics]
        # --- 함수 구현 끝 ---

    # --- Corrected Methods for Arithmetic ---
    # Handles addition and subtraction
    # Arguments are now first_term, op1, term1, op2, term2, ...
    def arithmetic_expr(self, first_term, *operations_and_terms):
        # --- Added Debug Print ---
        print(f"DEBUG: arithmetic_expr received first_term={first_term}, operations_and_terms={operations_and_terms}")
        # --- End Added Debug Print ---
        result = first_term
        # Iterate over the flattened list of operations and terms in pairs
        for i in range(0, len(operations_and_terms), 2):
            # --- Added Debug Prints ---
            print(f"DEBUG: arithmetic_expr loop i={i}, len={len(operations_and_terms)}")
            if i + 1 >= len(operations_and_terms):
                 print(f"DEBUG: arithmetic_expr loop will fail at i+1={i+1} because len={len(operations_and_terms)}")
            # --- End Added Debug Prints ---
            op = str(operations_and_terms[i]) # Operator token (e.g., '+', '-')
            term = operations_and_terms[i+1] # Transformed operand
            if op == '+':
                # Ensure both operands are numbers for arithmetic
                if not isinstance(result, (int, float)) or not isinstance(term, (int, float)):
                     raise RuntimeError(f"Unsupported operand types for +: {type(result)} and {type(term)}")
                result += term
            elif op == '-':
                 if not isinstance(result, (int, float)) or not isinstance(term, (int, float)):
                     raise RuntimeError(f"Unsupported operand types for -: {type(result)} and {type(term)}")
                 result -= term
            else:
                # Should not happen with current grammar
                raise RuntimeError(f"Unknown arithmetic operator: {op}")
        return result

    # Handles multiplication and division
    # Arguments are now first_factor, op1, factor1, op2, factor2, ...
    def term(self, first_factor, *operations_and_factors):
        # --- Added Debug Print ---
        print(f"DEBUG: term received first_factor={first_factor}, operations_and_factors={operations_and_factors}")
        # --- End Added Debug Print ---
        result = first_factor
        # Iterate over the flattened list of operations and factors in pairs
        for i in range(0, len(operations_and_factors), 2):
            # --- Added Debug Prints ---
            print(f"DEBUG: term loop i={i}, len={len(operations_and_factors)}")
            if i + 1 >= len(operations_and_factors):
                 print(f"DEBUG: term loop will fail at i+1={i+1} because len={len(operations_and_factors)}")
            # --- End Added Debug Prints ---
            op = str(operations_and_factors[i]) # Operator token (e.g., '*', '/')
            factor = operations_and_factors[i+1] # Transformed operand
            if op == '*':
                if not isinstance(result, (int, float)) or not isinstance(factor, (int, float)):
                     raise RuntimeError(f"Unsupported operand types for *: {type(result)} and {type(factor)}")
                result *= factor
            elif op == '/':
                if not isinstance(result, (int, float)) or not isinstance(factor, (int, float)):
                     raise RuntimeError(f"Unsupported operand types for /: {type(result)} and {type(factor)}")
                if factor == 0:
                     raise RuntimeError("Division by zero")
                result /= factor
            else:
                 # Should not happen with current grammar
                 raise RuntimeError(f"Unknown term operator: {op}")
        return result

    # factor method is not explicitly needed with v_args(inline=True)
    # Lark will pass the result of the factor rule directly to the term method

    # --- End Corrected Methods for Arithmetic ---


# 파일 내용을 한 줄씩 읽고 실행하는 함수 (REPL의 '.' 명령어에서 사용)
def run_minilang_line_by_line(file_path: str, parser: Lark, transformer: MiniLangExec):
    """
    Reads a MiniLang file line by line, handling line continuations,
    parses and executes each complete statement using the provided transformer.
    Maintains the transformer's environment across lines.
    """
    print(f"Running file '{file_path}' line by line...")
    try:
        with open(file_path, encoding="utf-8") as f:
            line_buffer = ""
            line_num_start = 0 # Track the starting line number for multi-line statements

            for line_num, line in enumerate(f, 1):
                stripped_line = line.strip()

                # Skip empty lines and comments unless they are part of a multi-line statement
                if not line_buffer and (not stripped_line or stripped_line.startswith('//')):
                    continue

                # Check for line continuation character '\'
                if stripped_line.endswith('\\'):
                    line_buffer += stripped_line[:-1] + " " # Add line to buffer, remove '\', add space
                    if not line_buffer.strip() and line_num_start == 0: # If buffer was empty before adding this line and not already tracking
                        line_num_start = line_num # Start tracking line number for this statement
                    continue # Read next line

                # If no continuation character, add the current line to the buffer and process
                line_buffer += stripped_line
                if not line_buffer.strip() and line_num_start == 0: # If buffer is still empty after adding this line and not already tracking
                     # This handles cases where a line only contained a backslash or was empty/commented
                     line_num_start = line_num # Start tracking line number for this statement
                     line_buffer = "" # Reset buffer
                     continue

                # Determine the line number to report for errors
                report_line_num = line_num_start if line_num_start > 0 else line_num

                print(f"minilang> {line_buffer}") # Print the complete statement being executed

                try:
                    # Parse the complete statement from the buffer
                    # Add a newline at the end as Lark often expects it
                    tree = parser.parse(line_buffer + "\n")

                    # Execute the parsed statement
                    transformer.transform(tree)

                except LarkError as e:
                    print(f"MiniLang Parsing Error (File line {report_line_num}): {e}", file=sys.stderr)
                    # Decide error handling: continue or stop? Continuing for now.
                except (RuntimeError, NameError) as e:
                    print(f"MiniLang Execution Error (File line {report_line_num}): {e}", file=sys.stderr)
                    # Decide error handling: continue or stop? Continuing for now.
                except Exception as e:
                    print(f"An unexpected error occurred (File line {report_line_num}): {e}", file=sys.stderr)
                    # Decide error handling: continue or stop? Continuing for now.

                # Reset buffer and line number tracking for the next statement
                line_buffer = ""
                line_num_start = 0

            # Handle any remaining content in the buffer after the loop finishes
            if line_buffer.strip():
                 report_line_num = line_num_start if line_num_start > 0 else line_num # Use the last line number or start if only one line
                 print(f"minilang> {line_buffer}")
                 try:
                     tree = parser.parse(line_buffer + "\n")
                     transformer.transform(tree)
                 except LarkError as e:
                     print(f"MiniLang Parsing Error (File line {report_line_num}): {e}", file=sys.stderr)
                 except (RuntimeError, NameError) as e:
                     print(f"MiniLang Execution Error (File line {report_line_num}): {e}", file=sys.stderr)
                 except Exception as e:
                     print(f"An unexpected error occurred (File line {report_line_num}): {e}", file=sys.stderr)


        print(f"Finished running file '{file_path}'.")
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'", file=sys.stderr)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}", file=sys.stderr)


# 파일 전체를 실행하는 함수 (CLI 모드에서 사용)
def run_minilang_script_full(file_path: str, parser: Lark, transformer: MiniLangExec):
    """
    Reads and executes the entire MiniLang script file at once.
    Used for CLI mode.
    """
    print(f"Running MiniLang script file: {file_path}")
    try:
        with open(file_path, encoding="utf-8") as f:
            code = f.read()
        tree = parser.parse(code)
        transformer.transform(tree)
        print(f"Finished running script file: {file_path}")
    except FileNotFoundError:
        print(f"Error: Input file '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except LarkError as e:
        print(f"MiniLang Parsing Error (File): {e}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, NameError) as e:
        print(f"MiniLang Execution Error (File): {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred (File): {e}", file=sys.stderr)
        sys.exit(1)


# 3) REPL 실행 함수
def run_repl():
    print("MiniLang REPL (Type 'exit' to quit, '.' to run file line by line, '!' to toggle mode)")
    transformer = MiniLangExec() # REPL 세션 동안 Transformer 인스턴스 유지
    current_mode = "minilang" # 현재 모드 ('minilang' 또는 'python')
    # Removed first_input flag - always start with minilang> prompt

    while True:
        try:
            # Current mode prompt
            prompt = "minilang> " if current_mode == "minilang" else "python> "

            line = input(prompt)

            if line.lower() == 'exit':
                break
            if not line.strip(): # Ignore empty lines
                continue

            # --- Special commands ---
            # Check for '.' command ONLY in minilang mode
            if current_mode == "minilang" and line == '.':
                file_path = input("Run file line by line: ")
                if not os.path.exists(file_path):
                    print(f"Error: File not found at '{file_path}'", file=sys.stderr)
                    continue
                # Pass the REPL's transformer instance to maintain state
                run_minilang_line_by_line(file_path, parser, transformer)
                continue # Skip to the next REPL prompt after file execution

            # Check for '!' command in ANY mode
            if line == '!':
                current_mode = "python" if current_mode == "minilang" else "minilang"
                print(f"Switched to {current_mode.capitalize()} mode.")
                continue # Skip to the next REPL prompt after mode toggle
            # --- End Special commands ---

            # --- Mode-specific execution ---
            if current_mode == "minilang":
                # MiniLang mode: Parse and execute the single line (or multi-line with \)
                # Note: Multi-line handling for direct REPL input is not implemented here,
                # only for file execution via '.' command.
                try:
                    # Add a newline at the end as Lark often expects it
                    tree = parser.parse(line + "\n")
                    result = transformer.transform(tree)
                    transformer.last_result = result # Store the result

                    # Print the result if it's not None (e.g., from assignment, not print_stmt)
                    if result is not None:
                        print(result)

                except LarkError as e:
                    print(f"MiniLang Parsing Error: {e}", file=sys.stderr)
                except (RuntimeError, NameError) as e:
                    print(f"MiniLang Execution Error: {e}", file=sys.stderr)
                except Exception as e:
                    print(f"An unexpected error occurred: {e}", file=sys.stderr)

            elif current_mode == "python":
                # Python mode: Execute the single line of Python code
                try:
                    # Try eval first for expressions
                    # Pass the transformer's environment for variable access
                    result = eval(line, transformer.env, transformer.env)
                    # Print result if not None
                    if result is not None:
                         print(result)
                except SyntaxError:
                    # If eval fails, try exec for statements
                    try:
                        # Pass the transformer's environment
                        exec(line, transformer.env, transformer.env)
                        transformer.last_result = None # exec doesn't return a result
                    except Exception as e:
                        print(f"Python Execution Error: {e}", file=sys.stderr)
                except Exception as e:
                     # Catch other exceptions during eval
                    print(f"Python Execution Error: {e}", file=sys.stderr)

        except EOFError: # Handle Ctrl+D
            print("\nExiting REPL.")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)


# 4) Main entry point
if __name__ == "__main__":
    # Use argparse to parse command line arguments
    parser_cli = argparse.ArgumentParser(description="MiniLang REPL or CLI Interpreter")
    parser_cli.add_argument("input_file", nargs="?", help="MiniLang script file to run in CLI mode")

    args = parser_cli.parse_args()

    # The Lark parser is initialized outside to be used by both modes

    if args.input_file:
        # If an argument is provided, run in CLI mode
        # Create a new transformer instance for the CLI run
        cli_transformer = MiniLangExec()
        run_minilang_script_full(args.input_file, parser, cli_transformer)
    else:
        # If no argument, run in REPL mode
        run_repl()