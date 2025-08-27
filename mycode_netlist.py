from Main import expression


demorgan_rules = {
    "AND": {
        "gates": ["NAND", "not"],
        "description": "A AND B = not(NAND(A,B))",
        "gate_count": 2
    },
    "OR": {
        "gates": ["NAND", "NAND"],
        "description": "A OR B = NAND(not(A), not(B)) = NAND(NAND(A,A), NAND(B,B))",
        "gate_count": 3
    },
    "not": {
        "gates": ["NAND"],
        "description": "not(A) = NAND(A,A)",
        "gate_count": 1
    }
}

def convert_to_nand(operation, inputs):
    """Convert logical operation to NAND implementation"""
    if operation not in demorgan_rules:
        raise ValueError(f"Unsupported operation: {operation}")
    
    rule = demorgan_rules[operation]
    if operation == "not":
        return f"NAND({inputs[0]}, {inputs[0]})"
    elif operation == "AND":
        nand_result = f"NAND({inputs[0]}, {inputs[1]})"
        return f"NAND({nand_result}, {nand_result})"
    elif operation == "OR":
        not_a = f"NAND({inputs[0]}, {inputs[0]})"
        not_b = f"NAND({inputs[1]}, {inputs[1]})"
        return f"NAND({not_a}, {not_b})"

def traverse_nested_lists(nested_list):
    """
    Traverse nested lists from innermost to outermost.
    Returns a list of elements in traversal order.
    """
    result = []
    
    def inner_traverse(lst, depth=0):
        # Base case: if element is not a list
        if not isinstance(lst, list):
            return
        
        # Check if current list contains any nested lists
        has_nested = any(isinstance(x, list) for x in lst)
        
        if not has_nested:
            # If no nested lists, add current list to result
            result.append((depth, lst))
            return
            
        # Recursive case: traverse nested lists first
        for item in lst:
            if isinstance(item, list):
                inner_traverse(item, depth + 1)
        
        # Add current list after processing nested ones
        result.append((depth, lst))
    
    inner_traverse(nested_list)
    
    # Sort by depth (descending) to get innermost first
    result.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in result]

# Example usage:

traversed = traverse_nested_lists(expression)


def process_expression(traversed):
    """Process nested expression and convert to NAND gates"""
    result = []
    temp_vars = {}
    not_vars = {}  # Track NOT operations
    var_counter = 0
    
    def get_temp_var():
        nonlocal var_counter
        var_counter += 1
        return f"temp_{var_counter}"
    
    for lst in traversed:
        if len(lst) == 1:
            continue
            
        if lst[0] == "not":
            if len(lst) != 2:
                raise ValueError("NOT should have exactly one operand")
            operand = lst[1]
            
            # Handle sub-expression or variable
            input_val = temp_vars.get(str(operand), str(operand))
            temp_var = get_temp_var()
            nand_conversion = f"NAND({input_val}, {input_val})"
            temp_vars[str(lst)] = temp_var
            not_vars[str(operand)] = temp_var  # Track NOT operation result
            result.append(f"{temp_var} = {nand_conversion}")
            
        elif lst[0] in ("AND", "OR"):
            operator = lst[0]
            operands = lst[1:]
            if len(operands) < 2:
                raise ValueError(f"{operator} should have at least two operands")
            
            if operator == "AND":
                processed_operands = [temp_vars.get(str(op), str(op)) for op in operands]
                temp_var = get_temp_var()
                nand_result = f"NAND({processed_operands[0]}, {processed_operands[1]})"
                result.append(f"{temp_var} = {nand_result}")
                temp_var2 = get_temp_var()
                result.append(f"{temp_var2} = NAND({temp_var}, {temp_var})")
                temp_vars[str(lst)] = temp_var2
            
            elif operator == "OR":
                processed_operands = []
                for op in operands:
                    if str(op) in not_vars:
                        processed_operands.append(not_vars[str(op)])
                    else:
                        temp = get_temp_var()
                        result.append(f"{temp} = NAND({op}, {op})")
                        processed_operands.append(temp)
                
                temp_var = get_temp_var()
                result.append(f"{temp_var} = NAND({processed_operands[0]}, {processed_operands[1]})")
                temp_vars[str(lst)] = temp_var
        
        else:
            raise ValueError(f"Unknown operator: {lst[0]}")
    
    return result

# Use the function
traversed = traverse_nested_lists(expression)
final_circuit = process_expression(traversed)
print("\nCircuit implementation:")
for line in final_circuit:
    print(line)


