import os
from ...commons import (
    max_difference
)
from .level_1 import esig, level1
from .level_2 import level2, markov_blanket
from .level_3 import level3


def table(domain, target, evidence, dummy):
    # original function starts here
    print("domain:",domain)
    esign = esig(domain, target, evidence, dummy)
    print("esign:",esign)
    dominant, consistent, conflicting, mixed_consistent, mixed_conflicting = level1(domain, esign, target)
    XI = markov_blanket(domain, target, evidence, esign, dummy)
    lvl2_og, lvl2_new = level2(domain, evidence, esign, XI)
    lvl3 = level3(domain, esign, XI, dummy)
    #setup_evidence(domain,target,evidence)
    print("Level 1")
    print("------------------------------------------------------------------------------")
    # print("The chance of", target.get_label(), "being", target.get_state_label(0) ,"=", target.get_belief(0))
    domain.propagate()
    print("The chance of", target.get_label(), "being", target.get_state_label(1), "=", target.get_belief(1))
    print("------------------------------------------------------------------------------")
    print("What are the factors that support above prediction of", target.get_label() + "?")

    for i in dominant:
        print(i.get_label(), "=", i.get_state_label(evidence[i]), "(Very important)")
    for i in consistent:
        print(i.get_label(), "=", i.get_state_label(evidence[i]))

    if len(mixed_consistent) != 0:
        print("Partially supporting:")
    for i in mixed_consistent:
        print(i.get_label(), "=", i.get_state_label(evidence[i]))
    if len(dominant) == 0 and len(consistent) == 0 and len(mixed_consistent) == 0:
        print("None")

    print("------------------------------------------------------------------------------")
    print("What are the factors that do not support above prediction of", target.get_label() + "?")
    for i in conflicting:
        print(i.get_label(), "=", i.get_state_label(evidence[i]))
    if len(mixed_conflicting) != 0:
        print("Partially contradicting:")
    for i in mixed_conflicting:
        print(i.get_label(), "=", i.get_state_label(evidence[i]))
    if len(conflicting) == 0 and len(mixed_conflicting) == 0:
        print("None")
    print("------------------------------------------------------------------------------")
    print("Level 2")
    print("------------------------------------------------------------------------------")
    print("How does the model utilize the above factors to predict",
        target.get_label() + "? \nAs the immediate causes of ", target.get_label(), "the model uses:")
    for i in lvl2_og:
        diff, index = max_difference(lvl2_og[i], lvl2_new[i])
        print(i.get_label(), ": ", diff, "% increase in", i.get_state_label(index))
    print("------------------------------------------------------------------------------")
    print("Level 3")
    print("------------------------------------------------------------------------------")
    for node in lvl3:
        print("What are the factors that support above prediction of", node.get_label() + "?")
        for i in lvl3[node][0][0]:
            print(i.get_label(), "=", i.get_state_label(evidence[i]))
        for i in lvl3[node][0][1]:
            print(i.get_label(), "=", i.get_state_label(evidence[i]))
        if len(lvl3[node][0][3]) != 0:
            print("Partially supporting:")
            for i in lvl3[node][0][3]:
                print(i.get_label(), "=", i.get_state_label(evidence[i]))
        if len(lvl3[node][0][0]) == 0 and len(lvl3[node][0][1]) == 0 and len(lvl3[node][0][3]) == 0:
            print("None")
        print("------------------------------------------------------------------------------")
        print("What are the factors that do not support above prediction of", node.get_label() + "?")
        if len(lvl3[node][0][2]) != 0:
            for i in lvl3[node][0][2]:
                print(i.get_label(), "=", i.get_state_label(evidence[i]))
        if len(lvl3[node][0][4]) != 0:
            print("Partially contradicting:")
            for i in lvl3[node][0][4]:
                print(i.get_label(), "=", i.get_state_label(evidence[i]))
        if len(lvl3[node][0][2]) == 0 and len(lvl3[node][0][4]) == 0:
            print("None")
        print("------------------------------------------------------------------------------")