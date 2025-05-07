# minilang_runner.py
# minilang_parser에서 파서와 Transformer를 가져와서
# 미리 정의된 MiniLang 코드를 실행합니다.

from minilang_parser import get_minilang_parser, MiniLangTransformer # MiniLangTransformer도 가져옵니다.
from lark import Lark # Lark도 가져옵니다.

# 실행할 MiniLang 테스트 코드 (MiniLang test code to execute)
# (This code matches the example from the prompt)
MINILANG_TEST_CODE = """
# 사칙연산 테스트 (Arithmetic operations test)
let x = 3
let y = x + 3000
print(y) # Expected: 3003

# CSV 로드 및 통계 테스트 (CSV load and statistics test)
let data = load_csv("titanic.csv")
print(data) # DataFrame 자체를 출력 (Print the DataFrame itself)
let result = stats(data, ["mean", "std", "50%"])
print(result)

# 여러 파일 로드 및 병합, 피벗 테이블 테스트 (Multiple file load, merge, and pivot table test)
let file1_data = load_csv("./file1.csv")
let file2_data = load_csv("./file2.csv")
let file3_data = load_csv("./file3.csv")

print(file1_data)
print(file2_data)
print(file3_data)

let merged_data = concat_dataframes([file1_data, file2_data, file3_data])
print(merged_data)

let pivot_table = create_pivot(
    merged_data,
    index="Category",
    columns="SubCategory",
    values="Value",
    aggfunc="sum"
)
print(pivot_table)

# 리스트 및 딕셔너리 테스트 (List and dictionary test)
let my_list = [1, x + 10, "hello"]
print(my_list) # Expected: [1, 13, "hello"] (assuming x=3 from previous context)

let my_dict = {
    name: "MiniLang",
    version: 0.1,
    "features": ["parsing", "execution", my_list]
}
print(my_dict)
"""

if __name__ == "__main__":
    print("--- MiniLang Runner ---")
    
    # minilang.lark 문법 파일을 읽어 Lark 객체 생성
    # (Read minilang.lark grammar file and create Lark object)
    try:
        with open("minilang.lark", "r", encoding="utf-8") as f:
            grammar_text = f.read()
        
        # 새로운 Transformer 인스턴스를 각 실행마다 생성하여 환경을 초기화
        # (Create a new Transformer instance for each execution to initialize the environment)
        transformer_instance = MiniLangTransformer()
        minilang_parser = Lark(grammar_text, parser='lalr', transformer=transformer_instance, debug=False)
        
        print("Parsing and executing MiniLang code:\n")
        print("-------------------- CODE START --------------------")
        print(MINILANG_TEST_CODE.strip())
        print("--------------------- CODE END ---------------------\n")
        print("----------------- EXECUTION LOGS -----------------\n")
        
        # 코드를 파싱하고 실행합니다 (Transformer가 실행 로직을 처리).
        # (Parse and execute the code (Transformer handles execution logic).)
        # Lark에 transformer를 전달하면 parse()가 변환된 트리(이 경우 실행 결과)를 반환합니다.
        # (If a transformer is passed to Lark, parse() returns the transformed tree (execution result in this case).)
        execution_result = minilang_parser.parse(MINILANG_TEST_CODE)
        
        print("\n----------------- FINAL RESULT -----------------\n")
        print("Final result of the script (transformed tree):", execution_result)
        print("\n--- MiniLang Runner Finished ---")

    except FileNotFoundError:
        print("Error: minilang.lark grammar file not found. Make sure it's in the same directory.")
    except Exception as e:
        print(f"An error occurred during parsing or execution: {e}")
        import traceback
        traceback.print_exc()

