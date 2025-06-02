import re
import json
import argparse

"""
This module extract the relevant metadata from a Bayesian network

usage: getmetadata.py [file_path]

todo:
    -Is the content of the nodes all the metadata we need?
    -Change the function call, maybe a txt is not sufficient?
        -Make function call more general
        -still need to check if read works with all bayesian nets on the repository
    -Input validation?
"""


def get_nodes(file_path):

    """
    Reads a (.txt) bayesian model, and extracts the text content text of the nodes.

    Parameters:
        file_path (str): the file path

    Returns:
        matches ([str]): the (text) content of the nodes
    """
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    matches = re.findall(r"node\s+(\w+)\s*\{(.*?)\}", content, re.DOTALL)

    return matches



def format_metadata(node):
    """
    Extracts all the metadata from the node into a more organized state (Hard coded, ideally more generalized, maybe automate regex?)

    Parameters:
        node (str): The text content of the within-node structure

    Returns:
        metadata: Dictionary of key-value pairs for the metadata present

    """
    metadata = {}

    pattern = r'(\w+)\s*=\s*(\([^)]+\)|"[^"]+"|\S+);'
    matches = re.findall(pattern, node[1])

    def convert_value(value):
        """
        Converts a string to int, float, list, or keeps it as a string.
        """
        value = value.strip('"')  # Remove surrounding quotes

        if value.startswith("(") and value.endswith(")"):
            value_list = value[1:-1].split()
            return [convert_value(v) for v in value_list]  # Recursively process list elements

        # Try converting to int or float
        if re.fullmatch(r"-?\d+", value):  # Integer
            return int(value)
        elif re.fullmatch(r"-?\d+\.\d+", value):  # Float
            return float(value)

        return value  # Return as-is if not a number

    # Process all key-value pairs
    for key, value in matches:
        metadata[key] = convert_value(value)

    return metadata

def get_metadata_for_network(filename):
    """
    Processes the Bayesian model file and extracts metadata for each node.
    Returns the JSON representation of the extracted data.
    """
    print("filename: ", filename)
    nodes = get_nodes(filename)

    data = {node[0]: format_metadata(node) for node in nodes}

    json_data = json.dumps(data, indent=4)

    # Init example:
    # with open("bnserver/bnserverappV1/temp_models/endorisk_output_example.json", "w") as file:
    #     file.write(json_data)

    return json_data


def main(filename):
    """
    Processes the Bayesian model file and extracts metadata for each node.
    Returns the JSON representation of the extracted data.
    """
    nodes = get_nodes(filename)

    data = {node[0]: format_metadata(node) for node in nodes}

    json_data = json.dumps(data, indent=4)

    # Init example:
    # with open("bnserver/bnserverappV1/temp_models/endorisk_output_example.json", "w") as file:
    #     file.write(json_data)

    return json_data


DEFAULT_FILE = "bnserver/bnserverappV1/temp_models/endorisk.txt" # Change file for testing different files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a Bayesian model file and output JSON metadata.")
    parser.add_argument('filename', nargs='?', type=str, default=DEFAULT_FILE, help='The path to the file')

    args = parser.parse_args()

    result = main(args.filename)
    # print(result)