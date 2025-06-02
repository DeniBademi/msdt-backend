from django.shortcuts import render

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .read_bayesnet import BayesNet 

from .variable_elim import VariableElimination  # Import my own var elimination class

# To do: import existing library, we have to decide whether we are using this one or another (better) one or my class
# from pgmpy.models import BayesianNetwork
# from pgmpy.inference import VariableElimination

# To do if using pgmpy: set the model to load/define a Bayesian network
# model = BayesianNetwork([('A', 'B'), ('B', 'C')]) # replace A, B, C by real variables

# If using pgmpy: create inference object (when the model has been created)
# inference = VariableElimination(model) 


# Example code to check whether Postman request can be runned (it works)
# @csrf_exempt
# def predict(request):
#     return JsonResponse({'message': 'This is a test!'})

@csrf_exempt
def predict(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            evidence = data.get('evidence')
            query = data.get('query')

            # Check if evidence and query are present
            if evidence is None or query is None:
                return JsonResponse({'error': 'Missing evidence or query'}, status=400)

            # predict result (test, dummy output)
            result = {'prediction': 'some_prediction_based_on_evidence_and_query'}

            # To do if using pgmpy: return real result that is obtained from the library's function to predict
            # result = inference.query(variables=query, evidence=evidence)

            # To do if using my class for BN: create code to read from input and run inference
            # network =  # here comes a format of the network
            # ve = VariableElimination(network)
            # heuristic = True # If True, then the heuristic is leaf nodes first. Else, the order is net.nods
            # elim_order = ve.choose_elim_order(query, heuristic)

            # Call the variable elimination function for the queried node given the evidence and the elimination ordering as follows:   
            # result = ve.run(query, evidence, elim_order)

            return JsonResponse(result)        

        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON format: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Something went wrong: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method. Only POST is allowed.'}, status=400)


def home(request):
    return HttpResponse("Welcome to the Bayesian Network API")