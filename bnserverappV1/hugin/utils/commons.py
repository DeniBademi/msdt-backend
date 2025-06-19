import sys
sys.path.append("..")
try:
    from pyhugin96 import *
except ImportError:
    from ..pyhugin96 import *
import math

def reset(domain):
    """
    Reset the Bayesian network domain by retracting all evidence and recompiling.

    Args:
        domain: The Bayesian network domain to reset

    This function ensures the network is compiled, removes all evidence,
    and propagates the network to update all probabilities.
    """
    if not domain.is_compiled():
        domain.compile()
    domain.retract_findings()
    domain.propagate()

def nprint(node):
    """
    printerfunction for nodes, prints the label and value of the given node
    Params: node: Node
    """
    if type(node) == dict:
        for e in node:
            print(e.get_label(), node[e])
    else:
        print(node.get_label())

def remove_dseparated(domain, target, evidence, dummy):
    """
    Remove d-separated nodes from the evidence set.

    Args:
        domain: The Bayesian network domain
        target: The target node
        evidence (dict): Dictionary of evidence nodes and their states
        dummy: A dummy node used for d-separation checks

    Returns:
        dict: A new evidence dictionary with d-separated nodes removed

    This function removes evidence nodes that are d-separated from the target
    given the other evidence nodes, as they cannot influence the target's
    probability distribution.
    """
    evidence_copy = dict(evidence)
    ecnodes = list(evidence_copy.keys())
    for e in evidence.keys():
        ecnodes.remove(e)

        if not ecnodes:
            continue

        dsep = domain.get_d_separated_nodes([target], ecnodes, [dummy])
        if e in dsep:
            evidence_copy.pop(e)
        ecnodes.append(e)
    return evidence_copy

def get_dseparated_nodes(domain, target, evidence, dummy):
    dseparated_nodes = []
    evidence_nodes = list(evidence.keys())

    for e in evidence.keys():
        temp_nodes = evidence_nodes.copy()
        temp_nodes.remove(e)

        if not temp_nodes:
            continue

        try:
            dsep = domain.get_d_separated_nodes([target], temp_nodes, [dummy])

            if e in dsep:
                dseparated_nodes.append(e)
        except Exception as ex:
            print(f"Error checking d-separation for {e}: {ex}")

    return dseparated_nodes

def hellinger_distance_discrete(p, q):
    """
        Calculates the hellinger distance between two probability lists.

        Args:
            p: List
            q: List
        Returns:
            float: The hellinger distance between the two probability lists
    """
    return (1 / math.sqrt(2)) * math.sqrt(sum(math.pow(math.sqrt(p[i]) - math.sqrt(q[i]), 2) for i in range(len(p))))

def max_difference(one, two):
    """
    Find the maximum difference between corresponding elements in two lists.

    Args:
        one (list): First list of numbers
        two (list): Second list of numbers

        Returns:
        tuple: (percentage, index) where:
               - percentage is the maximum difference as a percentage
               - index is the position where the maximum difference occurs
    """
    maxdif = 0
    for i in range(len(one)):
        dif = one[i] - two[i]
        if dif < maxdif:
            maxdif = dif
            index = i
    percentage = round(abs(maxdif) * 100, 1)
    return percentage, index

def P(domain, target, evidence=None, target_state=None):
    """
    Calculate the probability distribution of a target node given evidence.

        Args:
        domain: The Bayesian network domain
        target: The target node
        evidence (dict, optional): Dictionary of evidence nodes and their states
        target_state (int, optional): Specific state of the target to get probability for

        Returns:
        float or list: If target_state is specified, returns the probability of that state.
                      Otherwise, returns a list of probabilities for all states.

    This function resets the network, applies the evidence, propagates the network,
    and returns the resulting probability distribution for the target node.
    """
    reset(domain)
    if evidence != None:
        for i in evidence.keys():
            node = i
            node.select_state(evidence[i])
        domain.propagate()
    result = target
    if target_state != None:
        return target.get_belief(target_state)
    else:
        if target.get_number_of_states() > 2:
            lst = []
            for i in range(target.get_number_of_states()):
                lst.append(target.get_belief(i))
            return lst
        else:
            return [target.get_belief(0), target.get_belief(1)]