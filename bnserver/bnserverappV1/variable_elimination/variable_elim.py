# Student: Soz Raheem
# Student number: s1096881
# Course: Artificial Intelligence Principles & Techniques
# Assignment 3
# 20-12-2024

"""
@Author: Joris van Vugt, Moira Berens, Leonieke van den Bulk (original authors)
Modified by Soz Raheem

Class for the implementation of the variable elimination algorithm.

"""

import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler("log.txt", mode='w'), # Write logs to log.txt 
        logging.StreamHandler() # Also print Logs to console
    ]
)
logger = logging.getLogger("VariableElimination")


class Factor():
    """
    This class represents a factor in the variable elimination algorithm

    """

    # Static variable to keep track of Factor numbers
    count = 0 

    def __init__(self, variables, table, product = False):
        """
        Construct a Factor  from a list of variables and a probablility table
        """
        # List of variables (in the form of a String) 
        self.variables = variables

        # Probablility distribution table
        self.table = table 

        # After multiplying factors in the function "multiply()", we obtain a new factor.
        # But this new factor is not finished, as has not gone through the marginalization yet
        # Therefore, we don't want to increase the index number in that case
        if (product):
            self.index = Factor.count

        # For all other cases where we create a new factor, we increase the index number    
        else:
            self.index = Factor.count

            # Update the static variable for future factors
            Factor.count += 1

        # Write to the log file everytime a new factor is created
        logger.debug(f"Created factor {self.index}: \n {self.table} \n")    


    def __str__(self):
        """
        Dunder method to return the factor as a String, e.g. f0: (Burglary)

        """
        variables_to_string = ""
        length = len(self.variables)

        # In case the factor has no variables
        if length <1: 
            variables_to_string += "NONE"

        else:
            variables_to_string += self.variables[0]

            # If it contains more than 1 variable, then add the variables together with a , in between
            if (length >1): 
                for var in self.variables[1:]:
                    variables_to_string +=  ", " + var

        string = f"f{self.index}: ({variables_to_string})"   #e.g. f0: (Burglary)
        return string


    def reduce(self, var, val):
        """
        Reduce the current factor by removing the observed value

        Input:
            var:    The observed variable
            val:    The value of the observed variable

        Output: A new Factor after selecting the rows of the observed value and removing the rest

        """

        # In case the factor only contains one variable, just remove that variable from its list 
        if len(self.variables)==1:
            self.variables.remove(var)
            return self
        
        else:
            # Copy the table of the current factor and reduce it on the observed variable
            table = self.table[self.table[var] == val]
            table = table.drop(columns=[var])

            # Copy the variables that are supposed to be kept
            variables = [v for v in self.variables if v != var]

            # Write an update to the log.txt file
            logger.debug(f"Reducing factor {self.index} on {var} = {val}")
            
            return Factor(variables,table)
        

    def product(self, other_factor):
        """
        Applying the product method to two factors

        Input:
            self:           This factor
            other_factor:   Other factor

        Output: A new factor obtained after multipliying two factors. This new factor is not
                finished yet. It has to go through marganilization first.

        """

        # Collecting the variables that are in common and will therefore be multiplied
        common_variables = list(set(self.variables) & set(other_factor.variables))

        # In case there are no common variables, raise an error
        if not common_variables:
            raise ValueError(
                f"Cannot combine factors: no common variables between {self.variables} and {other_factor.variables}."
            )

        # Updating the log.txt file
        logger.debug(f"Multiplying factor {self.index} with factor {other_factor.index}")
        
        # Merge the two tables on the common variables
        merged_table = pd.merge(
            self.table,
            other_factor.table,
            on=common_variables,
            suffixes=('_x', '_y')
        )

        # Compute the product of probabilities
        merged_table['prob'] = merged_table['prob_x'] * merged_table['prob_y']

        # Drop old probability columns
        merged_table = merged_table.drop(columns=['prob_x', 'prob_y'])
        
        # Collect all the variables for the new factor
        all_variables = list(set(self.variables + other_factor.variables))

        # Return a new factor
        return Factor(all_variables, merged_table, product=True)


    def marginalize(self, var_to_eliminate):
        """
        Applying marginalization to the current factor

        Input:
            self:               This factor
            var_to_eliminate:   The variable we are marginalizing over

        Output: A new factor obtained after marginalization

        """

        # Check if the variable to marginalize over is actually in the list of variables
        if var_to_eliminate not in self.variables:
            raise ValueError(f"Variable {var_to_eliminate} not in factor: {self.variables}")

        # Update the log.txt file
        logger.debug(f"Marginalizing Factor {self.index} on {var_to_eliminate}")
        
        # Group the remaining variables by summing over the target
        remaining_vars = [v for v in self.variables if v != var_to_eliminate]
        marginalized_table = (
            self.table.groupby(remaining_vars, as_index=False)['prob'].sum()
        )

        # Create a new factor with the updated table
        return Factor(remaining_vars, marginalized_table)


class VariableElimination():

    def __init__(self, network, debug=False):
        """
        Initialize the variable elimination algorithm with the specified network.
        Add more initializations if necessary.

        Input:
            network:    An instance of the class Bayesnet, containing the Bayesian network
            debug:      The degree to which details are used in the log.txt file

        """

        self.network = network
        self.factor_list = []

        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)


    def create_factor_list(self):
        """
        Creating a list of factors to deal with in the ve algorithm

        Output: A list of factors

        """

        # Creating the factors
        factor_index = 0

        # For every variable retrieve its parents if they have any, and create a factor
        for variable in self.network.parents:
            logger.debug(f"\nCreating factor {factor_index} for variable: {variable}...")
            parents = self.network.parents.get(variable)
            if not parents:
                logger.debug(f"Variable {variable} has no parents")
                factor = Factor([variable], self.network.probabilities.get(variable))
            else:
                logger.debug(f"Variable {variable} has parents: {parents}")
                list_of_variables = [variable] + parents
                factor = Factor(list_of_variables, self.network.probabilities.get(variable))  
            self.factor_list.append(factor)
            factor_index+=1


    def str(self, factor_list):
        """
        Returning a String instance of the factor list
        """

        string = "\n Factor List:"
        for f in factor_list:
            string += "\n" + str(f) 
        return string+"\n"    
    

    def reduce_observed(self, observed):
        """
        Reduce factors by observed variables.

        Input: 
            observed: Dictionary with the variable as the key and the observed value as its item/value
        """

        logger.info("Reducing factors based on observed variables...")
        logger.debug(f"Observed variables: {observed}")

        for obs in observed:
            obs_var = obs
            obs_value = observed.get(obs)

            # A removal list to keep track of what factors to remove (to prevent errors when iterating over a list and removing items at the same time)
            factors_to_remove = []
            add_list = []

            # Iterate over evey factor in our list to check for the observed variable
            for f in self.factor_list:
                if obs_var in f.variables:

                    logger.debug(f"Factor {f} contains this observed variable.")

                    # Create a new reduced factor and add the old factor to the removal list
                    reduced_factor = f.reduce(obs_var, obs_value)   
                    factors_to_remove.append(f)

                    # If the reduced factor still has variables, add it to the factor list
                    if reduced_factor.variables:
                        add_list.append(reduced_factor)
                        logger.debug(f"Added factor {reduced_factor} to the factor list")

                    # Otherwise just remove the factor
                    else:
                        logger.debug(f"Factor f{f.index} is empty now and will be removed")
        

            # Removing the old factors by iterating over the removal list
            for f in factors_to_remove:
                self.factor_list.remove(f)

            # Adding the new factors
            for a in add_list:
                # Only if the factor is not empty, add it to the factor list
                if not "NONE" in a.variables: 
                    self.factor_list.append(a)   

        # Update the log.txt file
        logger.debug(f"Updated factor list after reduction: {self.str(self.factor_list)}")             


    def eliminate_variable(self, variable):
        """
        Eliminate a variable by combining relevant factors and marginalizing
        """

        # Collecting the relevant factors that contain this variable
        relevant_factors = [f for f in self.factor_list if variable in f.variables]

        if not relevant_factors:
            logger.warning(f"No factors found containing variable {variable}")
            return
        

        # Combine factors using product
        new_factor = []

        # Start with the first factor to either combine or marginalize (in case there is only 1 factor)
        if relevant_factors:
            combined_factor = relevant_factors[0]

        # Check if there are multiple factors to combine
        if(len(relevant_factors)>1):

            # Iterate over all other relevant factors and combine it with the current combined_factor
            for f in relevant_factors[1:]:
                logger.debug(f"Combining factors: {combined_factor} and {f}")
                combined_factor = combined_factor.product(f)

        # Check if there are variables left after eliminating the current variable (for which then marginalization is needed)
        if (len(combined_factor.variables)>1):
            # Marginalize the variable from combined_factor
            new_factor = combined_factor.marginalize(variable)

        # A removal list (to prevent errors that occur when iterating over a list and removing items at the same time)
        factors_to_remove = [f for f in self.factor_list if f in relevant_factors]
        
        # Removing the old factors
        for f in factors_to_remove:
            self.factor_list.remove(f)
            logger.debug(f"Removed factor {f} from the list")

        # Add the new factor to the factor list
        if new_factor:
            self.factor_list.append(new_factor)
            logger.debug(f"Added new factor {new_factor}")
    
        logger.debug(f"\nUpdated factor list: {self.str(self.factor_list)}")    


    def normalize_result(self):
        """
        Normalize the final result, i.e., make sure the probabilities add up to 1.
        """

        logger.debug("Now as a final step: Normalization")

        # Check if the factor list contains 0, 1, or multiple factors
        length = len(self.factor_list)

        if length == 0:
            logger.warning("Something went wrong... There is no factor left...")
            return None
        
        elif length == 1:
            new_factor = self.factor_list[0]

        else:
            # Combine the final factors
            combined_factor = self.factor_list[0]

            for f in self.factor_list[1:]:
                combined_factor = combined_factor.product(f)
                logger.debug(f"Adding {combined_factor}") 
                self.factor_list.append(combined_factor)

            new_factor = Factor(combined_factor.variables, combined_factor.table)

        # Normalizing the final factor: making sure the probabilities add up to 1
        total_prob = new_factor.table['prob'].sum()
        if total_prob != 0:
            new_factor.table['prob'] = new_factor.table['prob'] / total_prob
        else:
            logger.warning("Error: Total probability sums to 0, cannot normalize.")

        return new_factor
    

    def create_parent_list(self):
        """
        Creating a list of 

        Input:
            self:           This factor
            other_factor:   Other factor

        Output: A new factor obtained after multipliying two factors. This new factor is not
                finished yet. It has to go through marganilization first.

        """
        # Creating the a list that contains the parent nodes
        parent_list = [] 
        
        for variable in self.network.parents:
            parents = self.network.parents.get(variable)
            if not parents:
                pass
            else: 
                for element in parents:
                    parent_list.append(element)


        return parent_list
    
           
    def choose_elim_order(self, query, heuristic):
        """
        Prioritize elimination order with either leaf nodes first or no heuristic

        Input:
            heuristic: Boolean value. If true, determine elimination order with leaf nodes first. Else, no heuristic is used.
        """
        if heuristic:
            parent_list = self.create_parent_list()
            leaf_nodes = [v for v in self.network.nodes if v not in parent_list and v != query]
            non_leaf_nodes = [v for v in self.network.nodes if v in parent_list and v != query]
            elim_order = leaf_nodes + non_leaf_nodes
        else:
            elim_order = [v for v in self.network.nodes if v != query]
        return elim_order


    def run(self, query, observed, elim_order):
        """
        Use the variable elimination algorithm to find out the probability
        distribution of the query variable given the observed variables

        Input:
            query:      The query variable
            observed:   A dictionary of the observed variables {variable: value}
            elim_order: Either a list specifying the elimination ordering
                        or a function that will determine an elimination ordering
                        given the network during the run

        Output: A variable holding the probability distribution
                for the query variable

        """


        self.create_factor_list()
        self.reduce_observed(observed)

        for o in observed:
            elim_order.remove(o)
        
        for element in elim_order:
            self.eliminate_variable(element) 

        result_factor = self.normalize_result() 

        if result_factor is None:
            return None

        #query_distribution = result_factor.table
        result = result_factor.table.set_index(query)['prob'].to_dict()
        return result

    # Old run function from assignment AIPT
        # def run(self, query, observed, elim_order):
        # """
        # Use the variable elimination algorithm to find out the probability
        # distribution of the query variable given the observed variables

        # Input:
        #     query:      The query variable
        #     observed:   A dictionary of the observed variables {variable: value}
        #     elim_order: Either a list specifying the elimination ordering
        #                 or a function that will determine an elimination ordering
        #                 given the network during the run

        # Output: A variable holding the probability distribution
        #         for the query variable

        # """
        # logger.info(f"========== Initializing Factors ==========\n")

        # logger.info(f"Query variable: {query}")
        # logger.info(f"Observed variable: {observed}")
        # logger.info(f"Elim order before removing observed variable: {elim_order} ")
        # logger.info(f"Creating factors now... \n")

        # self.create_factor_list()
        # logger.info(f"We start with factors: {self.str(self.factor_list)}")

        # logger.info(f"========== Reducing factors on observed variable ==========\n")
        # self.reduce_observed(observed)
        # logger.info(f"Elim order before removal: {elim_order}")
        # logger.info(f"observed: {observed}")

        # for o in observed:
        #     elim_order.remove(o)
        
        # logger.info(f"Elim order after removal: {elim_order} ")

        # logger.info(f"\n\n========== Start Variable Elimination ==========\n")
        # logger.info(f"We now have factors: {self.str(self.factor_list)}")
        # logger.info(f"Variable elimination order: {elim_order}")  

        # for element in elim_order:
        #     logger.info(f"\nEliminating variable {element}\n-------------------------------------------------------------------------")
        #     self.eliminate_variable(element) 

        # result_factor = self.normalize_result() 
        # query_distribution = result_factor.table
        # logger.info(f"\n\n========== Solution ==========\n")

        # logger.info(f"Final probablity distribution of {query}: \n{query_distribution}")

 