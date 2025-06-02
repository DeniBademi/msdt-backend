from ...commons import (
    get_dseparated_nodes,
    P
)

def markov_blanket(domain, target, evidence, esign, dummy):
    """
        Determines the markov blanket of the target, removing the D separated nodes with the significant evidence
        Args:
            domain: Domain
            target: Node
            evidence: dictionary
            esign: dictionary
        Returns:
            List: The markov blanket of the target
    """
    XI = []
    for parents in target.get_parents():
        XI.append(parents)
    for children in target.get_children():
        XI.append(children)
        for family in children.get_parents():
            XI.append(family)
    dseperated = get_dseparated_nodes(domain, target, esign, dummy)

    XI = list(set(XI))
    #remove the dseperated nodes, because they don't influence the probability of the target.
    for i in dseperated:
        #print(i.get_name(), "TEST")
        if i in XI:
            XI.remove(i)

    if target in XI:
        print("LOL")
        XI.remove(target)

    return XI

def level2(domain, evidence, esign, XI):
    """
        Determines the change of all markov blanket variables after the evidence
    """
    level2_og = {}
    level2_current = {}
    for i in XI:
        level2_og[i] = P(domain, i)
        level2_current[i] = P(domain, i, esign)
    return level2_og, level2_current
