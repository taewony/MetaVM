from lark import Lark, Transformer

# 1. 문법 정의: 변수 선언, 참조, print, 계산식 포함
calculator_grammar = """
    ?start: stmt+

    ?stmt: expr                           -> eval_only
         | "print" "(" expr ")"           -> eval_and_print
         | "let" NAME "=" expr            -> let_stmt

    ?expr: term ((ADD | SUB) term)*       -> expr
    ?term: factor ((MUL | DIV) factor)*   -> term
    ?factor: INT                          -> number
           | NAME                         -> var
           | "(" expr ")"                 -> factor

    ADD: "+"
    SUB: "-"
    MUL: "*"
    DIV: "/"

    %import common.INT
    %import common.WS
    %import common.CNAME -> NAME
    %ignore WS
"""

# 2. 계산기 + 변수 저장 기능 Transformer
class CalcTransformer(Transformer):
    def __init__(self):
        self.env = {}  # 변수 저장 딕셔너리

    def number(self, args):
        return int(args[0])

    def var(self, args):
        name = str(args[0])
        if name in self.env:
            return self.env[name]
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
        self.env[name] = value
        print(f"[let] {name} = {value}")
        return value

    def eval_only(self, args):
        return args[0]

    def eval_and_print(self, args):
        value = args[0]
        print(f"print 결과: {value}")
        return value

# 3. 입력 및 실행
if __name__ == "__main__":
    input_program = """
        let x = 3
        let y = x + 1000 * 3
        print(y)
        print(x * 2)
        print( (2 + 3) * 4 - 10 / 2 )
        1 + (2 * 3 - 4) / 2
    """

    parser = Lark(calculator_grammar, parser='lalr')
    transformer = CalcTransformer()

    try:
        tree = parser.parse(input_program)
        print(tree.pretty())  # 파스 트리 출력
        result = transformer.transform(tree)
        print(f"최종 결과: {result}")
    except Exception as e:
        print(f"오류 발생: {e}")
