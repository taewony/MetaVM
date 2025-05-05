#!/usr/bin/env python3
import sys
import pandas as pd
from lark import Lark, Transformer, v_args, LarkError, Tree # Import Tree
import argparse

# 1) Lark 파서 초기화 (main 함수 안으로 이동)

# 2) Transformer 정의
@v_args(inline=True)
class MiniLangExec(Transformer):
    def __init__(self):
        super().__init__()
        self.env = {}

    def let_stmt(self, name, value):
        self.env[name] = value

    def print_stmt(self, value):
        if isinstance(value, pd.DataFrame):
            # Use to_string() for better display of DataFrames in console
            print(value.to_string())
        else:
            print(value)

    def call_stmt(self, value):
        # For a standalone call statement, we just execute the call.
        # The result is typically ignored.
        return value # The result of the call method

    def var(self, name):
        # Check if the variable exists in the environment
        if name not in self.env:
             raise NameError(f"Variable '{name}' is not defined.")
        return self.env[name]

    def number(self, tok):
        return float(tok)

    def string(self, tok):
        # Remove quotes from the string literal
        return tok[1:-1]

    # Handles lists containing any expressions
    def list(self, *items):
        # items are already transformed expressions
        return list(items)

    # Handles dictionary literals { key=value, ... }
    def dictionary(self, *key_value_pairs):
        d = {}
        for key, value in key_value_pairs: # key_value_pair transformation returns (key_string, value)
             d[key] = value
        return d

    # Handles key=value pairs within dictionaries or as keyword arguments
    def key_value_pair(self, name, value):
        # Returns a tuple of (key_string, value)
        return (str(name), value)

    # --- Added Method ---
    # Handles the transformation of the 'keyword_argument' rule
    # This ensures args method receives a consistent tuple format
    def keyword_argument(self, name, value):
        # The 'name' here is the transformed NAME token (a string)
        # The 'value' here is the transformed expr
        return (str(name), value) # Return as (key_string, value) tuple
    # --- End Added Method ---


    # --- Crucial Change Here ---
    # Handles the arguments list for function calls
    # Collects positional and keyword arguments separately
    def args(self, *arguments):
        pos_args = []
        keyword_args = {}
        for arg in arguments:
            # Check if the argument is the result of transforming a 'keyword_argument' rule
            # which is now explicitly a tuple thanks to the new keyword_argument method
            if isinstance(arg, tuple) and len(arg) == 2 and isinstance(arg[0], str):
                 keyword_args[arg[0]] = arg[1]
            # --- Removed the check for Tree type here ---
            # elif isinstance(arg, Tree) and arg.data == 'keyword_argument':
            #      # This case is no longer needed with the dedicated keyword_argument method
            #      # The result of keyword_argument transformation is now the tuple itself
            #      pass # This logic was incorrect anyway
            # --- End Removed Check ---
            else:
                 # Otherwise, it's a positional argument (transformed expression value)
                 pos_args.append(arg)
        # Return a tuple containing the list of positional args and the dictionary of keyword args
        return (pos_args, keyword_args)

    # --- Crucial Change Here ---
    # Handles function calls, now correctly receiving and using pos_args and keyword_args
    def call(self, name, args_tuple=None):
        func = str(name)
        pos_args = []
        keyword_args = {}

        # --- Added Debug Prints ---
        print(f"DEBUG: call method received name='{func}', args_tuple={args_tuple}")
        # --- End Added Debug Prints ---

        # Unpack the tuple returned by the args method
        if args_tuple and isinstance(args_tuple, tuple) and len(args_tuple) == 2:
            pos_args, keyword_args = args_tuple
        elif args_tuple is not None:
             # This case should ideally not happen if grammar and args transformer are correct
             print(f"WARNING: Unexpected args_tuple format for function '{func}': {args_tuple}", file=sys.stderr)


        print(f"DEBUG: Calling function '{func}' with positional args: {pos_args}, keyword args: {keyword_args}") # Original Debug print

        # --- Implement functions based on the new grammar and Excel example ---

        # load_excel function
        if func == "load_excel":
            if not pos_args:
                 raise RuntimeError("load_excel requires a file path.")
            path = pos_args[0]
            if not isinstance(path, str):
                 raise RuntimeError(f"load_excel: expected string path, got {type(path)}")
            try:
                # Assuming load_excel needs pandas.read_excel
                return pd.read_excel(path)
            except FileNotFoundError:
                raise RuntimeError(f"load_excel: File not found at '{path}')")
            except Exception as e:
                raise RuntimeError(f"load_excel: Error reading file '{path}': {e}")

        # concat_dataframes function
        if func == "concat_dataframes":
            if not pos_args or not isinstance(pos_args[0], list):
                 raise RuntimeError("concat_dataframes requires a list of dataframes as the first positional argument.")
            dfs_list = pos_args[0]
            # Basic type check for list elements
            if not all(isinstance(df, pd.DataFrame) for df in dfs_list):
                 raise RuntimeError("concat_dataframes: All items in the list must be DataFrames.")
            try:
                return pd.concat(dfs_list, ignore_index=True) # ignore_index=True often useful after concat
            except Exception as e:
                raise RuntimeError(f"concat_dataframes: Error during concatenation: {e}")

        # create_pivot function
        if func == "create_pivot":
            if not pos_args:
                 raise RuntimeError("create_pivot requires a dataframe as the first positional argument.")
            df = pos_args[0]
            if not isinstance(df, pd.DataFrame):
                 raise RuntimeError(f"create_pivot: expected DataFrame, got {type(df)}")

            # --- Use keyword_args dictionary ---
            index_col = keyword_args.get('index')
            columns_col = keyword_args.get('columns')
            values_col = keyword_args.get('values')
            aggfunc = keyword_args.get('aggfunc', 'sum') # Default aggregation function is now 'sum' as per example

            # Basic validation
            if index_col is None or not isinstance(index_col, str): # 'index' is required and must be a string
                 raise RuntimeError("create_pivot requires a string 'index' keyword argument.")
            # columns_col and values_col can be None, but if provided, should be strings or lists of strings
            if columns_col is not None and not isinstance(columns_col, (str, list)):
                 raise RuntimeError("create_pivot 'columns' must be a string or list of strings.")
            if values_col is not None and not isinstance(values_col, (str, list)):
                 raise RuntimeError("create_pivot 'values' must be a string or list of strings.")
            if not isinstance(aggfunc, str):
                 raise RuntimeError("create_pivot 'aggfunc' must be a string.")

            # Check if specified columns exist in the dataframe
            cols_to_check = [index_col]
            if columns_col:
                 cols_to_check.extend([columns_col] if isinstance(columns_col, str) else columns_col)
            if values_col:
                 cols_to_check.extend([values_col] if isinstance(values_col, str) else values_col)

            # Ensure columns_col and values_col are lists if they are single strings, for consistent lookup
            cols_to_check_flat = []
            for col in cols_to_check:
                if isinstance(col, list):
                    cols_to_check_flat.extend(col)
                else:
                    cols_to_check_flat.append(col)


            missing_cols = [col for col in cols_to_check_flat if col not in df.columns]
            if missing_cols:
                 raise RuntimeError(f"create_pivot: Columns not found in DataFrame: {missing_cols}")

            try:
                # Use pandas.pivot_table, passing keyword arguments directly
                return pd.pivot_table(
                    df,
                    index=index_col,
                    columns=columns_col,
                    values=values_col,
                    aggfunc=aggfunc
                )
            except Exception as e:
                raise RuntimeError(f"create_pivot: Error creating pivot table: {e}")


        # visualize_pivot_stats function (Placeholder)
        if func == "visualize_pivot_stats":
            if not pos_args:
                 raise RuntimeError("visualize_pivot_stats requires a pivot table.")
            pivot_df = pos_args[0]
            if not isinstance(pivot_df, pd.DataFrame):
                 raise RuntimeError(f"visualize_pivot_stats: expected DataFrame (pivot table), got {type(pivot_df)}")

            print("\n--- Visualizing Pivot Table Statistics (Placeholder) ---")
            # In a real implementation, this would use a plotting library like matplotlib or seaborn
            # For now, just print a summary or the table itself
            print(pivot_df.describe().to_string()) # Print descriptive stats of the pivot table
            print("\n-----------------------------------------------------")
            return None # Visualization functions often don't return a value

        # --- Original functions ---
        # load_csv function
        if func == "load_csv":
            if not pos_args:
                 raise RuntimeError("load_csv requires a file path.")
            path = pos_args[0] # Use pos_args
            if not isinstance(path, str):
                 raise RuntimeError(f"load_csv: expected string path, got {type(path)}")
            try:
                return pd.read_csv(path)
            except FileNotFoundError:
                raise RuntimeError(f"load_csv: File not found at '{path}'")
            except Exception as e:
                raise RuntimeError(f"load_csv: Error reading file '{path}': {e}")


        # stats function
        if func == "stats":
            if len(pos_args) < 2:
                 raise RuntimeError("stats requires a dataframe and a list of metrics.")
            df = pos_args[0] # Use pos_args
            metrics = pos_args[1] # Use pos_args

            if not isinstance(df, pd.DataFrame):
                 raise RuntimeError(f"stats: expected DataFrame, got {type(df)}")
            if not isinstance(metrics, list):
                 raise RuntimeError(f"stats: expected list of metrics, got {type(metrics)}")

            desc = df.describe()
            missing = [m for m in metrics if m not in desc.index]
            if missing:
                 raise RuntimeError(f"stats: unknown metrics {missing}")
            return desc.loc[metrics]

        # --- End of function implementations ---

        raise RuntimeError(f"Unknown function: {func}")


# 3) 실행 함수
def run_minilang(code: str, parser: Lark):
    try:
        tree = parser.parse(code)
        print("DEBUG: Parse successful. AST:") # Debug print
        print(tree.pretty()) # Print the parse tree for debugging
        MiniLangExec().transform(tree)
    except LarkError as e:
        print(f"MiniLang Parsing Error: {e}", file=sys.stderr)
    except RuntimeError as e:
        print(f"MiniLang Execution Error: {e}", file=sys.stderr)
    except NameError as e:
        print(f"MiniLang Execution Error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)


# 4) 메인
def main():
    # Use argparse for better command line argument handling
    parser_cli = argparse.ArgumentParser(description="MiniLang Interpreter and Grammar Checker")
    parser_cli.add_argument("input_file", nargs="?", help="MiniLang script file to run (or stdin if not provided)")
    parser_cli.add_argument("-lark", action="store_true", help="Check the minilang.lark grammar file for syntax errors")

    args = parser_cli.parse_args()

    # Load the grammar file first, as it's needed for both modes
    try:
        with open("minilang.lark", encoding="utf-8") as f:
            grammar = f.read()
        lark_parser = Lark(grammar, parser="lalr", propagate_positions=True) # propagate_positions=True useful for error reporting
        print("DEBUG: Grammar file 'minilang.lark' loaded successfully.") # Debug print
    except FileNotFoundError:
        print("Error: 'minilang.lark' grammar file not found.", file=sys.stderr)
        sys.exit(1)
    except LarkError as e:
         print(f"Error parsing 'minilang.lark' grammar file: {e}", file=sys.stderr)
         sys.exit(1)


    if args.lark:
        # If -lark option is used, just check the grammar file itself
        print("Checking MiniLang grammar file 'minilang.lark'...")
        print("MiniLang grammar file syntax is valid.")
    else:
        # If -lark option is not used, run the MiniLang script
        if args.input_file:
            try:
                code = open(args.input_file, encoding="utf-8").read()
            except FileNotFoundError:
                print(f"Error: Input file '{args.input_file}' not found.", file=sys.stderr)
                sys.exit(1)
        else:
            print("Reading MiniLang code from stdin...")
            code = sys.stdin.read()

        print("Running MiniLang script...")
        run_minilang(code, lark_parser) # Pass the loaded parser to run_minilang


if __name__ == "__main__":
    main()
