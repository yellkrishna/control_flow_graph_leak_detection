import argparse
import re

# Function to parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="LLVM-like code analysis")
    parser.add_argument("-i", "--input", required=True, help="Input LLVM-like file")
    parser.add_argument("-g", "--output", required=True, help="Output directory for dot files")
    return parser.parse_args()

def parse_input_file(input_file):
    functions = {}

    with open(input_file, 'r') as file:
        lines = file.readlines()

        current_function = None
        for line in lines:
            line = line.strip()

            if line.startswith('define'):
                function_name = line.split('@')[1].split('(')[0].strip()
                current_function = function_name
                functions[current_function] = []
            elif line.startswith('}'):
                current_function = None
            elif current_function is not None:
                functions[current_function].append(line)

    return functions


# Function to identify basic blocks
def identify_basic_blocks(functions):
    basic_blocks = {}

    block_counter = 0
    for function_name, instructions in functions.items():
        blocks = []
        current_block = []

        for instruction in instructions:
            # Remove any leading/trailing whitespace and skip empty lines
            instruction = instruction.strip()
            if not instruction:
                continue

            # Check if the instruction is a label or leader

            # print("current block", current_block)
            if is_leader(instruction) and current_block:
                #print("current block inside isleader", current_block)
                blocks.append(current_block.copy())
                current_block = []

            current_block.append(instruction)

            if is_conditional_jump(instruction):
                #print("inside is conitional", instruction)
                branch_targets = [target.split('label %')[-1] for target in instruction.split(',') if 'label' in target]
                current_block.append(branch_targets)
                blocks.append(current_block.copy())
                current_block = []
            elif is_unconditional_jump(instruction) or is_ret(instruction):
                # print("inside is unconitional", current_block)
                branch_target = [target.split('label %')[-1] for target in instruction.split(',') if 'label' in target]
                current_block.append(branch_target) if not is_ret(instruction) else current_block.append(branch_target)
                blocks.append(current_block.copy())
                current_block = []

            elif is_unconditional_jump_call(instruction):
                pattern = r'@([^(\s]+)'
                branch_target = [re.search(pattern, target).group(1) for target in instruction.split() if re.search(pattern, target)]
                # print("branch target", branch_target)
                #branch_target = [target.split('@')[-1] for target in instruction.split() if '@' in target]
                current_block.append(branch_target)
                blocks.append(current_block.copy())
                current_block = []

        if current_block:
            blocks.append(current_block.copy())

        formatted_blocks = {}
        for block in blocks:
            formatted_blocks[f"Block {block_counter}"] = block
            block_counter += 1

        basic_blocks[function_name] = formatted_blocks

    return basic_blocks

def is_conditional_jump(instruction):
    # Check if the instruction represents a conditional jump (e.g., br with i1 condition)
    return 'br i1' in instruction 
def is_unconditional_jump_call(instruction):
    # Check if the instruction represents a conditional jump (e.g., br with i1 condition)
    return 'call' in instruction 

def is_unconditional_jump(instruction):
    # Check if the instruction represents an unconditional jump (e.g., br without i1 condition)
    return 'br' in instruction and 'br i1' not in instruction

def is_leader(instruction):
    # Check if the instruction is the first line of a basic block
    return instruction.endswith(':') or instruction.startswith('define')

def is_ret(instruction):
    # Check if the instruction is a return statement
    return 'ret ' in instruction


# Function to create jump targets
def extract_jump_targets(input_data):
    jump_targets = {}
    for function_name, blocks in input_data.items():
        count = 0
        jump_targets[function_name] = {}
        for block_label, block_content in blocks.items():
            #print("block content", block_content)
            block_number = int(block_label.split()[-1])  # Extract block number
            first_element = block_content[0]
            pen_ult_element = block_content[-2]

            # Check if the first element indicates a jump target
            if first_element.endswith(':'):
                # Extract label and associate it with block number
                label = first_element.rstrip(':')
                jump_targets[function_name][label] = block_number
            else:
                if count == 0:
                    jump_targets[function_name][function_name] = block_number
            count += 1

    return jump_targets


# Function to construct control-flow graphs
def construct_control_flow_graphs(basic_blocks, jump_targets):
    control_flow_graphs = {}

    for function_name, blocks in basic_blocks.items():
        #jump_target_dict = jump_targets.get(function_name, {})
        #print("jump target dict", jump_target_dict)
        cfg = {}

        for block_number, instructions in blocks.items():
            #print(function_name, block_number, instructions)
            successors = []

            if isinstance(instructions[-1], list):
                for label in instructions[-1]:
                    #print("label", label)
                    for function_name in jump_targets.keys():
                        if label in jump_targets[function_name]:
                            successors.append(jump_targets[function_name][label])
                    #if label in jump_target_dict:
                    #    print('entered', label, jump_target_dict)
                    #    successors.append(jump_target_dict[label])


            cfg[int(block_number.split()[1])] = successors

        control_flow_graphs[function_name] = cfg

    return control_flow_graphs



# Function to generate dot output
def generate_dot_output(control_flow_graphs, output_directory):
    dot_output = "digraph {\n"
    node_definitions = {}  # To store node definitions
    node_count = 0
    for inner_dict in control_flow_graphs.values():
        # Add the length of each inner dictionary to the total
        node_count += len(inner_dict)

    for function_name, cfg in control_flow_graphs.items():
        # Create node definitions
        #node_count = len(cfg)
        #print('cfg', cfg)
        #print("node count", node_count)
        for node in range(node_count):
            node_definitions[node] = f"Node{node} [shape=record,label=\"\"];\n"

        # Define connections between nodes
        for node, successors in cfg.items():
            # print("node", node, "successors", successors, "node definitions", node_definitions)
            dot_output += node_definitions[node]
            if len(successors) == 0:
                continue
            count = 1
            for successor in successors:
                dot_output += f"Node{node} -> Node{successor} [label=\"{count}\"];\n"
                count += 1



    dot_output += "}"

    # Save DOT output to a file or print it
    if output_directory:
        print(dot_output)
        with open(output_directory, "w") as file:
            file.write(dot_output)
        print(f"DOT output saved to {output_directory}")
    else:
        print(dot_output)


        

import re

def has_leak(llvm_ir):
    # Pattern for a call to SOURCE storing the result in a variable
    source_pattern = re.compile(r'(%\w+)\s*=\s*call\s+i32\s+@SOURCE\s*\(\s*\)')

    # Pattern for a call to SINK using the result of SOURCE
    sink_pattern = re.compile(r'call\s+i32\s+@SINK\s*\(\s*i32\s+(%\w+)\s*\)')

    for function_code in llvm_ir.values():
        function_code = ' '.join(function_code)  # Combine lines of code for each function

        # Search for matches
        source_match = source_pattern.search(function_code)
        sink_match = sink_pattern.search(function_code)

        # Check if there is a call to SOURCE and its result is used in a call to SINK
        if bool(source_match) and bool(sink_match):
            source_var = source_match.group(1)
            sink_var = sink_match.group(1)

            if source_var == sink_var:
                return "Leak"

    return "No Leak"




# Main function
def main():
    args = parse_arguments()
    input_file = args.input
    output_directory = args.output

    functions = parse_input_file(input_file)
    #print(functions)
    basic_blocks = identify_basic_blocks(functions)
    #print(basic_blocks)
    jump_targets = extract_jump_targets(basic_blocks)
    #print(jump_targets)
    control_flow_graphs = construct_control_flow_graphs(basic_blocks, jump_targets)
    #print(control_flow_graphs)
    generate_dot_output(control_flow_graphs, output_directory)

    result = has_leak(functions)
    print(result)

if __name__ == "__main__":
    main()
