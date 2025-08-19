input = input("Pass a boolean expression to the script ")
def concat_expression(expr):
    expr = expr.replace(" ", "")
    expr = expr.replace("~", " NOT ").replace("&", " AND ").replace("|", " OR ")
    for sym in "()":
        expr = expr.replace(sym, f" {sym} ")
    return expr.split()
