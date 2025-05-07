from lark import Lark, Transformer

# ---------------------------
# 트랜스포머 클래스 (기본 구현)
# ---------------------------
class BasicTransformer(Transformer):
    def number(self, items):
        return float(items[0]) if '.' in items[0] else int(items[0])
    
    def string(self, items):
        return items[0].value[1:-1]  # 따옴표 제거
    
    def var(self, items):
        return str(items[0])
    
    def list(self, items):
        return list(items)
    
    def func_call(self, items):
        func_name = str(items[0])
        args = items[1:]
        print(f"[Function Call] {func_name}({args})")
        return None

    def let_stmt(self, items):
        var_name, value = items[0].value, items[1]
        print(f"변수 할당: {var_name} = {value}")
        return value

# ---------------------------
# 메인 실행 코드
# ---------------------------
if __name__ == "__main__":
    # 문법 파일 로드
    with open("minilang.lark", "r", encoding='utf-8') as f:
        grammar = f.read()
    
    # 파서 생성
    parser = Lark(grammar, start='start', parser='lalr')
    
    # 샘플 코드 파싱
    sample_code = """
    let x = 42
    let data = load_csv("data.csv")
    """
    
    # 파싱 및 변환 실행
    tree = parser.parse(sample_code)
    result = BasicTransformer().transform(tree)
    print("파싱 결과:", result)