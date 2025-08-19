input = input("Pass a boolean expression to the script ")
def concat_expression(expr):
    expr = expr.replace(" ", "")
    expr = expr.replace("~", " NOT ").replace("&", " AND ").replace("|", " OR ")
    for sym in "()":
        expr = expr.replace(sym, f" {sym} ")
    return expr.split()



def account_brackets(input):
  stack = [[]]  

  for t in input:
      if t == "(":
          stack.append([])  
      elif t == ")":
          group = stack.pop()          
          stack[-1].append(group)     
      else:
          stack[-1].append(t)
  return stack[0]

def account_OR(expression):
    output = []
   
    i = 0
    while i < len(expression):
        #print("Current item:", expression[i])
        if isinstance(expression[i],list):
            expression[i] = account_OR(expression[i])
        if expression[i] == "OR":
            if expression[i-1] and expression[i+1]:
                left = output.pop()
                right = expression[i+1]
                if isinstance(right, list):
                    right = account_OR(right)
                output.append(["OR", left, right])
                i += 2
        else:
            output.append(expression[i])
            i += 1
    return output
            
    

def account_AND(expression):
    
    output = []
   
    i = 0
    while i < len(expression):
        #print("Current item:", expression[i])
        if isinstance(expression[i],list):
            expression[i] = account_AND(expression[i])
        if expression[i] == "AND":
            if expression[i-1] and expression[i+1]:
                left = output.pop()
                right = expression[i+1]
                if isinstance(right, list):
                    right = account_AND(right)
                output.append(["AND", left, right])
                i += 2
        else:
            output.append(expression[i])
            i += 1
    return output

def account_NOT(expression):
    output = []
    i = 0
    while i < len(expression):
        if isinstance(expression[i], list):
            expression[i] = account_NOT(expression[i])
        if expression[i] == "NOT":
            operand = expression[i + 1]
            if isinstance(operand, list):
                operand = account_NOT(operand)
            output.append(["not", operand])
            i += 2
        else:
            output.append(expression[i])
            i += 1
    return output 





input = concat_expression(input)
expression = account_brackets(input)
#print(" Brackets handled:", expression)

expression = account_NOT(expression)
#print("NOT handled:", expression)

expression = account_AND(expression)
#print(" AND handled:", expression)

expression = account_OR(expression)
#print("OR handled:", expression)

print("Final AST:", expression)
