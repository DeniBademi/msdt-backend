from ...commons import (
    remove_dseparated,
)
from .level_1 import conflict_analysis2

def level3(domain, esign, XI, dummy):
    """
        Performs the conflict analysis from level 1 on the markov blanket
        Args:
            domain: Domain
            esign: dictionary
            XI: List
        Returns:
            Dictionary: The conflict analysis from level 1 on the markov blanket
    """
    level3 = {}
    for i in XI:
        evidence = remove_dseparated(domain, i, esign, dummy)
        level3[i] = [conflict_analysis2(domain, evidence, i)]
    return level3