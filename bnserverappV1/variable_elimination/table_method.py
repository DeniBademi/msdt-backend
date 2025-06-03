import numpy as np
from .variable_elim import VariableElimination, Factor

#python -m bnserverappV1.variable_elimination.run


class TableMethod():

    def __init__(self, evidence, target, net, result):
        """
        Initializes the TableMethod class with evidence, target variable, and Bayesian network.

        Parameters:
        -----------
        evidence : dict
            A dictionary representing the evidence variables and their values.
        target : str
            The target variable for which we want to compute the posterior probability.
        net : BayesNet
            An instance of the BayesNet class representing the Bayesian network.
        """
        self.evidence = evidence
        self.target = target
        self.net = net
        self.ve = VariableElimination(net, debug=True)
        heuristic = True # If True, then the heuristic is leaf nodes first. Else, the order is net.nods
        self.elim_order = self.ve.choose_elim_order(target, heuristic)
        self.result = result


    def table_method(self):
        self.distances =  self.level_one_step_one()
        sig_evidence = self.level_one_step_two()
        conflict_information = self.level_one_step_three()
        return sig_evidence, conflict_information
        

    
    def level_one_step_one(self):
        """
        Calculates the importance of each evidence variable by measuring its influence on the posterior distribution.

        This function performs sensitivity analysis by iteratively removing one piece of evidence at a time,
        recomputing the posterior probability without it, and computing the Hellinger distance between the original
        and modified distributions.

        The higher the Hellinger distance, the more impact that piece of evidence has on the target variable's posterior.

        Returns:
        --------
        dict
            A dictionary mapping each evidence variable to its Hellinger distance, indicating how much removing
            that evidence changes the posterior.
        """
        posterior_prob = self.result
        evidences = self.evidence.copy()
        self.distances = {}
        # in this for loop we will remove one evidence at a time and calculate the posterior probability without that evidence.
        # Then we will calculate the Hellinger distance between the posterior probability with and without the evidence.
        for evidence in self.evidence:
            #remove specific evidence from the evidence list
            evidences.pop(evidence)
            posterior_prob_without_evidence = self.ve.run(self.target, evidences.copy(), self.elim_order.copy())
            # calculate the Hellinger distance between the two posterior probabilities
            distance = self.hellinger_dist(posterior_prob, posterior_prob_without_evidence)
            self.distances[evidence] = distance
            # add the evidence to the list again.
            evidences[evidence] = self.evidence[evidence]

        print(self.distances)
        return self.distances
    
    def level_one_step_two(self):
        """
        Filters evidence variables based on their impact relative to a distance threshold derived from the posterior and prior.

        This function performs the second step of the explanation algorithm:
        it compares the posterior probability of the target (given evidence)
        to the prior probability (without any evidence) and computes an intermediate
        distribution `G` using a tunable alpha value.

        A Euclidean distance between `G` and the original posterior is calculated and used
        as a threshold to filter out less influential evidence variables. Only evidence variables
        whose Hellinger distance exceeds this threshold are retained.

        Returns:
        --------
        dict
            A dictionary of filtered evidence variables whose distances are above the calculated threshold.
        """
        posterior_prob = np.array(list(self.result.copy().values()))
        print(posterior_prob)
        # Here we will get the probabilty of the target without any evidence.
        df = self.net.probabilities[self.target]
        true_probs = np.sum(df[df[self.target] == 'True']['prob'].to_numpy())
        false_probs = np.sum(df[df[self.target] == 'False']['prob'].to_numpy())
        target_prob = np.array([true_probs, false_probs])

        # Here we will pick a specific alpha value from the list of alpha values.
        Alpha = [0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.01, 0.005, 0.001]

        alpha = Alpha[4]  

        # Here we will calculate G which is in between the posterior probability and the target probability.
        G = posterior_prob - alpha * (posterior_prob - target_prob)
        # Here we will calculate the distance between G and the posterior probability.
        # This distance is used to filter the evidence variables based on their impact on the posterior distribution.
        threshold = distance = np.linalg.norm(G - posterior_prob)

        # Here we will filter the evidence variables based on the distance calculated above.
        distances = self.distances.copy()
        filtered_distances = {k: v for k, v in distances.items() if v > threshold}

        return filtered_distances

    def level_one_step_three(self):
        """
        Analyzes the influence of each evidence variable on the posterior probability by comparing directionality.

        This function assesses whether each piece of evidence is:
        - "consistent": if its impact on the posterior is in the same direction as the total evidence
        - "conflicting": if it moves the posterior in the opposite direction
        - "mixed": if its effect is not entirely aligned with either direction

        It works by:
        1. Calculating the total change caused by all evidence.
        2. Removing each evidence variable one at a time.
        3. Measuring how the absence of that variable changes the posterior.
        4. Comparing the direction of these changes.

        Returns:
        --------
        dict
            A dictionary mapping each evidence variable to a classification string:
            "consistent", "conflicting", or "mixed".
        """
        posterior_prob = self.result
        evidences = self.evidence.copy()

        # Here we will get the probabilty of the target without any evidence.
        df = self.net.probabilities[self.target]
        true_probs = np.sum(df[df[self.target] == 'True']['prob'].to_numpy())
        false_probs = np.sum(df[df[self.target] == 'False']['prob'].to_numpy())

        # Here we will calculate the impact of the total evidence on the posterior probability.
        true_impact_of_evidence = posterior_prob['True'] - true_probs
        false_impact_of_evidence = posterior_prob['False'] - false_probs


        matching_signs = {}

        for evidence in self.evidence:
            evidences.pop(evidence)
            # Here we will calculate the difference the posterior probability withe all the evidence and the posterior probability without the specific evidence.
            posterior_prob_without_evidence = self.ve.run(self.target, evidences.copy(), self.elim_order.copy())
            target_true_difference = posterior_prob['True'] - posterior_prob_without_evidence['True']
            target_false_difference = posterior_prob['False'] - posterior_prob_without_evidence['False']

            # Here we will check if the evidence is consistent, conflicting or mixed with the target variable.
            if target_true_difference * true_impact_of_evidence > 0 and target_false_difference * false_impact_of_evidence > 0:
                matching_signs[evidence] = "consistent"
            elif target_true_difference * true_impact_of_evidence < 0 and target_false_difference * false_impact_of_evidence < 0:
                matching_signs[evidence] = "conflicting"
            elif target_true_difference * true_impact_of_evidence < 0 or target_false_difference * false_impact_of_evidence < 0:
                matching_signs[evidence] = "mixed"


            evidences[evidence] = self.evidence[evidence]

        return matching_signs
    
    def hellinger_dist(self, p, q):
        """
        Computes the Hellinger distance between two discrete probability distributions.

        Parameters:
        -----------
        p : dict
            A dictionary representing the first probability distribution.
            Keys are outcome labels (e.g., 'True', 'False'), and values are probabilities.
        q : dict
            A dictionary representing the second probability distribution.
            Same format as `p`.

        Returns:
        --------
        float
            The Hellinger distance between the two distributions. This is a value between 0 and 1,
            where 0 means identical distributions and 1 means completely different.
        """
        keys = sorted(set(p) | set(q))
        p = np.array([p.get(k, 0.0) for k in keys])
        q = np.array([q.get(k, 0.0) for k in keys])
        return np.sqrt(np.sum((np.sqrt(p) - np.sqrt(q)) ** 2)) / np.sqrt(2)

            
