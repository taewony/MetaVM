from lark import Lark, Transformer
import pandas as pd
from tabulate import tabulate # type: ignore

class MiniLangTransformer(Transformer):
    def datasource(self, items):
        return ('load_csv', items[2].value.strip('"'))
    
    def transform(self, items):
        return ('transform', items[2].children[0].value, eval(items[5]))
    
    def printblock(self, items):
        return ('print', items[2].value.strip('"'), items[6].children[0].value)

def execute_script(script):
    parser = Lark.open("minilang.lark", parser="lalr", transformer=MiniLangTransformer())
    parsed = parser.parse(script)
    
    data = {}
    for cmd in parsed:
        if cmd[0] == 'load_csv':
            df = pd.read_csv(cmd[1])
            data['current_df'] = df
        elif cmd[0] == 'transform':
            metrics = {m.split(':')[0]: [m.split(':')[1]] for m in cmd[2]}
            stats = data['current_df'].agg(metrics)
            data[cmd[1]] = stats
        elif cmd[0] == 'print':
            print(f"\n[{cmd[1]}]")
            print(tabulate(data[cmd[2]], headers='keys', tablefmt='psql', showindex=False))