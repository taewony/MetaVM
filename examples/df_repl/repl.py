from parser import MiniLangExecutor, load_parser, run_line, run_script

def start_repl():
    parser = load_parser()
    shared_env = {'__builtins__': __builtins__}
    transformer = MiniLangExecutor(shared_env)

    mode = "minilang"
    print("🎯 MiniLang REPL 시작. 명령어 '!': 모드 토글, '!파일.minilang': 스크립트 실행")

    while True:
        prompt = f"{mode}> "
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if not line:
            continue

        # 종료 명령어 처리 (추가된 부분)
        if line.lower() == "exit":
            print("프로그램을 종료합니다.")
            break

        if line.startswith("!"):
            if line == "!":
                mode = "python" if mode == "minilang" else "minilang"
                print(f"모드 전환됨: {mode}")
            elif line.endswith(".minilang"):
                run_script(parser, transformer, line[1:])
            continue

        if mode == "minilang":
            run_line(parser, transformer, line)
        else:
            try:
                exec(line, shared_env, shared_env)
                if not line.startswith((' ', '\t', 'def', 'class', 'import')):
                    try:
                        result = eval(line, shared_env)
                        if result is not None:
                            print(f"결과: {result}")
                    except:
                        pass
            except Exception as e:
                print(f"[Python 오류] {e}")

if __name__ == "__main__":
    start_repl()