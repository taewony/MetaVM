import argparse
from minilang import execute_script

def main():
    parser = argparse.ArgumentParser(description="MetaVM MiniLang CLI")
    parser.add_argument("script", type=str, help="MiniLang script file")
    args = parser.parse_args()
    
    with open(args.script, "r") as f:
        script = f.read()
    
    execute_script(script)

if __name__ == "__main__":
    main()