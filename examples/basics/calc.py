from lark import Lark, Transformer
import operator

# 1. 정수 계산 문법 정의 (이전 답변과 동일)
#    expr: 덧셈/뺄셈 우선순위 (가장 낮음)
#    term: 곱셈/나눗셈 우선순위 (중간)
#    factor: 숫자 또는 괄호 표현식 (가장 높음)
#    %import common.INT: Lark의 기본 정수 규칙 사용
#    %import common.WS: 공백 규칙 사용
#    %ignore WS: 파싱 시 공백 무시
calculator_grammar = """
    ?start: expr

    ?expr: term (addop term)*
    ?term: factor (mulop factor)*
    ?factor: INT           -> number
       | "(" expr ")"

    addop: "+" -> add
     | "-" -> sub

    mulop: "*" -> mul
     | "/" -> div

    %import common.INT
    %import common.WS
    %ignore WS
"""

# 2. 파스 트리를 계산 결과로 변환하는 Transformer 정의
#    Transformer 클래스의 메서드는 파스 트리의 해당 노드 이름과 일치합니다.
#    메서드의 매개변수 children는 해당 노드의 자식 노드들을 처리한 결과들의 리스트입니다.
class CalcTransformer(Transformer):
    def number(self, args):
        return int(args[0])

    def add(self, args): return "+"
    def sub(self, args): return "-"
    def mul(self, args): return "*"
    def div(self, args): return "/"

    def expr(self, args):
        print(f"[expr] args = {args}")
        result = args[0]
        for i in range(1, len(args), 2):
            op = args[i]
            right = args[i+1]
            if op == "+":
                result += right
            else:
                result -= right
        return result

    def term(self, args):
        print(f"[term] args = {args}")
        result = args[0]
        for i in range(1, len(args), 2):
            op = args[i]
            right = args[i+1]
            if op == "*":
                result *= right
            else:
                result /= right
        return result

# 계산할 수식 문자열 (괄호와 사칙연산 포함)
input_expr_calc = "1 + (2 * 3 - 4) / 2"
input_expr_print = "print(1 + (2 * 3 - 4) / 2)"

# Lark 파서 생성
# - calculator_grammar: 앞에서 정의한 계산기용 문법
# - parser='lalr': 더 빠르고 일반적인 LALR 파서 사용
# - transformer는 이 시점에서는 지정하지 않음 (직접 후처리할 예정)
parser = Lark(calculator_grammar, parser='lalr')

# Transformer 인스턴스 생성
# - Transformer는 파싱된 트리를 실제 계산 결과로 변환하는 역할
transformer = CalcTransformer()

# 입력 문자열을 파싱하여 트리(구문 트리, parse tree) 생성
tree = parser.parse(input_expr_calc)

# 파스 트리 구조 출력 (디버깅 및 구조 이해용)
# - Tree.pretty(): 트리 구조를 보기 쉽게 출력해줌
print(tree.pretty())

# Transformer를 이용해 파스 트리를 후처리하고, 최종 계산 결과 얻기
# - 이 과정에서 CalcTransformer의 메서드(expr, term, factor 등)가 순차적으로 호출됨
result = transformer.transform(tree)

# 최종 결과 출력
print(f"계산 결과: {result}")
