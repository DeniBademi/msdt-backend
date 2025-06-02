import sys
sys.path.append("..")
try:
    from pyhugin96 import *
except ImportError:
    from ..pyhugin96 import *
import math

def reset(domain):
    """
    Function that resets the domain/network, retracting all evidence and propagating the network.
    Params: domain: Domain
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
        remove D-seperated nodes from target
        Params:
        domain: Domain
        target: Node
        evidence: dictionary
    """
    evidence_copy = dict(evidence)
    ecnodes = list(evidence_copy.keys())
    for e in evidence.keys():
        ecnodes.remove(e)

        if not ecnodes:
            continue

        dsep = domain.get_d_separated_nodes([target], ecnodes, [dummy])
        #for i in dsep:
            #print(i.get_label())
            #print(e.get_label())
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
        Returns the index and difference for the biggest difference variable of the lists
        Params:
            one: List
            two: List
        Returns:
            tuple: The index and difference for the biggest difference variable of the lists
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
        Calculates the probability of the target node for 1 or more states, given possible evidence.
        Does so by resetting the domain, setting the evidence and running inference on the model, then returning the beliefs for the target node/state

        Args:
            domain: Domain
            target: Node
            evidence: dictionary, default = None
            target_state: int, default = None
        Returns:
            List: The beliefs for the target node/state
    """
    reset(domain)
    if evidence != None:
        for i in evidence.keys():
            node = i
            node.select_state(evidence[i])
        domain.propagate()
    result = target
    # return a distribution...
    if target_state != None:
        return target.get_belief(target_state)
    else:
        # print([target.get_belief(0), target.get_belief(1)])
        if target.get_number_of_states() > 2:
            lst = []
            for i in range(target.get_number_of_states()):
                lst.append(target.get_belief(i))
            return lst
        else:
            return [target.get_belief(0), target.get_belief(1)]