import re
import json

def get_nodes_bif(file_path):
    """
    Reads a .bif bayesian model file and extracts the variable definitions.

    Parameters:
        file_path (str): the file path

    Returns:
        matches ([str]): list of tuples containing (variable_name, variable_content)
    """
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Find all variable blocks in the .bif file: example: variable x {
    matches = re.findall(r"variable\s+(\w+)\s*\{(.*?)\}", content, re.DOTALL)
    return matches

def format_metadata_bif(node):
    """
    Extracts metadata from a .bif variable definition into a structured format.

    Parameters:
        node (tuple): Tuple containing (variable_name, variable_content)

    Returns:
        metadata (dict): Dictionary containing the extracted metadata
    """
    metadata = {}
    content = node[1]

    # Extract states - updated regex to match the .bif format
    states_match = re.search(r'type discrete.*?\{([^}]+)', content)
    print("states_match: ", states_match)
    if states_match:
        # Extract the states part and clean it up
        states_str = states_match.group(1)
        # Remove any whitespace and split by commas
        states = [state.strip() for state in states_str.split(',')]
        metadata['states'] = states

    return metadata

def get_metadata_for_network_bif(filename):
    """
    Processes a .bif Bayesian model file and extracts metadata for each variable.
    Returns the JSON representation of the extracted data.

    Parameters:
        filename (str): Path to the .bif file

    Returns:
        str: JSON string containing the metadata
    """
    nodes = get_nodes_bif(filename)
    print("nodes: ", nodes)
    data = {node[0]: format_metadata_bif(node) for node in nodes}
    return json.dumps(data, indent=4)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process a .bif Bayesian model file and output JSON metadata.")
    parser.add_argument('filename', type=str, help='The path to the .bif file')

    args = parser.parse_args()
    result = get_metadata_for_network_bif(args.filename)
    print(result)