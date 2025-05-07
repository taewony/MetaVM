from lark import Lark, Transformer

class CalcTransformer(Transformer):
    def __init__(self, shared_env=None):
        self.shared_env = shared_env or {}
    
    def number(self, args):
        return int(args[0])

    def var(self, args):
        name = str(args[0])
        if name in self.shared_env:
            return self.shared_env[name]
        else:
            raise NameError(f"변수 '{name}'가 정의되지 않았습니다.")

    def factor(self, args):
        return args[0]

    def term(self, args):
        result = args[0]
        for i in range(1, len(args), 2):
            op = str(args[i])
            right = args[i + 1]
            if op == "*":
                result *= right
            elif op == "/":
                result /= right
        return result

    def expr(self, args):
        result = args[0]
        for i in range(1, len(args), 2):
            op = str(args[i])
            right = args[i + 1]
            if op == "+":
                result += right
            elif op == "-":
                result -= right
        return result

    def let_stmt(self, args):
        name = str(args[0])
        value = args[1]
        self.shared_env[name] = value
        print(f"[let] {name} = {value}")
        return value

    def eval_only(self, args):
        return args[0]

    def eval_and_print(self, args):
        value = args[0]
        print(f"print 결과: {value}")
        return value
    
def load_parser():
    with open("minilang.lark", "r") as f:
        grammar = f.read()
    return Lark(grammar, start='start', parser='lalr')

def run_line(parser, transformer, line):
    try:
        tree = parser.parse(line)
        return transformer.transform(tree)
    except Exception as e:
        print(f"Error: {e}")

def run_script(parser, transformer, filename):
    print(f"📜 스크립트 실행: {filename}")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                print(f"minilang> {line}")
                run_line(parser, transformer, line)

    except FileNotFoundError:
        print(f"[오류] 파일을 찾을 수 없습니다: {filename}")

