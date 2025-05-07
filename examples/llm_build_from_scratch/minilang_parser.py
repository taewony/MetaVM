# minilang_parser.py

from lark import Lark, Transformer, v_args, Token, Tree
import operator

# 간단한 DataFrame 및 PivotTable 모의 객체 (Simple mock objects for DataFrame and PivotTable)
# 실제 Pandas/Numpy 대신 사용됩니다. (Used instead of actual Pandas/Numpy)
class MockDataFrame:
    def __init__(self, data, columns=None, name="DataFrame"):
        self.name = name
        if isinstance(data, str) and data.endswith(".csv"): # 파일 경로인 경우 (If it's a file path)
            self.source_file = data
            # 실제 파일 로딩 대신, 파일 이름을 기반으로 간단한 더미 데이터 생성
            # (Instead of actual file loading, generate simple dummy data based on the file name)
            if "titanic" in data:
                self.columns = ["PassengerId", "Survived", "Pclass", "Name", "Sex", "Age"]
                self.data = [
                    [1, 0, 3, "Braund, Mr. Owen Harris", "male", 22.0],
                    [2, 1, 1, "Cumings, Mrs. John Bradley (Florence Briggs Thayer)", "female", 38.0],
                    [3, 1, 3, "Heikkinen, Miss. Laina", "female", 26.0]
                ]
            else:
                self.columns = [f"col{i+1}" for i in range(2)]
                self.data = [[f"{data}_r{r}_c{c}" for c in range(2)] for r in range(3)]

        elif isinstance(data, list) and all(isinstance(row, list) for row in data): # 데이터 리스트인 경우 (If it's a list of data)
            self.data = data
            self.columns = columns if columns else [f"col{i+1}" for i in range(len(data[0]) if data else 0)]
        else:
            self.data = []
            self.columns = []

    def __str__(self):
        header = "\t".join(self.columns)
        rows = ["\t".join(map(str, row)) for row in self.data[:5]] # 처음 5개 행만 표시 (Display only the first 5 rows)
        return f"MockDataFrame '{self.name}':\n{header}\n" + "\n".join(rows) + ("\n..." if len(self.data) > 5 else "")

    def head(self, n=5):
        return MockDataFrame(self.data[:n], self.columns, name=f"{self.name}.head({n})")


class MiniLangTransformer(Transformer):
    # FIX: Correct the typo in the __init__ method definition
    def __init__(self): # Corrected from def __init__(self__(self):
        super().__init__()
        self.env = {}
        # 내장 함수 정의
        self.env.update({
            "load_csv": self._load_csv,
            "stats": self._stats,
            "concat_dataframes": self._concat_dataframes,
            "create_pivot": self._create_pivot,
        })

    # --- Helper methods for execution ---
    def _load_csv(self, file_path):
        print(f"Executing: load_csv('{file_path}')")
        # 실제 CSV 로딩 대신 모의 DataFrame 반환
        return MockDataFrame(file_path, name=file_path.split('/')[-1].split('.')[0])

    def _stats(self, dataframe, operations):
        print(f"Executing: stats on DataFrame '{dataframe.name}', operations: {operations}")
        if not isinstance(dataframe, MockDataFrame):
            raise TypeError("stats() first argument must be a DataFrame.")
        results = {"dataframe": dataframe.name}
        # 모의 통계 계산
        num_cols = [col for col in dataframe.columns if all(isinstance(row[dataframe.columns.index(col)], (int, float)) for row in dataframe.data)]

        for op in operations:
            if op == "mean":
                for col_name in num_cols:
                    col_idx = dataframe.columns.index(col_name)
                    col_data = [row[col_idx] for row in dataframe.data if isinstance(row[col_idx], (int, float))]
                    results[f"{col_name}_mean"] = sum(col_data) / len(col_data) if col_data else float('nan')
            elif op == "std":
                 for col_name in num_cols:
                    col_idx = dataframe.columns.index(col_name)
                    col_data = [row[col_idx] for row in dataframe.data if isinstance(row[col_idx], (int, float))]
                    mean = sum(col_data) / len(col_data) if col_data else 0
                    variance = sum([(x - mean) ** 2 for x in col_data]) / len(col_data) if col_data else 0
                    results[f"{col_name}_std"] = variance ** 0.5
            elif op == "50%" or op == "median":
                for col_name in num_cols:
                    col_idx = dataframe.columns.index(col_name)
                    col_data = sorted([row[col_idx] for row in dataframe.data if isinstance(row[col_idx], (int, float))])
                    if col_data:
                        mid = len(col_data) // 2
                        results[f"{col_name}_median"] = (col_data[mid -1] + col_data[mid]) / 2 if len(col_data) % 2 == 0 else col_data[mid]
                    else:
                        results[f"{col_name}_median"] = float('nan')
            else:
                results[op] = f"mock_value_for_{op}"
        return results

    def _concat_dataframes(self, df_list, axis=0):
        print(f"Executing: concat_dataframes on {len(df_list)} DataFrames")
        if not all(isinstance(df, MockDataFrame) for df in df_list):
            raise TypeError("concat_dataframes() argument must be a list of DataFrames.")

        all_data = []
        all_columns = []
        if df_list:
            all_columns = list(df_list[0].columns)
            for df in df_list:
                if list(df.columns) != all_columns:
                    print(f"Warning: DataFrame '{df.name}' has different columns. Using columns from the first DataFrame.")
                all_data.extend(df.data)

        return MockDataFrame(all_data, columns=all_columns, name="merged_data")

    def _create_pivot(self, dataframe, index, columns, values, aggfunc):
        print(f"Executing: create_pivot on DataFrame '{dataframe.name}' with index='{index}', columns='{columns}', values='{values}', aggfunc='{aggfunc}'")
        if not isinstance(dataframe, MockDataFrame):
            raise TypeError("create_pivot() first argument must be a DataFrame.")
        # 모의 피벗 테이블 생성
        return {"pivot_config": {"index": index, "columns": columns, "values": values, "aggfunc": aggfunc},
                "data": f"mock_pivot_table_from_{dataframe.name}"}


    # --- Lark Transformer methods ---
    # REMOVE the @v_args(inline=True) decorator from assignment method
    def assignment(self, children_results): # Lark passes children results here
        # When @v_args(inline=True) is removed for 'assignment: LET CNAME EQ expression',
        # based on debug output, Lark passes a list of length 2: [Token('CNAME', 'a'), value_of_expression].
        # It seems to discard the LET and EQ tokens by default even if they have transformer methods.

        print(f"DEBUG: assignment received children_results={children_results}, type={type(children_results)}, len={len(children_results) if isinstance(children_results,list) else 'N/A'}")

        # We expect children_results to be a list of exactly 2 items: [CNAME_token, value_of_expression]
        # based on the observed debug output.
        if not isinstance(children_results, list) or len(children_results) != 2:
             # If the structure is ever different, this will catch it.
             raise ValueError(f"Unexpected input structure or number of children results for assignment. Expected a list of 2 items ([CNAME_token, value]), got {type(children_results).__name__} with length {len(children_results) if isinstance(children_results,list) else 'N/A'}. Input: {children_results}")


        # Unpack the 2 items based on the observed debug structure: [CNAME, expression]
        name_token = children_results[0]
        value = children_results[1] # This should be the evaluated expression result (e.g., integer 10)


        # Basic type check for the name_token
        if not isinstance(name_token, Token) or name_token.type != 'CNAME':
             raise TypeError(f"Expected CNAME token as the first item in assignment children results, got {type(name_token).__name__} type {name_token.type}. Input: {children_results}")

        # No strict type check on 'value' as it can be various expression results.

        # Now perform the core logic: assign the value to the variable name
        name = name_token.value # Get the variable name string from the CNAME token object
        self.env[name] = value # Assign the evaluated value (which should be 10 in this test case)
        print(f"Assigned: {name} = {value}") # Print confirmation

        return value # Return the assigned value
        
    @v_args(inline=True)
    # Update signature to accept all 4 arguments from the grammar rule:
    # PRINT, "(", expression, ")"
    # We only need the value (the expression result)
    def print_statement(self, print_token, open_paren_token, value, close_paren_token):
        # print(f"DEBUG: Print - print_token:{print_token}, open_paren:{open_paren_token}, value:{value}, close_paren:{close_paren_token}") # Optional debug
        print("Output:", value)
        return value    

    def expression_statement(self, items):
        return items[0]

    @v_args(inline=True) # This seems correct
    def expression(self, item):
        return item

    # --- Arithmetic operations ---
    # Processing the standard structure for a (op b)*: [a_result, [op1_token, b1_result, op2_token, b2_result, ...]]

    def arithmetic_expression(self, items): # term (("+"|"-") term)*
        # Expected structure: [term_result, [Token op1, term_result_2, Token op2, term_result_3, ...]]
        # If only a single term: [term_result]
        print(f"DEBUG: arith items={items}, type={type(items)}, len={len(items) if isinstance(items,list) else 'N/A'}")

        if not isinstance(items, list) or len(items) == 0:
             raise TypeError(f"Unexpected input structure for arithmetic_expression. Expected a non-empty list, got {type(items).__name__} with length {len(items) if isinstance(items, list) else 'N/A'}. Items: {items}")

        result = items[0] # First term result (should be a number)

        if len(items) > 1: # Check if the repeated group matched
            # items[1] should be the list containing the operator/term pairs
            op_pairs = items[1]

            print(f"DEBUG: arith op_pairs={op_pairs}, type={type(op_pairs)}, len={len(op_pairs) if isinstance(op_pairs,list) else 'N/A'}")

            # Check if op_pairs is indeed a list as expected for repetition results
            if not isinstance(op_pairs, list):
                 # This check now correctly identifies if items[1] is NOT the expected list.
                 raise TypeError(f"Expected list of operator/term pairs as the second item in arithmetic_expression, but received {type(op_pairs).__name__}. Items: {items}. Value of items[1]: {items[1]}")

            # Process the pairs within the list: [op1, operand2, op2, operand3, ...]
            try:
                for i in range(0, len(op_pairs), 2): # <- len() is called on op_pairs here
                    # Ensure we have a pair of items
                    if i + 1 >= len(op_pairs):
                         raise SyntaxError(f"Malformed operator/term pair list in arithmetic_expression. Odd number of items in {op_pairs}. Items: {items}")

                    op_token = op_pairs[i]     # Operator token (e.g., Token('+', '+'))
                    right_operand = op_pairs[i+1] # Result of the right-hand term (should be a number)

                    # Ensure op_token is actually a Token before accessing value
                    if not isinstance(op_token, Token):
                         raise TypeError(f"Expected operator Token in operator/term pair, but received {type(op_token).__name__}. Value: {op_token}. Pair index: {i}. Op_pairs: {op_pairs}. Items: {items}")

                    op_char = op_token.value

                    # Perform the operation - this expects result and right_operand to be numbers
                    try:
                        if op_char == '+':
                            result = operator.add(result, right_operand)
                        elif op_char == '-':
                            result = operator.sub(result, right_operand)
                        else:
                             raise SyntaxError(f"Unexpected operator '{op_char}' in arithmetic expression.")
                    except TypeError as e:
                         # Catch TypeErrors specifically for the operation
                         raise TypeError(f"Cannot perform {op_char} operation on {type(result).__name__} ({result}) and {type(right_operand).__name__} ({right_operand}). Original error: {e}. Items: {items}. Op_pairs: {op_pairs}")
            except TypeError as e:
                 # Catch TypeErrors during the loop iteration or len(op_pairs) check
                 raise TypeError(f"Error processing operator/term pairs list in arithmetic_expression: {e}. Op_pairs: {op_pairs}. Items: {items}")


        return result


    def term(self, items):
        """Handles multiplication, division, modulo: factor (("*"|"/"|"%") factor)*"""
        # Expected structure: [factor_result, [Token op1, factor_result_2, Token op2, factor_result_3, ...]]
        # If only a single factor: [factor_result]

        print(f"DEBUG: term items={items}, type={type(items)}, len={len(items) if isinstance(items,list) else 'N/A'}")


        if not isinstance(items, list) or len(items) == 0:
             raise TypeError(f"Unexpected input structure for term. Expected a non-empty list, got {type(items).__name__} with length {len(items) if isinstance(items, list) else 'N/A'}. Items: {items}")


        result = items[0] # First factor result

        if len(items) > 1: # Check if the repeated group matched
            # items[1] should be the list containing the operator/factor pairs
            op_pairs = items[1]
            print(f"DEBUG: term op_pairs={op_pairs}, type={type(op_pairs)}, len={len(op_pairs) if isinstance(op_pairs,list) else 'N/A'}")


            # Check if op_pairs is indeed a list as expected for repetition results
            if not isinstance(op_pairs, list):
                 # This check now correctly identifies if items[1] is NOT the expected list.
                 raise TypeError(f"Expected list of operator/factor pairs as the second item in term, but received {type(op_pairs).__name__}. Items: {items}. Value of items[1]: {items[1]}")


            # Process the pairs within the list: [op1, operand2, op2, operand3, ...]
            try:
                for i in range(0, len(op_pairs), 2): # <- len() is called on op_pairs here
                    # Ensure we have a pair of items
                    if i + 1 >= len(op_pairs):
                         raise SyntaxError(f"Malformed operator/factor pair list in term. Odd number of items in {op_pairs}. Items: {items}")

                    op_token = op_pairs[i]
                    right_operand = op_pairs[i + 1]

                    if not isinstance(op_token, Token):
                         raise TypeError(f"Expected operator Token in operator/factor pair, but received {type(op_token).__name__}. Value: {op_token}. Pair index: {i}. Op_pairs: {op_pairs}. Items: {items}")

                    op_char = op_token.value

                    try:
                        if op_char == '*':
                            result = operator.mul(result, right_operand)
                        elif op_char == '/':
                            if right_operand == 0: raise ZeroDivisionError("Division by zero")
                            result = operator.truediv(result, right_operand)
                        elif op_char == '%':
                            if right_operand == 0: raise ZeroDivisionError("Modulo by zero")
                            result = operator.mod(result, right_operand)
                        else:
                            raise SyntaxError(f"Unexpected operator '{op_char}' in term.")
                    except TypeError as e:
                         raise TypeError(f"Cannot perform {op_char} operation on {type(result).__name__} ({result}) and {type(right_operand).__name__} ({right_operand}). Original error: {e}. Items: {items}. Op_pairs: {op_pairs}")
            except TypeError as e:
                 # Catch TypeErrors during the loop iteration or len(op_pairs) check
                 raise TypeError(f"Error processing operator/factor pairs list in term: {e}. Op_pairs: {op_pairs}. Items: {items}")

        return result


    def factor(self, items):
        """Handles unary operations and power: power | unary_op factor"""
        print(f"DEBUG: factor items={items}, type={type(items)}, len={len(items) if isinstance(items,list) else 'N/A'}")
        if not isinstance(items, list) or len(items) == 0:
             raise TypeError(f"Unexpected input structure for factor. Expected a list with at least one item, got {type(items).__name__} with length {len(items) if isinstance(items, list) else 'N/A'}. Items: {items}")


        if len(items) == 1:
            return items[0] # Result from power
        elif len(items) == 2:
            op_token, operand = items # op_token is Token, operand is factor result
            print(f"DEBUG: factor unary op_token={op_token}, type={type(op_token)}, operand={operand}, type={type(operand)}")
            if not isinstance(op_token, Token):
                 raise TypeError(f"Expected unary operator Token, but received {type(op_token).__name__} in factor. Items: {items}")
            op_char = op_token.value

            # Perform the operation - this expects operand to be a number or boolean
            try:
                if op_char == '-':
                    result = -operand
                elif op_char == '+':
                    result = +operand
                elif op_char == '!':
                    result = not operand
                else:
                    raise SyntaxError(f"Unknown unary operator: {op_char}")
            except TypeError as e:
                 raise TypeError(f"Cannot perform unary {op_char} operation on {type(operand).__name__}. Original error: {e}. Items: {items}")

            return result
        else:
            raise SyntaxError(f"Invalid factor expression structure. Expected 1 or 2 items, got {len(items)}. Items: {items}")


    def power(self, items):
        """Handles exponentiation: atom_expression ("**" factor)?"""
        print(f"DEBUG: power items={items}, type={type(items)}, len={len(items) if isinstance(items,list) else 'N/A'}")
        if not isinstance(items, list) or len(items) == 0:
             raise TypeError(f"Unexpected input structure for power. Expected a list with at least one item, got {type(items).__name__} with length {len(items) if isinstance(items, list) else 'N/A'}. Items: {items}")

        if len(items) == 1:
            return items[0] # Result from atom_expression
        elif len(items) == 3:
            base, op_token, exponent = items # op_token is Token
            print(f"DEBUG: power base={base}, type={type(base)}, op_token={op_token}, type={type(op_token)}, exponent={exponent}, type={type(exponent)}")
            if not isinstance(op_token, Token):
                 raise TypeError(f"Expected power operator Token, but received {type(op_token).__name__} in power. Items: {items}")
            if op_token.value == '**':
                 try:
                    result = operator.pow(base, exponent)
                 except TypeError as e:
                     raise TypeError(f"Cannot perform '**' operation on {type(base).__name__} ({base}) and {type(exponent).__name__} ({exponent}). Original error: {e}. Items: {items}")

                 return result
            else:
                raise SyntaxError(f"Unexpected operator '{op_token.value}' in power expression. Items: {items}")
        else:
            raise SyntaxError(f"Invalid power expression structure. Expected 1 or 3 items, got {len(items)}. Items: {items}")


    @v_args(inline=True)
    def atom_expression(self, item):
        """Handles parentheses and primary expressions"""
        print(f"DEBUG: atom_expression received item: {item}, type: {type(item)}")
        return item


    @v_args(inline=True)
    def primary_expression(self, item):
        """Handles literals, variable references, and function calls"""
        print(f"DEBUG: primary_expression received item: {item}, type: {type(item)}")
        if isinstance(item, Token) and item.type == 'CNAME':
            var_name = item.value
            if var_name in self.env:
                return self.env[var_name]
            else:
                raise NameError(f"Variable '{var_name}' is not defined.")
        return item # Result from literal or call_expression

    @v_args(inline=True) # This should be correct now
    def literal(self, item):
        """Handles literals (numbers, strings, etc.)"""
        print(f"DEBUG: literal received item: {item}, type: {type(item)}")
        return item

    @v_args(inline=True)
    def string_literal(self, token): # Corrected parameter name to token as it's inline True with one token child
        print(f"DEBUG: string_literal received token: {token}, type: {type(token)}")
        s = token.value
        if (s.startswith('"') and s.endswith('"')) or \
           (s.startswith("'") and s.endswith("'")):
             return s[1:-1]
        return s


    @v_args(inline=True)
    def number_literal(self, token):
        print(f"DEBUG: number_literal received token: {token}, type: {type(token)}")
        val_str = token.value
        if '.' in val_str or 'e' in val_str or 'E' in val_str:
            return float(val_str)
        return int(val_str)

    @v_args(inline=True)
    def boolean_literal(self, token):
        print(f"DEBUG: boolean_literal received token: {token}, type: {type(token)}")
        return token.value == "True"

    @v_args(inline=True)
    def none_literal(self, token):
        print(f"DEBUG: none_literal received token: {token}, type: {type(token)}")
        return None

    # --- List and Dict handling ---
    def list_literal(self, items):
        print(f"DEBUG: list_literal received items: {items}, type={type(items)}, len={len(items) if isinstance(items,list) else 'N/A'}")
        if not isinstance(items, list):
             raise TypeError(f"Unexpected input structure for list_literal. Expected a list, got {type(items).__name__}. Items: {items}")
        return list(items)

    def dict_literal(self, items):
        print(f"DEBUG: dict_literal received items: {items}, type={type(items)}, len={len(items) if isinstance(items,list) else 'N/A'}")
        if not isinstance(items, list):
             raise TypeError(f"Unexpected input structure for dict_literal. Expected a list, got {type(items).__name__}. Items: {items}")

        d = {}
        for key, value in items:
             if not isinstance(key, str):
                  raise TypeError(f"Unexpected key type in dict_literal items. Expected string, got {type(key).__name__}. Value: {key}. Items: {items}")
             d[key] = value
        return d

    @v_args(inline=True)
    def dict_entry(self, key_item, value):
        print(f"DEBUG: dict_entry received key_item: {key_item}, type: {type(key_item)}, value: {value}, type: {type(value)}")

        key = key_item

        if isinstance(key_item, Token) and key_item.type == 'CNAME':
            key = key_item.value

        if not isinstance(key, str):
             raise TypeError(f"Dictionary key must be a string or identifier value, but got {type(key).__name__}. Original item: {key_item}")

        return key, value

    # --- Function call handling ---
    def arguments(self, items):
         print(f"DEBUG: arguments received items: {items}, type={type(items)}, len={len(items) if isinstance(items,list) else 'N/A'}")
         if not isinstance(items, list):
              raise TypeError(f"Unexpected input structure for arguments. Expected a list, got {type(items).__name__}. Items: {items}")
         return items

    @v_args(inline=True)
    def arg(self, item1, item2=None, item3=None):
        print(f"DEBUG: arg received item1: {item1}, type: {type(item1)}, item2: {item2}, type: {type(item2)}, item3: {item3}, type: {type(item3)}")
        if item2 is not None and item3 is not None:
            if not isinstance(item1, Token) or item1.type != 'CNAME':
                 raise SyntaxError(f"Expected CNAME token for keyword argument name, but got {type(item1).__name__}. Items: {item1}, {item2}, {item3}")
            return ('__kw__', item1.value, item3)
        else:
            return item1


    @v_args(inline=True)
    def call_expression(self, func_name_token, args_list=None):
        print(f"DEBUG: call_expression received func_name_token: {func_name_token}, type: {type(func_name_token)}, args_list: {args_list}, type: {type(args_list)}")
        if not isinstance(func_name_token, Token) or func_name_token.type != 'CNAME':
             raise SyntaxError(f"Expected CNAME token for function name, but got {type(func_name_token).__name__}. Token: {func_name_token}")

        func_name = func_name_token.value

        if func_name not in self.env or not callable(self.env[func_name]):
            raise NameError(f"Function '{func_name}' not defined or not callable.")

        func = self.env[func_name]

        pos_args = []
        kw_args = {}
        if args_list is not None:
            if not isinstance(args_list, list):
                 raise TypeError(f"Expected list of arguments from 'arguments' method, but got {type(args_list).__name__}. Value: {args_list}")

            for arg in args_list:
                if isinstance(arg, tuple) and arg[0] == '__kw__':
                    if len(arg) != 3 or not isinstance(arg[1], str):
                         raise TypeError(f"Malformed keyword argument tuple: {arg}")
                    kw_args[arg[1]] = arg[2]
                else:
                    pos_args.append(arg)

        try:
            result = func(*pos_args, **kw_args)
            return result
        except Exception as e:
             raise RuntimeError(f"Error calling function '{func_name}': {e}") from e


    # --- Top-level rules ---
    def program(self, items):
        print(f"DEBUG: program received items: {items}, type={type(items)}, len={len(items) if isinstance(items,list) else 'N/A'}")
        if not isinstance(items, list):
             raise TypeError(f"Unexpected input structure for program. Expected a list, got {type(items).__name__}. Items: {items}")
        # Process each statement sequentially
        last_result = None
        for item in items:
             # If EOS or $END is included in items, skip processing them as statements
             if isinstance(item, Token) and item.type in ('EOS', '$END'):
                  continue # Skip the EOS/END_OF_PROGRAM token in the items list
             last_result = item # Or execute the statement if needed, but statement rules often execute directly

        # If using statement rules that return results, you might process them here
        # For this grammar, statements print or assign, so returning the last result is fine.
        return last_result


    def empty_statement(self, _):
        print("DEBUG: empty_statement called")
        return None # Empty lines do nothing


def get_minilang_parser():
    """minilang.lark 파일을 읽어 Lark 파서 객체를 반환합니다."""
    with open("minilang.lark", "r", encoding="utf-8") as f:
        grammar = f.read()
    # Set debug=True temporarily to see the parse tree and transformation steps if needed
    # WARNING: debug=True produces A LOT of output for complex grammars/inputs.
    # return Lark(grammar, parser='lalr', transformer=MiniLangTransformer(), debug=True) # Use this line for detailed debug output
    return Lark(grammar, parser='lalr', transformer=MiniLangTransformer(), debug=False, start='program') # Explicitly set the start rule

if __name__ == '__main__':
    try:
        # Create parser with debug=False for normal runs
        parser = get_minilang_parser()
        print("MiniLang parser created successfully with MiniLangTransformer.")

        # Simple test
        print("\n--- Testing basic assignment and print ---")
        # Added semicolons to match the grammar change
        test_code_simple = """
let a = 10;
print(a);
"""
        parser.parse(test_code_simple)


        print("\n--- Testing arithmetic ---")
        # Expected: 15.0
        # Added semicolon to match the grammar change
        test_code_arith = "print( (2 + 3) * 4 - 10 / 2 );"
        parser.parse(test_code_arith)

        print("\n--- Testing function call with keyword args ---")
        # Define a dummy function in the environment for this test
        def my_test_func(p1, p2=100, p3="default"):
            print(f"my_test_func called with p1={p1}, p2={p2}, p3='{p3}'")
            return p1 + p2

        # Temporarily add to a fresh transformer instance for isolated test
        temp_transformer = MiniLangTransformer()
        # Copy existing built-in functions
        temp_transformer.env.update(MiniLangTransformer().env)
        temp_transformer.env["my_test_func"] = my_test_func

        with open("minilang.lark", "r", encoding="utf-8") as f:
             grammar = f.read()
        temp_parser = Lark(grammar, parser='lalr', transformer=temp_transformer, debug=False, start='program') # Explicitly set the start rule
        # Added semicolons to match the grammar change
        test_code_func = """
let res = my_test_func(5, p3="custom_val", p2=50);
print(res);
"""
        temp_parser.parse(test_code_func)


    except Exception as e:
        print(f"Error creating or testing MiniLang parser: {e}")
        import traceback
        traceback.print_exc()