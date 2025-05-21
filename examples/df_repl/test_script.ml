
// This is a test MiniLang script.
let script_var = 100
print(script_var * 2)

let titanic_data = load_csv("titanic.csv")
print("First few rows of titanic data from script:")
print(titanic_data)

let some_stats = stats(titanic_data, ["min", "max"])
print("Min/Max stats from script:")
print(some_stats)
