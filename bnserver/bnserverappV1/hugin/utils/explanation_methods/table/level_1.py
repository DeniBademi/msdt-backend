import numpy as np
from ...commons import (
    P,
    hellinger_distance_discrete,
    remove_dseparated
)

def impact(domain, target, evidence, e):
    """
        Calculates the impact of an evidence variable e, given all evidence, using the hellinger distance.

        Args:
            domain: Domain
            target: Node
            evidence: dictionary
            e: dictionary
        Returns:
            float: The impact of the evidence variable e
    """
    ptE = P(domain, target, evidence)
    evidence_copy = dict(evidence)
    del evidence_copy[e]
    ptEe = P(domain, target, evidence_copy)
    # print(kl_div(ptE, ptEe))
    return hellinger_distance_discrete(ptE, ptEe)

def threshold(domain, target, evidence, alpha):
    """
        Determines the threshold theta, as the Hellinger distance between P(T|E) adn G
        Args:
            domain: Domain
            target: Node
            evidence: dictionary
            alpha: float
        Returns:
            float: The threshold theta
    """
    pte = P(domain, target, evidence)
    G = P(domain, target, evidence) - alpha * (np.array(P(domain, target, evidence)) - P(domain, target))
    return hellinger_distance_discrete(pte, G)

def esig(domain, target, evidence, dummy, a=None):
    """
    Determines the significant evidence, and prints alpha
        Args:
            domain: Domain
            target: Node
            evidence: dictionary
            a: list, default: None
        Returns:
            dictionary: The significant evidence
    """
    print("domain:",domain)
    print("target:",target)
    print("evidence:",evidence)
    print("dummy:",dummy)
    evidence = remove_dseparated(domain, target, evidence, dummy)
    esig = {}
    if a == None:
        a = [0.9, 0.8, 0.7, 0.6, 0.5, 0.5, 0.3, 0.2, 0.1, 0.001]
    c = 0
    keys = list(evidence.keys())
    while len(keys) > len(esig):
        if c < len(a):
            print("ADSADA")
            alpha = a[c]
        else:
            print("ran out of alpha's")
            return esig
        theta = threshold(domain, target, evidence, alpha)
        for e in keys:
            if impact(domain, target, evidence, e) > theta:
                # print(e.get_label())
                esig[e] = evidence[e]
                del evidence[e]
                keys.remove(e)
        c += 1
    print("alpha:", alpha)
    return esig

def RR(domain, esign, target, target_state, e):
    """
        Calculates the relative risk P(T|E)/P(T|E-e)
        Args:
            domain: Domain
            esign: dictionary
            target: Node
            target_state: int
            e: String
        Returns:
            float: The relative risk P(T|E)/P(T|E-e)
    """
    evidence_copy = dict(esign)
    ptE = P(domain, target, evidence_copy, target_state)
    del evidence_copy[e]
    ptEe = P(domain, target, evidence_copy, target_state)
    return ptE / ptEe

def direction_label(domain, esign, target, target_state, e):
    """
        Determines the direction label of a node e
        Args:
            domain: Domain
            esign: dictionary
            target: Node
            target_state: int
            e: String
        Returns:
            String: The direction label of the node e
    """
    evidence_copy = dict(esign)
    if RR(domain, evidence_copy, target, target_state, e) > 1:
        del evidence_copy[e]
        if all(RR(domain, evidence_copy, target, target_state, e1) > 1 for e1 in evidence_copy):
            return "dcons"
        else:
            return "donf"

def delta_t_e(domain, esign, target, target_state, e):
    evidence_copy = dict(esign)
    ptE = P(domain, target, evidence_copy, target_state)
    del evidence_copy[e]
    ptEe = P(domain, target, evidence_copy, target_state)
    return ptE - ptEe

def delta_t_E(domain, esign, target, target_state, e):
    evidence_copy = dict(esign)
    ptE = P(domain, target, evidence_copy, target_state)
    pt = P(domain, target, target_state=target_state)
    return ptE - pt

def direction_of_change1(domain, esign, target, e):
    if all((delta_t_E(domain, esign, target, t, e) > 0 and delta_t_e(domain, esign, target, t, e) > 0) or (
            delta_t_E(domain, esign, target, t, e) < 0 and delta_t_e(domain, esign, target, t, e) < 0)
           for t in range(target.get_number_of_states())):
        return "dcons"
    elif all((delta_t_E(domain, esign, target, t, e) > 0 and delta_t_e(domain, esign, target, t, e) < 0) or (
            delta_t_E(domain, esign, target, t, e) < 0 and delta_t_e(domain, esign, target, t, e) > 0)
            for t in range(target.get_number_of_states())):
        return "dconf"
    else:
        return "dmix"

def conflict_analysis_direction(domain, esign, target):
    dcons = []
    dconf = []
    dmix = []
    for e in esign.keys():
        if direction_of_change1(domain, esign, target, e) == "dcons":
            dcons.append(e)
        elif direction_of_change1(domain, esign, target, e) == "dconf":
            dconf.append(e)
        elif direction_of_change1(domain, esign, target, e) == "dmix":
            dmix.append(e)
        else:
            print("what the fuck 2")
    return dcons, dconf, dmix

# https://stackoverflow.com/questions/3787908/python-determine-if-all-items-of-a-list-are-the-same-item
def all_same(items):
    return all(x == items[0] for x in items)

def conflict_analysis2(domain, esign, target):
    dcons, dconf, dmix = conflict_analysis_direction(domain, esign, target)
    dominant = []
    consistent = []
    conflicting = dconf
    mixed_consistent = []
    mixed_conflicting = []

    for e in dcons:
        evidence_copy = dict(esign)
        del evidence_copy[e]
        if all(impact(domain, target, esign, e) > impact(domain, target, esign, er) for er in evidence_copy):
            dominant.append(e)
        else:
            consistent.append(e)
    for e1 in dmix:
        count_cons = 0
        count_conf = 0
        for t in range(target.get_number_of_states()):
            if direction_label(domain, esign, target, t, e1) == "dcons":
                count_cons += 1
            elif direction_label(domain, esign, target, t, e1) == "dconf":
                count_conf += 1
        if count_cons > count_conf:
            mixed_consistent.append(e1)
        else:
            mixed_conflicting.append(e1)
    return dominant, consistent, conflicting, mixed_consistent, mixed_conflicting


def level1(domain, esign, target):
    return conflict_analysis2(domain, esign, target)
