from lark import Lark, Transformer

# 1. 문법 정의: 연산자 토큰 명시 + print 지원
calculator_grammar = """
    ?start: stmt                          // 프로그램 시작은 stmt

    ?stmt: expr                           -> eval_only
         | "print" "(" expr ")"           -> eval_and_print

    ?expr: term ((ADD | SUB) term)*       -> expr
    ?term: factor ((MUL | DIV) factor)*   -> term
    ?factor: INT | "(" expr ")"           -> factor

    ADD: "+"
    SUB: "-"
    MUL: "*"
    DIV: "/"

    %import common.INT
    %import common.WS
    %ignore WS
"""

# 2. 계산 수행을 위한 Transformer 클래스
class CalcTransformer(Transformer):
    def INT(self, token):
        return int(token)

    def factor(self, args):
        # 괄호식이나 숫자 하나만 있으므로 그대로 반환
        return args[0]

    def term(self, args):
        # 곱셈/나눗셈 처리
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
        # 덧셈/뺄셈 처리
        result = args[0]
        for i in range(1, len(args), 2):
            op = str(args[i])
            right = args[i + 1]
            if op == "+":
                result += right
            elif op == "-":
                result -= right
        return result

    def eval_only(self, args):
        # 단순 계산식 (print 없음)
        return args[0]

    def eval_and_print(self, args):
        # print(계산식)
        value = args[0]
        print(f"print 결과: {value}")
        return value

# 3. 입력과 실행
if __name__ == "__main__":
    input_expr_calc = "1 + (2 * 3 - 4) / 2"
    input_expr_print = "print(1 + (2 * 3 - 4) / 2)"

    parser = Lark(calculator_grammar, parser='lalr')
    transformer = CalcTransformer()

    for expr in [input_expr_calc, input_expr_print]:
        print(f"\n입력 표현식: {expr}")
        try:
            tree = parser.parse(expr)
            print(tree.pretty())  # 파스 트리 출력
            result = transformer.transform(tree)
            print(f"계산 결과: {result}")
        except Exception as e:
            print(f"오류 발생: {e}")
