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

    ?expr: term (("+"|"-") term)*
    ?term: factor (("*"|"/") factor)*
    ?factor: INT | "(" expr ")"

    %import common.INT
    %import common.WS
    %ignore WS
"""

# 2. 파스 트리를 계산 결과로 변환하는 Transformer 정의
#    Transformer 클래스의 메서드는 파스 트리의 해당 노드 이름과 일치합니다.
#    메서드의 매개변수 children는 해당 노드의 자식 노드들을 처리한 결과들의 리스트입니다.
class CalculatorTransformer(Transformer):
    # INT 터미널을 Python의 int 형으로 변환합니다.
    # Lark의 INT 터미널은 토큰 객체이며, 그 값은 문자열입니다.
    def INT(self, token):
        return int(token) # token.value 대신 token 자체를 int()에 전달해도 됩니다.

    # factor 규칙 처리:
    # 자식 노드가 하나만 있습니다 (INT 또는 괄호 안의 expr).
    # 자식 노드는 이미 하위 Transformer에 의해 처리된 결과입니다.
    def factor(self, children):
        return children

    # term 규칙 처리:
    # children 리스트는 [ factor1, op1, factor2, op2, factor3, ... ] 형태입니다.
    # 연산자(* 또는 /)를 순서대로 적용합니다 (왼쪽 결합).
    def term(self, children):
        # 첫 번째 자식(factor) 값을 초기 결과로 사용합니다.
        result = children
        # 나머지 자식들을 순회하며 연산자와 다음 factor를 처리합니다.
        for i in range(1, len(children), 2):
            op = children[i]
            next_value = children[i+1]
            if op == '*':
                result *= next_value
            elif op == '/':
                 # 정수 나눗셈을 위해 // 사용
                result //= next_value
        return result

    # expr 규칙 처리:
    # children 리스트는 [ term1, op1, term2, op2, term3, ... ] 형태입니다.
    # 연산자(+ 또는 -)를 순서대로 적용합니다 (왼쪽 결합).
    def expr(self, children):
         # 첫 번째 자식(term) 값을 초기 결과로 사용합니다.
        result = children
        # 나머지 자식들을 순회하며 연산자와 다음 term를 처리합니다.
        for i in range(1, len(children), 2):
            op = children[i]
            next_value = children[i+1]
            if op == '+':
                result += next_value
            elif op == '-':
                result -= next_value
        return result

    # start 규칙 처리:
    # 최종 결과는 expr 규칙의 결과입니다.
    def start(self, children):
        return children


# 3. 파서 생성 및 계산 실행
parser = Lark(calculator_grammar)
transformer = CalculatorTransformer()

# 계산할 입력 문자열
input_expression = "1 + (2 * 3 - 4) / 2"
# input_expression = "10 * 5 + 20 / 4 - 3" # 다른 예시

try:
    # 입력 문자열 파싱 -> 파스 트리 생성
    parse_tree = parser.parse(input_expression)
    # print("Parse Tree:")
    # print(parse_tree.pretty()) # 파스 트리 구조 확인 (선택 사항)

    # Transformer를 사용하여 파스 트리 변환 -> 계산 결과 얻기
    result = transformer.transform(parse_tree)

    print(f"입력 표현식: {input_expression}")
    print(f"계산 결과: {result}")

except Exception as e:
    print(f"오류 발생: {e}")