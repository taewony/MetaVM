#!/usr/bin/env python3
import sys
import pandas as pd
from lark import Lark, Transformer, v_args

# 1) Lark 파서 초기화
with open("minilang.lark", encoding="utf-8") as f:
    grammar = f.read()
parser = Lark(grammar, parser="lalr")

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
            print(value.to_string())
        else:
            print(value)

    def var(self, name):
        return self.env.get(name, None)

    def number(self, tok):
        return float(tok)

    def string(self, tok):
        return tok[1:-1]

    def list(self, *items):
        processed = []
        for item in items:
            if hasattr(item, 'type') and item.type == 'STRING':
                processed.append(item.value[1:-1])
            elif isinstance(item, str):
                processed.append(item)
            else:
                raise RuntimeError(f"list: unexpected item type {type(item)}")
        return processed

    def args(self, *values):
        return list(values)

    def call(self, name, *args):
        # 만약 args 가 ([...],) 형태라면 풀어준다
        if len(args) == 1 and isinstance(args[0], list):
            args = args[0]
        func = str(name)

        # CSV 로드
        if func == "load_csv":
            path = args[0]
            if not isinstance(path, str):
                raise RuntimeError(f"load_csv: expected string path, got {type(path)}")
            return pd.read_csv(path)

        # 통계량 계산
        if func == "stats":
            df, metrics = args
            if not isinstance(df, pd.DataFrame):
                raise RuntimeError(f"stats: expected DataFrame, got {type(df)}")
            if not isinstance(metrics, list):
                raise RuntimeError(f"stats: expected list of metrics, got {type(metrics)}")
            desc = df.describe()
            missing = [m for m in metrics if m not in desc.index]
            if missing:
                raise RuntimeError(f"stats: unknown metrics {missing}")
            return desc.loc[metrics]

        raise RuntimeError(f"Unknown function: {func}")

# 3) 실행 함수
def run_minilang(code: str):
    tree = parser.parse(code)
    MiniLangExec().transform(tree)

# 4) 메인
def main():
    if len(sys.argv) == 2:
        code = open(sys.argv[1], encoding="utf-8").read()
    else:
        code = sys.stdin.read()
    run_minilang(code)

if __name__ == "__main__":
    main()
