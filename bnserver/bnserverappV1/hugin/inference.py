import os
import contextlib
from io import StringIO
import argparse
import json
import re

def get_state_values(node):
    """
    Returns a dictionary with the state labels as keys and the state values as values
    """
    state_dict = {}
    for i in range(node.get_number_of_states()):
        state_dict[node.get_state_label(i)] = i
    return state_dict

def parse_request(network, targetname, evidence_data=None):
    try:
        from .utils.commons import reset
    except ImportError:
        from utils.commons import reset
    reset(network)
    evidence = {}

    if evidence_data:
        for node_name, state in evidence_data.items():
            node = network.get_node_by_name(node_name)
            state_dict = get_state_values(node)
            if node is None:
                raise ValueError(f"Node '{node_name}' not found in the network.")
            #raw_evidence[node_name] = state

            try:
                state_value = state_dict[state]
            except KeyError:
                raise ValueError(f"State '{state}' not found for node '{node_name}'. Possible states: {state_dict}")
            node.select_state(state_value)
            evidence[node] = state_value
    network.propagate()

    try:
        target = network.get_node_by_name(targetname)
    except KeyError:
        raise ValueError(f"Target '{targetname}' not found in the network.")
    return evidence, target

def stdout_wrapper(domain, target, evidence, dummy):
    """Wrapper function that saves all print statements of this function to a .log file (see folder 'logs')

    Args:
        domain (Domain): The domain object
        target (Node): The target node
        evidence (dict): The evidence dictionary
        dummy (Node): The dummy node
    """
    try:
        from .utils.explanation_methods.table import table
    except ImportError:
        from utils.explanation_methods.table import table

    log_dir = os.path.join(os.path.dirname(__file__), "logs") # save it in 'logs' folder
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "hugin_output.log")
    log_buffer = StringIO()
    with contextlib.redirect_stdout(log_buffer), contextlib.redirect_stderr(log_buffer):
        try:
            table(domain, target, evidence, dummy)
        except Exception as e:
            print("Error during table2 execution:", e)

    # After the context, write buffer to file
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write(log_buffer.getvalue())

def infer(filename, path, targetname, evidence_data=None, case_name=None):
    """
        This is the main infer function that runs everything.

        Args:
            filename (str): Name of the bayesian network
            path (str): Path of the bayesian network file
            targetname (str): Name of the query (only one target)
            evidence_data (dict): Dictionary {str, int} where the str is the name of the evidence node and the int is the state of the evidence node.
        Returns:
            None
    """
    try:
        from .pyhugin96 import Domain, CATEGORY, KIND, Node
    except ImportError:
        from pyhugin96 import Domain, CATEGORY, KIND, Node
    #print(path,"LOLO")
    print(f"filename: {filename}")
    print(f"path: {path}")
    print(f"targetname: {targetname}")
    print(f"evidence_data: {evidence_data}")
    print(f"case_name: {case_name}")

    network = Domain.parse_domain(path)
    network.open_log_file("{}.log".format(filename))
    network.triangulate()
    network.compile()
    network.close_log_file()


    has_utilities = any(node.get_category() == CATEGORY.UTILITY for node in     network.get_nodes())
    print(f"has_utilities: {has_utilities}")

    network.update_policies()


    if case_name:
            network.parse_case(case_name, parse_listener)
            # print("Propagating the evidence specified in '{}'".format(case_name))
            network.propagate()
            # print("P(evidence) = {}".format(    network.get_normalization_constant()))
            if has_utilities:
                # print("Updated beliefs:")
                pass
            else:
                network.update_policies()
                # print("Overall expected utility: {}".format(    network.get_expected_utility()))
                # print("Updated beliefs (and expected utilities):")
            # print_beliefs_and_utilities(    network)

    assert isinstance(network, Domain), "failed to load domain"

    dummy = Node(network)
    dummy.set_label("d_sep_dummy")
    evidence, target = parse_request(network, targetname, evidence_data)
    stdout_wrapper(network, target, evidence, dummy)
    network.delete()

def parse_listener(line, description):
    """A parse listener that prints the line number and error description."""
    print("Parse error line {}: {}".format(line, description))

def bif_to_net_helper1(bif_file_path, net_name, folder_path, allow_mod=True):
    """
    This function convert bayesian networks in bif-format into net-format suitable or hugin inference
    """
    try:
        import pyagrum as gum #add to environment
    except ImportError:
        print("pyagrum is not installed. Please install it using 'pip install pyagrum'.")
        return None

    #load the bif file
    network = gum.loadBN(bif_file_path)

    # Ensure the folder exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Save as .net file in the specified folder
    net_file_path = os.path.join(folder_path, net_name)

    gum.saveBN(network, net_file_path, True)
    return network

def bif_to_net_helper2(input_path, output_path):
    """
    This second function adjusts the net file created by the first helper function to the right format accepted by the build-in hugin parser
    """
    with open(input_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    states_pattern = re.compile(r'^\s*states\s*=\s*\((.*?)\)\s*;?\s*$')
    software_pattern = re.compile(r'^\s*software\s*=\s*".*"\s*;?\s*$')
    simple_data_pattern = re.compile(r'data\s*=\s*\(.*\)\s*;?')
    

    inside_net_block = False
    inside_potential_block = False
    inside_data_block = False
    num_parents = 0

    for line in lines:
        stripped_line = line.strip()

        # NET BLOCK -------------------------------------
        if stripped_line.startswith('net'):
            inside_net_block = True
            new_lines.append(line)
            continue
        
        
        if inside_net_block and stripped_line == '}':
            inside_net_block = False
            new_lines.append(line)
            continue

        if inside_net_block and software_pattern.match(line):
            continue

        if inside_net_block and stripped_line.startswith('name'):
    
            name_match = re.match(r'(\s*name\s*=\s*)(\w+)(\s*;)', stripped_line)
            if name_match:
                new_line = f'   {name_match.group(1)}"{name_match.group(2)}"{name_match.group(3)}\n'
                new_lines.append(new_line)
                continue

        
        # STATES ---------------------------------------
        match = states_pattern.match(line)
        if match:
            states = match.group(1).strip().split()
            quoted_states = ' '.join(f'"{s}"' for s in states)
            new_line = f'   states = ( {quoted_states} );\n'
            new_lines.append(new_line)
            continue

        # POTENTIALS ------------------------------------
        if stripped_line.startswith('potential'):
            inside_potential_block = True
            new_lines.append(line)

            match = re.match(r'potential\s*\(\s*(\w+)\s*\|\s*(.*?)\s*\)', stripped_line)
            if match:
                child = match.group(1)  
                parents_str = match.group(2)  
                parents = parents_str.strip().split() 
                num_parents = len(parents)  
                print(f"Potential for {child}: {num_parents} parent(s) -> {parents}")

            # no "|"
            else:
                match_simple = re.match(r'potential\s*\(\s*(\w+)\s*\)', stripped_line)
                if match_simple:
                    child = match_simple.group(1)
                    num_parents = 0
                    print(f"Potential for {child}: {num_parents} parent(s)")
            continue

        if inside_potential_block and stripped_line == '}':

            inside_potential_block = False
            inside_data_block = False
            new_lines.append("}\n")
            continue

        # DATA BLOCK START -------------------------
        if inside_potential_block and stripped_line.startswith('data'):
            if simple_data_pattern.match(stripped_line):

                new_lines.append(line)
                inside_data_block = False  
            else:
                new_lines.append('   data =')
                inside_data_block = True
            continue


        # Parsing nested data lines
        if inside_data_block and '(' in stripped_line:

            # remove comments
            line_wo_comment = re.sub(r'%.*', '', line).strip()

            # tokenize
            tokens = re.findall(r'\(|\)|[^\s()]+', line_wo_comment)

            new_line = ''
            prev_token = ''
            for token in tokens:
                if token == '(':
                    # add '(' without trailing space
                    new_line += '('
                elif token == ')':
                    # remove trailing space before ')'
                    new_line = new_line.rstrip() + ')'
                else:
                    # Add space before token unless its after '('
                    if prev_token == '(' or new_line == '':
                        new_line += token
                    else:
                        new_line += ' ' + token
                prev_token = token
            
            new_lines.append(new_line + '\n')
            continue
            
        new_lines.append(line)

    with open(output_path, 'w') as f:
        f.writelines(new_lines)

def bif_to_net(bif_file_path, net_file_name, folder_path, allow_mod=True):
    bif_to_net_helper1(bif_file_path, net_file_name, folder_path, allow_mod=True)

    # Save as .net file in the specified folder
    net_file_path = os.path.join(folder_path, net_file_name)

    bif_to_net_helper2(net_file_path,net_file_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Bayesian Network Inference')
    parser.add_argument('--filename',
                        type=str, help='Name of the Bayesian network file',
                        default="asia_fixed")
    parser.add_argument('--path', type=str, help='Path to the Bayesian network file',
                        default="/Users/steve/IdeaProjects/programming/repository_MSDT/backend/bnserver/bnserverappV1/hugin/asia.net")
    parser.add_argument('--targetname', type=str, help='Name of the target node',
                        default="bronc")
    parser.add_argument('--evidence', type=str, help='Evidence in the format "node1:state1,node2:state2" in a json string',
                        default='{"smoke": "no"}')
    args = parser.parse_args()

    #Run this code to test out how you can transform bif-files to net-files --> transforms the asia.bif to asia.net and saves it into hugin folder. 
    bif_to_net("/Users/steve/IdeaProjects/programming/repository_MSDT/backend/bnserver/bnserverappV1/hugin/asia.bif", "asia.net", "/Users\steve/IdeaProjects/programming/repository_MSDT/backend/bnserver/bnserverappV1/hugin")

    #The rest of the code run inference on this asia.net file.
    filename = args.filename
    filepath = args.path
    target = args.targetname
    evidence = json.loads(args.evidence)
    infer(filename, filepath, target, evidence)