#!/usr/bin/env python3
import sys
import pandas as pd
from lark import Lark, Transformer, v_args, LarkError, Tree, Token # Import Token
import argparse
import os
import io

# 1) Lark 파서 초기화 (REPL 및 CLI 모드 모두에서 사용)
try:
    # minilang.lark 파일을 읽어 문법을 로드합니다.
    with open("minilang.lark", encoding="utf-8") as f:
        grammar = f.read()
    # Lark 파서를 초기화합니다. lalr 파서를 사용하고 위치 정보를 전파합니다.
    # start='start' 는 문법의 시작 규칙을 명시적으로 지정합니다 (일반적으로 필요).
    parser = Lark(grammar, parser="lalr", start='start', propagate_positions=True)
    print("MiniLang grammar loaded successfully.")
except FileNotFoundError:
    # 문법 파일이 없을 경우 오류 메시지를 출력하고 종료합니다.
    print("Error: 'minilang.lark' grammar file not found.", file=sys.stderr)
    sys.exit(1)
except LarkError as e:
    # 문법 파일 파싱 중 오류가 발생할 경우 메시지를 출력하고 종료합니다.
    print(f"Error parsing 'minilang.lark' grammar file: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during parser initialization: {e}", file=sys.stderr)
    sys.exit(1)


# 2) Transformer 정의 (MiniLang 코드 실행 로직 포함)
# @v_args(inline=True) 데코레이터를 사용하여 규칙의 자식 노드를 Transformer 메소드의 인자로 직접 전달합니다.
# inline=True 를 사용하면 Lark는 자식 노드를 먼저 변환하고 그 *결과*를 부모 규칙의 메소드에 인자로 전달합니다.
@v_args(inline=True)
class MiniLangExec(Transformer):
    def __init__(self):
        super().__init__()
        # 변수 환경을 저장할 딕셔너리입니다.
        self.env = {}
        # REPL에서 마지막 실행 결과를 저장합니다.
        self.last_result = None

    # --- 문장 처리 메소드 ---

    # 'let' 문을 처리하는 메소드입니다.
    # value 인자에는 오른쪽 표현식(expr)이 *이미 계산된 결과*가 전달됩니다.
    def let_stmt(self, name, value):
        # 변수 이름(name)은 Token 객체일 수 있으므로 str()로 변환합니다.
        name_str = str(name)
        self.env[name_str] = value
        # 할당문 자체는 REPL에서 명시적으로 값을 출력하지 않도록 None을 반환합니다.
        # 필요하다면 할당된 값을 반환하도록 수정할 수 있습니다: return value
        return None # REPL에서 할당 결과는 보통 출력 안 함

    # 'print' 문을 처리하는 메소드입니다. 문법에서 괄호가 선택적이므로 value 인자만 받습니다.
    # value 인자에는 괄호 안의 표현식이 *이미 계산된 결과*가 전달됩니다.
    def print_stmt(self, value):
        if isinstance(value, pd.DataFrame):
            print(value.to_string())
        else:
            print(value)
        return None # print 문은 값을 반환하지 않습니다.

    # 함수 호출 문을 처리하는 메소드입니다. 호출 결과 값을 반환합니다.
    # value에는 call 규칙의 결과 (함수 실행 결과)가 전달됩니다.
    def call_stmt(self, value):
        # REPL에서 호출 결과가 바로 출력되도록 값을 반환합니다.
        return value

    # --- 표현식 및 값 처리 메소드 ---

    # 변수 참조를 처리하는 메소드입니다.
    def var(self, name):
        name_str = str(name)
        if name_str not in self.env:
            raise NameError(f"Variable '{name_str}' is not defined.")
        return self.env[name_str]

    # 숫자를 처리하는 메소드입니다.
    def number(self, tok):
        return float(tok)

    # 문자열을 처리하는 메소드입니다.
    def string(self, tok):
        return tok[1:-1]

    # 리스트 리터럴을 처리하는 메소드입니다.
    # items에는 리스트 요소들이 *이미 계산된 결과*들이 가변 인자로 전달됩니다.
    def list(self, *items):
        return list(items)

    # 딕셔너리 리터럴을 처리하는 메소드입니다.
    # key_value_pairs에는 key_value_pair 규칙의 결과 (튜플)들이 가변 인자로 전달됩니다.
    def dictionary(self, *key_value_pairs):
        d = {}
        for key, value in key_value_pairs:
            # 키는 항상 문자열로 처리 (문법에 따라 달라질 수 있음)
            d[str(key)] = value
        return d

    # 딕셔너리 내의 키-값 쌍을 처리하는 메소드입니다.
    # name은 키 (보통 NAME 토큰), value는 값이 *이미 계산된 결과*입니다.
    def key_value_pair(self, name, value):
        # (키 이름 문자열, 값) 형태의 튜플로 반환합니다.
        return (str(name), value)

    # --- 산술 연산 처리 메소드 ---
    # @v_args(inline=True) 덕분에 자식 노드(term, factor)의 *결과*가 인자로 전달됩니다.

    # 덧셈 및 뺄셈 (arithmetic_expr 규칙)
    # left는 첫 번째 term의 결과, op는 연산자 토큰, right는 두 번째 term의 결과입니다.
    # 문법이 (term (op term)*) 형태일 경우, Lark가 왼쪽 우선으로 처리해줍니다.
    # 예를 들어 a + b - c 는 (a + b) - c 로 처리됩니다.
    # 수정된 버전: 왼쪽부터 순차적으로 계산합니다.
    def add(self, left, right):
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise RuntimeError(f"Unsupported operand types for +: {type(left)} and {type(right)}")
        return left + right

    def sub(self, left, right):
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise RuntimeError(f"Unsupported operand types for -: {type(left)} and {type(right)}")
        return left - right

    # 곱셈 및 나눗셈 (term 규칙)
    # left는 첫 번째 factor의 결과, op는 연산자 토큰, right는 두 번째 factor의 결과입니다.
    # 수정된 버전: 왼쪽부터 순차적으로 계산합니다.
    def mul(self, left, right):
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise RuntimeError(f"Unsupported operand types for *: {type(left)} and {type(right)}")
        return left * right

    def div(self, left, right):
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise RuntimeError(f"Unsupported operand types for /: {type(left)} and {type(right)}")
        if right == 0:
            raise RuntimeError("Division by zero")
        # 결과가 항상 float이 되도록 처리 (Python 3 동작 방식)
        return float(left) / float(right)


    # --- 함수 호출 처리 메소드 ---

    # 함수 호출의 인자 목록을 처리하는 메소드입니다. (args 규칙)
    # arguments 에는 각 인자 표현식이 *이미 계산된 결과* 또는 keyword_argument의 결과(튜플)가 전달됩니다.
    def args(self, *arguments):
        pos_args = []
        keyword_args = {}
        for arg in arguments:
            # keyword_argument 에서 반환된 (이름, 값) 튜플인지 확인
            if isinstance(arg, tuple) and len(arg) == 2 and isinstance(arg[0], str) and arg[0].startswith("_kw_"):
                # 키워드 인자 이름에서 접두사 제거
                keyword_args[arg[0][4:]] = arg[1]
            else:
                # 위치 인자
                pos_args.append(arg)
        return (pos_args, keyword_args)

    # 키워드 인자를 처리하는 메소드입니다. (keyword_argument 규칙)
    # name은 인자 이름 토큰, value는 인자 값이 *이미 계산된 결과*입니다.
    def keyword_argument(self, name, value):
        # 위치 인자와 구분하기 위해 특수한 형태의 튜플 반환 (예: 이름 앞에 접두사 추가)
        return ("_kw_" + str(name), value)


    # 함수 호출을 처리하는 메소드입니다. (call 규칙)
    # name은 함수 이름 토큰, args_tuple은 args 규칙의 결과 (pos_args, kw_args) 튜플입니다.
    # args_tuple이 없을 수도 있으므로 기본값을 None으로 설정합니다.
    def call(self, name, args_tuple=None):
        func_name = str(name)
        pos_args = []
        keyword_args = {}

        # args 규칙의 결과를 처리합니다.
        if args_tuple and isinstance(args_tuple, tuple) and len(args_tuple) == 2:
            pos_args, keyword_args = args_tuple
        # 인자가 없는 함수 호출 (예: my_func())의 경우 args_tuple이 없을 수 있습니다.
        # 또는 문법상 args가 선택적인 경우에도 None이 될 수 있습니다.
        elif args_tuple is not None:
             # args 규칙은 항상 (pos_args, kw_args) 튜플을 반환해야 합니다.
             # 이 경고는 문법이나 args 메소드 구현에 문제가 있을 수 있음을 나타냅니다.
             print(f"WARNING: Unexpected args_tuple format for function '{func_name}': {args_tuple}", file=sys.stderr)


        # --- 내장 함수 구현 ---
        # load_csv
        if func_name == "load_csv":
            if not pos_args or not isinstance(pos_args[0], str):
                raise RuntimeError("load_csv requires a file path (string) as the first argument.")
            path = pos_args[0]
            try:
                # 추가 키워드 인자를 pandas 함수에 전달할 수 있습니다.
                return pd.read_csv(path, **keyword_args)
            except FileNotFoundError:
                raise RuntimeError(f"load_csv: File not found at '{path}'")
            except Exception as e:
                raise RuntimeError(f"load_csv: Error reading file '{path}': {e}")

        # load_excel
        elif func_name == "load_excel":
            if not pos_args or not isinstance(pos_args[0], str):
                raise RuntimeError("load_excel requires a file path (string) as the first argument.")
            path = pos_args[0]
            try:
                 # 추가 키워드 인자를 pandas 함수에 전달할 수 있습니다.
                return pd.read_excel(path, **keyword_args)
            except FileNotFoundError:
                raise RuntimeError(f"load_excel: File not found at '{path}'")
            except Exception as e:
                raise RuntimeError(f"load_excel: Error reading file '{path}': {e}")

        # concat_dataframes
        elif func_name == "concat_dataframes":
            if not pos_args or not isinstance(pos_args[0], list):
                raise RuntimeError("concat_dataframes requires a list of dataframes as the first positional argument.")
            dfs_list = pos_args[0]
            if not all(isinstance(df, pd.DataFrame) for df in dfs_list):
                raise RuntimeError("concat_dataframes: All items in the list must be DataFrames.")
            try:
                # ignore_index는 키워드 인자로 받을 수 있도록 수정
                ignore_idx = keyword_args.get('ignore_index', True) # 기본값 True
                return pd.concat(dfs_list, ignore_index=ignore_idx, **{k:v for k,v in keyword_args.items() if k != 'ignore_index'})
            except Exception as e:
                raise RuntimeError(f"concat_dataframes: Error during concatenation: {e}")

        # create_pivot
        elif func_name == "create_pivot":
            if not pos_args or not isinstance(pos_args[0], pd.DataFrame):
                raise RuntimeError("create_pivot requires a dataframe as the first positional argument.")
            df = pos_args[0]
            # 키워드 인자 가져오기
            index_col = keyword_args.get('index')
            columns_col = keyword_args.get('columns')
            values_col = keyword_args.get('values')
            aggfunc = keyword_args.get('aggfunc', 'sum') # 기본값 'sum'

            # 필수 인자 및 타입 검사
            if index_col is None or not isinstance(index_col, (str, list)):
                 raise RuntimeError("create_pivot requires 'index' keyword argument (string or list of strings).")
            if columns_col is not None and not isinstance(columns_col, (str, list)):
                 raise RuntimeError("create_pivot 'columns' must be a string or list of strings if provided.")
            if values_col is not None and not isinstance(values_col, (str, list)):
                 raise RuntimeError("create_pivot 'values' must be a string or list of strings if provided.")
            if not isinstance(aggfunc, (str, list, dict)): # aggfunc는 더 다양한 타입을 받을 수 있음
                 raise RuntimeError("create_pivot 'aggfunc' must be a string, list, or dictionary.")

            # DataFrame에 컬럼 존재 여부 확인 (단일 문자열 또는 리스트 처리)
            def check_cols(cols):
                if isinstance(cols, str):
                    return [cols]
                elif isinstance(cols, list):
                    return cols
                return [] # None 이거나 다른 타입이면 빈 리스트 반환

            cols_to_check_flat = []
            cols_to_check_flat.extend(check_cols(index_col))
            if columns_col: cols_to_check_flat.extend(check_cols(columns_col))
            if values_col: cols_to_check_flat.extend(check_cols(values_col))

            missing_cols = [col for col in cols_to_check_flat if col not in df.columns]
            if missing_cols:
                raise RuntimeError(f"create_pivot: Columns not found in DataFrame: {missing_cols}")

            try:
                # pivot_table 호출
                return pd.pivot_table(df, index=index_col, columns=columns_col, values=values_col, aggfunc=aggfunc)
            except Exception as e:
                raise RuntimeError(f"create_pivot: Error creating pivot table: {e}")

        # visualize_pivot_stats (Placeholder)
        elif func_name == "visualize_pivot_stats":
            if not pos_args or not isinstance(pos_args[0], pd.DataFrame):
                 raise RuntimeError("visualize_pivot_stats requires a pivot table (DataFrame) as the first argument.")
            pivot_df = pos_args[0]
            print("\n--- Visualizing Pivot Table Statistics (Placeholder) ---")
            try:
                print(pivot_df.describe().to_string())
            except Exception as e:
                print(f"Could not describe pivot table: {e}")
            print("-----------------------------------------------------")
            return None # 시각화 함수는 보통 None 반환

        # stats (Placeholder)
        elif func_name == "stats":
            if len(pos_args) < 2 or not isinstance(pos_args[0], pd.DataFrame) or not isinstance(pos_args[1], list):
                 raise RuntimeError("stats requires a dataframe and a list of metrics (strings) as positional arguments.")
            df = pos_args[0]
            metrics = pos_args[1]
            if not all(isinstance(m, str) for m in metrics):
                raise RuntimeError("stats: metrics list must contain only strings.")

            try:
                desc = df.describe()
                missing = [m for m in metrics if m not in desc.index]
                if missing:
                    raise RuntimeError(f"stats: unknown metrics {missing}. Available: {list(desc.index)}")
                # 지정된 메트릭만 선택하여 반환
                return desc.loc[metrics]
            except Exception as e:
                raise RuntimeError(f"stats: Error calculating statistics: {e}")

        # --- 내장 함수 구현 끝 ---

        else:
            # 정의되지 않은 함수 호출 시 오류 발생
            raise RuntimeError(f"Unknown function: {func_name}")

    # --- Transformer의 기본 동작 ---
    # Lark는 문법 규칙과 일치하는 메소드가 없으면 기본 동작을 수행합니다.
    # 예를 들어, 'expr: term' 과 같은 규칙은 'expr' 메소드가 없으면
    # 자동으로 'term' 자식 노드를 변환하고 그 결과를 반환합니다.
    # 따라서 산술 연산자 우선순위를 처리하기 위해 모든 중간 규칙에 대한 메소드를 만들 필요는 없습니다.
    # 중요한 것은 최종 연산(add, sub, mul, div 등)과 기본 값(var, number, string 등)을 처리하는 메소드입니다.


# === 아래 코드는 기존 코드와 동일 ===

# 파일 내용을 한 줄씩 읽고 실행하는 함수 (REPL의 '.' 명령어에서 사용)
def run_minilang_line_by_line(file_path: str, parser: Lark, transformer: MiniLangExec):
    """
    MiniLang 파일을 한 줄씩 읽고 실행합니다. 줄 연속 문자를 처리하며,
    완성된 각 문장을 제공된 트랜스포머를 사용하여 파싱하고 실행합니다.
    트랜스포머의 환경(변수 등)은 줄을 넘어 유지됩니다.
    """
    print(f"Running file '{file_path}' line by line...")
    try:
        with open(file_path, encoding="utf-8") as f:
            line_buffer = "" # 여러 줄에 걸친 문장을 저장할 버퍼
            line_num_start = 0 # 여러 줄 문장의 시작 줄 번호를 추적

            for line_num, line in enumerate(f, 1):
                stripped_line = line.strip()

                # 버퍼가 비어 있고 현재 줄이 비어 있거나 주석으로 시작하면 건너뜁니다.
                if not line_buffer and (not stripped_line or stripped_line.startswith('//')):
                    continue

                # 줄 끝에 줄 연속 문자 '\'가 있는지 확인합니다.
                is_continuation = stripped_line.endswith('\\')
                if is_continuation:
                    # 버퍼에 줄을 추가하고 '\'를 제거한 후 공백을 추가합니다.
                    line_to_add = stripped_line[:-1].rstrip() # 끝 공백 제거 후 백슬래시 제거
                    if line_buffer and line_to_add: # 버퍼와 추가할 내용이 모두 있을 때만 공백 추가
                        line_buffer += " " + line_to_add
                    else:
                        line_buffer += line_to_add # 버퍼가 비었거나 추가할 내용이 없으면 그냥 추가

                    # 버퍼가 비어 있다가 이 줄이 추가된 경우 시작 줄 번호를 기록합니다.
                    if not line_buffer.strip() and line_num_start == 0: # 이 조건은 첫 줄이 \로 끝날 때만 의미있음
                       line_num_start = line_num
                    elif line_buffer.strip() and line_num_start == 0: # 내용이 있는 첫 줄이면서 \로 끝날 때
                       line_num_start = line_num

                    continue # 다음 줄을 읽습니다.

                # 줄 연속 문자가 없는 경우, 현재 줄을 버퍼에 추가하고 처리합니다.
                if line_buffer and stripped_line: # 이전 버퍼 내용과 현재 줄 내용이 모두 있을 때 공백 추가
                    line_buffer += " " + stripped_line
                else:
                     line_buffer += stripped_line

                # 버퍼가 비어 있었고, 이번 줄이 비거나 주석이면 (예: '\'만 있던 줄 다음)
                if not line_buffer.strip():
                    line_buffer = "" # 버퍼 리셋
                    line_num_start = 0 # 시작 줄 번호 리셋
                    continue

                # 오류 보고를 위한 줄 번호를 결정합니다 (여러 줄 문장의 경우 시작 줄).
                report_line_num = line_num_start if line_num_start > 0 else line_num

                # 실행 전 현재 환경 상태 출력 (디버깅용)
                # print(f"Executing line(s) starting {report_line_num}: '{line_buffer}' with env: {transformer.env}")
                print(f"minilang:{report_line_num}> {line_buffer}") # 실행할 완성된 문장을 출력합니다.

                try:
                    # 버퍼에서 완성된 문장을 파싱합니다.
                    # Lark가 종종 개행 문자를 기대하므로 끝에 개행 문자를 추가합니다.
                    # 문법에 _EOL 이나 NEWLINE 같은 터미널이 있으면 필요합니다.
                    tree = parser.parse(line_buffer + "\n")

                    # 파싱된 문장을 실행합니다.
                    result = transformer.transform(tree)
                    transformer.last_result = result # 마지막 결과 저장

                    # 결과가 None이 아니고, print문이 아닌 경우 REPL처럼 결과를 출력 (파일 실행시에는 선택사항)
                    # if result is not None and tree.data != 'print_stmt': # 최상위 노드가 print문이 아닐때만
                    #     if isinstance(result, pd.DataFrame):
                    #         print(result.to_string())
                    #     else:
                    #         print(result)


                except LarkError as e:
                    # 파싱 오류 발생 시 메시지를 출력합니다.
                    print(f"MiniLang Parsing Error (File near line {report_line_num}): {e}", file=sys.stderr)
                    # 오류 발생 시 해당 문장 실행 건너뛰고 계속 진행
                except (RuntimeError, NameError, ZeroDivisionError, TypeError) as e: # TypeError 추가
                    # 실행 오류 발생 시 메시지를 출력합니다.
                    print(f"MiniLang Execution Error (File near line {report_line_num}): {e}", file=sys.stderr)
                    # 오류 발생 시 해당 문장 실행 건너뛰고 계속 진행
                except Exception as e:
                    # 예상치 못한 오류 발생 시 메시지를 출력합니다.
                    print(f"An unexpected error occurred (File near line {report_line_num}): {e}", file=sys.stderr)
                    # 오류 발생 시 해당 문장 실행 건너뛰고 계속 진행

                # 다음 문장을 위해 버퍼와 줄 번호 추적을 리셋합니다.
                line_buffer = ""
                line_num_start = 0

            # 루프 종료 후 버퍼에 남아 있는 내용이 있는 경우 처리합니다 (예: 파일 끝에 '\' 가 있는 경우).
            if line_buffer.strip():
                report_line_num = line_num_start if line_num_start > 0 else line_num # 마지막 줄 번호 또는 시작 줄 번호를 사용합니다.
                print(f"minilang:{report_line_num}> {line_buffer} (Processing remaining buffer)")
                try:
                    tree = parser.parse(line_buffer + "\n")
                    result = transformer.transform(tree)
                    transformer.last_result = result
                    # if result is not None and tree.data != 'print_stmt':
                    #    if isinstance(result, pd.DataFrame): print(result.to_string())
                    #    else: print(result)
                except LarkError as e:
                    print(f"MiniLang Parsing Error (File near line {report_line_num}): {e}", file=sys.stderr)
                except (RuntimeError, NameError, ZeroDivisionError, TypeError) as e: # TypeError 추가
                    print(f"MiniLang Execution Error (File near line {report_line_num}): {e}", file=sys.stderr)
                except Exception as e:
                    print(f"An unexpected error occurred (File near line {report_line_num}): {e}", file=sys.stderr)

        print(f"Finished running file '{file_path}'.")
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'", file=sys.stderr)
    except Exception as e:
        print(f"Error reading or processing file '{file_path}': {e}", file=sys.stderr)


# 파일 전체를 실행하는 함수 (CLI 모드에서 사용)
def run_minilang_script_full(file_path: str, parser: Lark, transformer: MiniLangExec):
    """
    MiniLang 스크립트 파일 전체를 한 번에 읽고 실행합니다.
    CLI 모드에서 사용됩니다.
    """
    print(f"Running MiniLang script file: {file_path}")
    try:
        with open(file_path, encoding="utf-8") as f:
            code = f.read()
        # 파일이 개행 문자로 끝나지 않는 경우를 대비하여 마지막에 개행 문자를 추가합니다.
        # 이는 문법의 start 규칙(여러 문장을 포함하는 경우)에 따라 파싱 문제를 일으킬 수 있습니다.
        if not code.endswith('\n'):
            code += '\n'

        # 전체 코드를 한 번에 파싱
        tree = parser.parse(code)
        # 전체 트리를 한 번에 변환(실행)
        transformer.transform(tree)

        print(f"Finished running script file: {file_path}")
    except FileNotFoundError:
        print(f"Error: Input file '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except LarkError as e:
        print(f"MiniLang Parsing Error (File: {file_path}):\n{e}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, NameError, ZeroDivisionError, TypeError) as e: # TypeError 추가
        print(f"MiniLang Execution Error (File: {file_path}): {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while running script (File: {file_path}): {e}", file=sys.stderr)
        sys.exit(1)


# 3) REPL 실행 함수
def run_repl():
    print("MiniLang REPL (Type 'exit' to quit, '.' to run file line by line, '!' to toggle mode)")
    transformer = MiniLangExec() # REPL 세션 동안 Transformer 인스턴스를 유지합니다.
    current_mode = "minilang" # 현재 모드 ('minilang' 또는 'python')
    # 항상 minilang> 프롬프트로 시작합니다.
    line_buffer = "" # REPL 내 여러 줄 입력 버퍼 (\ 사용시)
    line_num_start = 0 # REPL 내 여러 줄 입력 시작 라인 (오류 보고용 가상 라인)
    repl_line_count = 0 # REPL 입력 줄 카운트

    while True:
        try:
            # 현재 모드와 버퍼 상태에 따른 프롬프트를 표시합니다.
            if line_buffer:
                prompt = "... " # 여러 줄 입력 중
            else:
                 prompt = "minilang> " if current_mode == "minilang" else "python> "

            line = input(prompt)
            repl_line_count += 1

            if not line_buffer and line.lower() == 'exit':
                break
            if not line_buffer and not line.strip(): # 첫 줄이 비어 있으면 무시
                continue

            # 줄 연속 처리 (\)
            stripped_line = line.strip()
            is_continuation = stripped_line.endswith('\\')

            if is_continuation:
                 line_to_add = stripped_line[:-1].rstrip()
                 if line_buffer and line_to_add:
                     line_buffer += " " + line_to_add
                 else:
                     line_buffer += line_to_add
                 if not line_buffer.strip() and line_num_start == 0: line_num_start = repl_line_count
                 elif line_buffer.strip() and line_num_start == 0: line_num_start = repl_line_count
                 continue # 다음 입력 받기
            else:
                 # 연속이 아니면 현재 줄을 버퍼에 추가
                 if line_buffer and stripped_line:
                     line_buffer += " " + stripped_line
                 else:
                      line_buffer += stripped_line

            # 완성된 입력 (line_buffer)
            full_input = line_buffer
            report_line_num = line_num_start if line_num_start > 0 else repl_line_count

            # 버퍼/시작라인 리셋 (다음 입력을 위해)
            line_buffer = ""
            line_num_start = 0

            if not full_input.strip(): # 최종 입력이 비었으면 무시 (예: '\'만 입력 후 엔터)
                continue

            # --- 특별 명령어 처리 ---
            if current_mode == "minilang" and full_input == '.':
                file_path = input("Run file line by line: ")
                if not os.path.exists(file_path):
                    print(f"Error: File not found at '{file_path}'", file=sys.stderr)
                    continue
                # REPL의 트랜스포머 인스턴스를 전달하여 상태를 유지합니다.
                run_minilang_line_by_line(file_path, parser, transformer)
                continue

            if full_input == '!':
                current_mode = "python" if current_mode == "minilang" else "minilang"
                print(f"Switched to {current_mode.capitalize()} mode.")
                continue
            # --- 특별 명령어 끝 ---


            # --- 모드별 실행 ---
            if current_mode == "minilang":
                try:
                    # Lark가 종종 개행 문자를 기대하므로 끝에 개행 문자를 추가합니다.
                    tree = parser.parse(full_input + "\n")
                    # 파싱된 문장을 실행하고 결과를 저장합니다.
                    result = transformer.transform(tree)
                    transformer.last_result = result

                    # 결과가 None이 아닌 경우 (예: 할당문, print문이 아닌 표현식이나 함수 호출 결과) 결과를 출력합니다.
                    if result is not None:
                         # DataFrame 형식 특별 처리
                        if isinstance(result, pd.DataFrame):
                            print(result.to_string())
                        else:
                            print(result)

                except LarkError as e:
                    print(f"MiniLang Parsing Error (REPL near line {report_line_num}): {e}", file=sys.stderr)
                except (RuntimeError, NameError, ZeroDivisionError, TypeError) as e: # TypeError 추가
                    print(f"MiniLang Execution Error (REPL near line {report_line_num}): {e}", file=sys.stderr)
                except Exception as e:
                    print(f"An unexpected error occurred (REPL near line {report_line_num}): {e}", file=sys.stderr)

            elif current_mode == "python":
                # Python 모드: 단일 줄(또는 여러 줄로 이어진)의 Python 코드를 실행합니다.
                try:
                    # 먼저 표현식에 대해 eval을 시도합니다.
                    # 변수 접근을 위해 트랜스포머의 환경을 globals와 locals로 전달합니다.
                    # MiniLang 변수를 Python 코드에서 사용할 수 있게 됩니다.
                    py_globals = {'pd': pd, **transformer.env} # pandas 등 필요한 모듈 추가 가능
                    py_locals = transformer.env
                    result = eval(full_input, py_globals, py_locals)

                    # eval 결과가 None이 아니면 출력합니다.
                    if result is not None:
                        print(result)
                    # 결과를 MiniLang 환경에도 반영 (선택 사항)
                    # transformer.last_result = result

                except SyntaxError:
                    # eval이 실패하면 문장에 대해 exec를 시도합니다.
                    try:
                        # exec는 환경을 직접 수정할 수 있습니다.
                        py_globals = {'pd': pd, **transformer.env}
                        py_locals = transformer.env
                        exec(full_input, py_globals, py_locals)
                        # exec 실행 후 변경된 내용을 MiniLang 환경에 다시 반영
                        # 주의: exec로 전역 변수를 직접 추가/변경하는 것은 복잡할 수 있음
                        # 여기서는 로컬 변경 사항만 반영하도록 시도
                        transformer.env.update(py_locals)
                        transformer.last_result = None # exec는 결과를 반환하지 않습니다.
                    except Exception as e:
                        print(f"Python Execution Error (exec) (REPL near line {report_line_num}): {e}", file=sys.stderr)
                except Exception as e:
                    # eval 중 다른 예외를 잡습니다.
                    print(f"Python Execution Error (eval) (REPL near line {report_line_num}): {e}", file=sys.stderr)

        except EOFError: # Ctrl+D 처리
            print("\nExiting REPL.")
            break
        except KeyboardInterrupt: # Ctrl+C 처리
             print("\nKeyboardInterrupt")
             line_buffer = "" # 입력 중이던 버퍼 초기화
             line_num_start = 0
        except Exception as e:
            print(f"An unexpected error occurred in REPL loop: {e}", file=sys.stderr)
            # REPL이 죽지 않도록 계속 실행 시도
            line_buffer = ""
            line_num_start = 0


# 4) 메인 진입점
if __name__ == "__main__":
    # argparse를 사용하여 명령줄 인자를 파싱합니다.
    parser_cli = argparse.ArgumentParser(description="MiniLang REPL or CLI Interpreter")
    parser_cli.add_argument("input_file", nargs="?", help="CLI 모드에서 실행할 MiniLang 스크립트 파일")
    # 디버그 옵션 추가 (선택 사항)
    parser_cli.add_argument("-d", "--debug", action="store_true", help="Enable debug prints (Not fully implemented)")

    args = parser_cli.parse_args()

    # Lark 파서는 두 모드에서 모두 사용되므로 외부에 초기화됩니다.
    # 파서 초기화는 이미 위에서 완료되었습니다.

    if args.input_file:
        # 인자가 제공되면 CLI 모드로 실행합니다.
        # CLI 실행을 위해 새로운 트랜스포머 인스턴스를 생성합니다.
        cli_transformer = MiniLangExec()
        run_minilang_script_full(args.input_file, parser, cli_transformer)
    else:
        # 인자가 없으면 REPL 모드로 실행합니다.
        run_repl()