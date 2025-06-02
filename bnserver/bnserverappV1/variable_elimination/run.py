# Student: Soz Raheem
# Student number: s1096881
# Course: Artificial Intelligence Principles & Techniques
# Assignment 3
# 20-12-2024

"""
@Author: Joris van Vugt, Moira Berens, Leonieke van den Bulk

Entry point for the creation of the variable elimination algorithm in Python 3.
Code to read in Bayesian Networks has been provided. We assume you have installed the pandas package.

"""

"""
To run locally:

Invoke-RestMethod -Uri http://127.0.0.1:8000/api/predict `
  -Method Post `
  -Headers @{"Content-Type" = "application/json"} `
  -InFile "./example_incoming_json.json"
"""

from .read_bayesnet import BayesNet
from .variable_elim import VariableElimination, Factor
from .table_method import TableMethod
import json
import os


class Run():
    def run(self, data):
        """
        Performs variable elimination on a Bayesian network using the input data.

        This function loads a Bayesian network from a `.bif` file, extracts the necessary
        nodes and probabilities, processes query and evidence from input data, determines 
        an elimination ordering (optionally using a heuristic), and runs the variable 
        elimination algorithm.

        Parameters:
        -----------
        data : dict
            A dictionary representing input for inference including the query and evidence list.

        Returns:
        --------
        dict
            A dictionary representing the posterior probability distribution of the query variable.
        """

        # The class BayesNet represents a Bayesian network from a .bif file in several variables
        net = BayesNet('earthquake.bif') # Format and other networks can be found on http://www.bnlearn.com/bnrepository/
        #net = BayesNet('survey.bif')

        # These are the variables read from the network that should be used for variable elimination
        print("\n\nNodes:")
        print(net.nodes)
        print("\n\nValues:")
        print(net.values)
        print("\n\nParents:")
        print(net.parents)
        print("\n\nProbabilities:")
        print(net.probabilities)
        # Make your variable elimination code in the seperate file: 'variable_elim'. 
        # You use this file as follows:
        ve = VariableElimination(net, debug=True)

            # Set the node to be queried as follows:
        query = data['query']

        # The evidence is represented in the following way (can also be empty when there is no evidence): 
        evidence = {item['variable']: item['value'] for item in data['evidence_list']}
    

        # Determine your elimination ordering before you call the run function. The elimination ordering   
        # is either specified by a list or a heuristic function that determines the elimination ordering
        # given the network. Experimentation with different heuristics will earn bonus points. The elimination
        # ordering can for example be set as follows:

        heuristic = True # If True, then the heuristic is leaf nodes first. Else, the order is net.nods
        elim_order = ve.choose_elim_order(query, heuristic)

        # Call the variable elimination function for the queried node given the evidence and the elimination ordering as follows:   
        result = ve.run(query, evidence, elim_order)
        print("result of {}: {}".format(query, result))

        # run the table method
        #"""
        table_method = TableMethod(evidence, query, net, result)
        table_result = table_method.table_method()
        print("result of table method: {}".format(table_result))
        #"""
        return {"result": result, "significant_evidence": table_result[0], "conflict_information": table_result[1]}


if __name__ == '__main__':

    file_path = os.path.join(os.path.dirname(__file__), 'example_incoming_json.json')
    with open(file_path, 'r') as file:
        data = json.load(file)

    Runner = Run()
    Runner.run(data)