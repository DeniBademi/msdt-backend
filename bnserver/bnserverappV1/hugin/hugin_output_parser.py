# Hugin output coverter into JSON
# It is done such that an output of the form of hugin_output_v1.log is handled (result is saved as 'parsed_output_v1.json')

# To do: test it on other output examples
# To do: add partially supporting/contradicting varialbes? needed or not?

import os
from pathlib import Path
import re
import json

def parse_hugin_output(text: str):
    lines = text.splitlines()
    data = {
        "prediction": {},
        "supporting_factors": [],
        "opposing_factors": [],
        "immediate_causes": [],
        "level3_explanations": {},
        "explanation_level": "Level 3"
    }

    # The probability of the target value (before the explanation levels)
    for line in lines:
        if "The chance of" in line:
            match = re.search(r'The chance of (.+?) being (.+?) = ([0-9.]+)', line)
            if match:
                var_name = match.group(1).strip()
                state_value = match.group(2).strip()
                prob = float(match.group(3))

                # convert to json
                data["prediction"] = {
                    "variable_name": var_name,
                    "predicted_value": state_value,
                    "probability": prob
                }


    # Level 1: supporting and opposing significant evidence/factors
    in_support_section = False
    in_opposing_section = False
    # avoid repeated factors
    supporting_seen = set()
    opposing_seen = set()
    #checks if there are any opposing factors
    has_opposing_factors = False

    for line in lines:
        line = line.strip()
        # check if the evidence is in support or not
        if "What are the factors that support" in line:
            in_support_section = True
            in_opposing_section = False
            continue

        # parse a supporting factor
        if in_support_section and "=" in line:
            parts = line.split("=")
            # Check if the structure 'variable = value' holds
            if len(parts) == 2:
                feature = parts[0].strip() # variable
                value_part = parts[1].strip() # value
                # avoiding duplicate values
                key = (feature, value_part)
                if key not in supporting_seen:
                    supporting_seen.add(key)
                    if "(" in value_part: # check for additional comments, e.g. yes (Very important)
                        value = value_part.split("(")[0].strip()
                        importance = value_part.split("(")[1].replace(")","").strip() # remove ()

                        # convert to json
                        data["supporting_factors"].append({
                            "feature": feature,
                            "value": value,
                            "importance": importance
                        })
                    else:
                        data["supporting_factors"].append({
                            "feature": feature,
                            "value": value_part,
                            "importance": "Neutral"
                        })

        if "What are the factors that do not support" in line:
            in_support_section = False
            in_opposing_section = True
            continue


        # parse an opposing factor
        if in_opposing_section and "=" in line:
            has_opposing_factors = True
            parts = line.split("=")
            # Check if the structure 'variable = value' holds
            if len(parts) == 2:
                feature = parts[0].strip() # variable
                value = parts[1].strip() # value
                # avoiding duplicate values
                key = (feature, value_part)
                if key not in opposing_seen:
                    opposing_seen.add(key)
                # convert to json
                data["opposing_factors"].append({
                    "feature": feature,
                    "value": value
                })


        # level 1 factors stop when we have reached level 2
        if "Level 2" in line:
            in_support_section = False
            in_opposing_section = False
            break
    if not has_opposing_factors:
        data["opposing_factors"].append({
                    "feature": "None",
                    "value": "None"
                })

    # Level 2: immediate evidence
    in_level2_section = False
    for line in lines:
        line = line.strip()
        if "As the immediate causes of" in line:
            in_level2_section = True
            continue
        if "Level 3" in line: # get out of this loop after reaching level 3
            break

        if in_level2_section and ":" in line:
            match = re.search(r'(.+?):\s+([0-9.]+)\s*% increase in (.+)', line)
            if match:
                feature = match.group(1).strip()
                increase = float(match.group(2))
                state = match.group(3).strip()
                data["immediate_causes"].append({
                    "feature": feature,
                    "increase_percent": increase,
                    "state": state
                })

    #level 3
    data["level3_explanations"] = []

    current_node = None
    current_mode = None
    in_partial_support = False

    has_opposing_factors = False
    has_partial_supporting_factors = False

    current_entry = None
    previous_node = None

    for line in lines:
        line = line.strip()

        if line.startswith("What are the factors that support above prediction of"):
            current_node = line.split("of")[-1].strip().rstrip("?")
            current_mode = "support"
            in_partial_support = False

            if current_entry is not None:

                if not has_partial_supporting_factors:
                    current_entry["partially_supporting"].append({"feature": "None", "value": "None"})


            current_entry = {
                "query": current_node,
                "supporting": [],
                "opposing": [],
                "partially_supporting": []
            }
            data["level3_explanations"].append(current_entry)

            has_opposing_factors = False
            has_partial_supporting_factors = False

            continue

        if line.startswith("Partially supporting:"):
            has_partial_supporting_factors = True
            in_partial_support = True
            current_mode = "partial_support"
            continue

        if line.startswith("What are the factors that do not support above prediction of"):
            current_mode = "oppose"
            in_partial_support = False
            continue

        if current_mode == "oppose" and line.startswith("None"):
            current_entry["opposing"].append({"feature": "None", "value": "None"})
            continue

        if current_entry and "=" in line:
            parts = line.split("=")
            feature = parts[0].strip()
            value = parts[1].strip()

            if current_mode == "support":
                current_entry["supporting"].append({"feature": feature, "value": value})
            elif in_partial_support:
                current_entry["partially_supporting"].append({"feature": feature, "value": value})
            elif current_mode == "oppose":
                if feature == None:
                    current_entry["opposing"].append({"feature": "None", "value": "None"})
                else:
                    current_entry["opposing"].append({"feature": feature, "value": value})

        if line.startswith("------------------------------------------------------------------------------"):
            current_mode = None
            in_partial_support = False

    if current_entry is not None:
        if not has_partial_supporting_factors:
            current_entry["partially_supporting"].append({"feature": "None", "value": "None"})

    return data

def parse_log_file(input_path: str, output_path: str):
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input log file not found: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    parsed_data = parse_hugin_output(raw_text)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, indent=4)

    print(f"Parsed JSON written to file: {output_file}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__)) # get directory of this script file
    input_p = os.path.join(script_dir, "logs\hugin_output.log") # build path input file hugin_output.log
    output_p = os.path.join(script_dir, "logs\parsed_output.json")

    parse_log_file(
        input_path=input_p,
        output_path=output_p
    )
# parsed = parse_hugin_output(raw_output)
# print(json.dumps(parsed, indent=2))
