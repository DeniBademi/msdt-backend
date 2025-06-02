from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import User, UploadedModel
import jwt
from .forms import UploadFileForm
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .variable_elimination.run import Run
import os
from .get_metadata import get_metadata_for_network
from .get_metadata_bif import get_metadata_for_network_bif
from .hugin.inference import infer
from .hugin.inference import bif_to_net
from .hugin import hugin_output_parser

import subprocess
from globals import PYTHONPATH

def get_token(user: User) -> str:
    """
    Generates a JWT token for the user.
    Parameters:
    ----------
    user : User
        The user object for which the token is generated.
    Returns:
    -------
    str
        A JWT token containing the user's username and role.
    """
    return jwt.encode(dict(username=user.username, role=user.role), "secret", algorithm="HS256")

#view
def index(request):
    """
    A simple view to check if the server is running.
    Parameters:
    request : HttpRequest
        The HTTP request object.
    Returns:
    HttpResponse
        A response indicating that the server is running.
    """

    return HttpResponse("Bayesian Network Server is running.")

@csrf_exempt
def login(request):
    """
    Handles user login by verifying username and password
    Parameters:
    request : HttpRequest
        The HTTP request object containing the login credentials.
    Returns:
    JsonResponse
        A response containing the user's information and a JWT token if login is successful,
        or an error message if the credentials are invalid.
    """
    if request.method != 'POST':
        return HttpResponse("Only POST method is allowed")

    #This gathers the data: {'username': [name], 'password': [pasword]}
    json_data = json.loads(request.body)

    try:
        user = User.objects.get(username=json_data['username'])
        if not check_password(json_data['password'], user.password):
            raise User.DoesNotExist
        token = get_token(user)
        out = dict(
            username = user.username,
            user_id = user.id,
            role = user.role,
            token = token
        )

    except User.DoesNotExist:
        return JsonResponse(dict(
            error = "Invalid username or password"
        ), status=401)

    return JsonResponse(out)

@csrf_exempt
def signup(request):
    """
    Handles user signup by creating a new user with the provided username, password, and role.
    Parameters:
    request : HttpRequest
        The HTTP request object containing the signup data.
    Returns:
    JsonResponse
        A response containing the new user's information and a JWT token if signup is successful,
        or an error message if the data is invalid.
    """

    if request.method != 'POST':
        return HttpResponse("Only POST method is allowed")

    json_data = json.loads(request.body)

    role = json_data.get('role', 'user')
    if role == 'admin' and json_data.get('admin_code') != 'password_is_password':
        return JsonResponse({"error": "Invalid admin code"}, status=403)

    new_user = User(
        username = json_data['username'],
        password = make_password(json_data['password']),
        role = role
    )

    new_user.save()

    out = dict(
        username = new_user.username,
        role = new_user.role,
        token = get_token(new_user)
    )
    return JsonResponse(out)

@csrf_exempt
def get_metadata(request, network_id):
    """
    Retrieves metadata for a given network based on its ID.
    Parameters:
    request : HttpRequest
        The HTTP request object.
    network_id : str
        The ID of the network for which metadata is requested.
    Returns:
    JsonResponse
        A response containing the network's metadata, or an error message if the network is not found.
    """

    if request.method != 'GET':
        return HttpResponse("Only GET method is allowed")

    try:
        # Get the network from the database
        network = UploadedModel.objects.get(id=network_id)

        # Get the file path
        file_path = network.file.path

        if not os.path.exists(file_path):
            return JsonResponse({
                "error": "Network file not found."
            }, status=404)

        # Determine which metadata extraction function to use based on file extension
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.bif':
            metadata = get_metadata_for_network_bif(file_path)
        else:  # .net files
            metadata = get_metadata_for_network(file_path)

        return JsonResponse({
            "id": network_id,
            "name": network.name,
            "metadata": json.loads(metadata)  # Convert the JSON string to a Python dict
        })

    except UploadedModel.DoesNotExist:
        return JsonResponse({
            "error": "Network not found"
        }, status=404)
    except Exception as e:
        return JsonResponse({
            "error": f"Failed to get metadata: {str(e)}"
        }, status=500)

@csrf_exempt
def predict(request):
    """
    Handles the prediction request by running inference on a Bayesian network.
    Parameters:
    request : HttpRequest
        The HTTP request object containing the query and evidence for inference.
    Returns:
    JsonResponse
        A response containing the inference results, or an error message if the request is invalid.
    """
    if request.method != 'POST':
        return HttpResponse("Only POST method is allowed")
    try:
        json_data = json.loads(request.body)
        print(json_data)
    except json.JSONDecodeError as e:
        return JsonResponse({
            "error": "Invalid JSON format",
            "details": str(e),
            "hint": "Check for missing commas, incorrect quotes, or trailing commas"
        }, status=400)


    try:
        query = json_data.get("query")
        evidence= json_data.get("evidence",[])
        network_id = json_data.get("network")

        if not query:
            return JsonResponse("Missing 'query' variable")
        if not network_id:
            return JsonResponse("Missing 'network' name")


        # check
        print("query",query)
        print("evidence:",evidence)

        # retrieve model from database
        try:
            model_instance = UploadedModel.objects.get(id=network_id)
        except UploadedModel.DoesNotExist:
            return JsonResponse({"error": f"Network '{network_id}' not found in database"}, status=404)
        

        # what steven changed ------------------------------------------

        # Get the full file path
        file_path = model_instance.file.path
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        file_ext = os.path.splitext(file_path)[1].lower()  

        if file_ext == '.bif':
            # Convert .bif to .net
            bif_file_path = file_path
            converted_filename = os.path.splitext(os.path.basename(file_path))[0] + "_converted.net"
            folder_path = os.path.dirname(file_path)
            file_path = os.path.join(folder_path, converted_filename)
            file_name = converted_filename
            
            # Call your bif_to_net converter
            #bif_to_net(bif_file_path, converted_filename, folder_path)
        elif file_ext == '.net':
            file_path = file_path
        else:
            return JsonResponse({"error": f"Unsupported file type: {file_ext}"}, status=400)
        
        # --------------------------------------------------------


        # run inference (see example usage in inference.py for more info)
        res = subprocess.check_output([PYTHONPATH,
                                       "./bnserverappV1/hugin/inference.py",
                                       "--filename", file_name, "--path", file_path, "--targetname", query, "--evidence", json.dumps(evidence)])   # output is saved in /hugin/logs/hugin_output.log
        print(res)
        # os.system(f"py {os.path.join(os.path.dirname(__file__), 'hugin', 'inference.py')} --filename {file_name} --path {file_path} --targetname {query} --evidence {json.dumps(evidence_list)}")
        # parse hugin output: output is saved in /hugin/logs/parser_output.json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(script_dir, "hugin", "logs", "hugin_output.log")
        parsed_json_path = os.path.join(script_dir, "hugin", "logs", "parsed_output.json")
        hugin_output_parser.parse_log_file(input_path=log_path, output_path=parsed_json_path)

        # return parsed result
        with open(parsed_json_path, "r", encoding="utf-8") as f:
            parsed_result = json.load(f)

        return JsonResponse(parsed_result)

    except Exception as e:
        return JsonResponse({"error": str(e)})
    
@csrf_exempt
def predict_MPE(request):
    if request.method != 'POST':
        return HttpResponse("Only POST method is allowed")
    try:
        json_data = json.loads(request.body)
        print(json_data)
    except json.JSONDecodeError as e:
        return JsonResponse({
            "error": "Invalid JSON format",
            "details": str(e),
            "hint": "Check for missing commas, incorrect quotes, or trailing commas"
        }, status=400)


    try:
        evidence= json_data.get("evidence",[])
        network_id = json_data.get("network")

        if not network_id:
            return JsonResponse("Missing 'network' name")


        # check
        print("evidence:",evidence)

        # retrieve model from database
        try:
            model_instance = UploadedModel.objects.get(id=network_id)
        except UploadedModel.DoesNotExist:
            return JsonResponse({"error": f"Network '{network_id}' not found in database"}, status=404)

        # Get the full file path
        net_file_path = model_instance.file.path
        net_filename = os.path.splitext(os.path.basename(net_file_path))[0]

        # run inference 
        import pyAgrum as gum

        bn = gum.loadBN(net_file_path)
        ie = gum.LazyPropagation(bn)
        ie.setEvidence(evidence)
        print("test")
        MPE = ie.mpe()
        print("MPE:", MPE)
        cleaned = str(MPE).strip("<>")
        pairs = cleaned.split("|")
        MPE = dict(pair.split(":") for pair in pairs)

        return JsonResponse({
            "MPE": MPE
        })

    except Exception as e:
        return JsonResponse({"error": str(e)})

@csrf_exempt  # Use this for development (better: use Angular's CSRF handling)
def upload_model(request):
    """
    Handles the file upload for Bayesian network models.
    Parameters:
    request : HttpRequest
        The HTTP request object containing the uploaded file and optional name.
    Returns:
    JsonResponse
        A response containing the uploaded file's URL and ID, or an error message if the upload fails.
    """
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        file_path = os.path.splitext(uploaded_file.name)[1].lower()

        if file_path not in [".bif", ".net"]:
            return HttpResponse("Invalid file type. Only .bif and .net files are allowed.", status=400)

        # Get the name from the form data
        name = request.POST.get("name", "Unnamed Network")

        # Save file to database
        model_instance = UploadedModel(file=uploaded_file, name=name)
        model_instance.save()

        return JsonResponse({
            "message": "Upload successful",
            "file_url": model_instance.file.url,
            "network_id": model_instance.id,
            "name": model_instance.name
        }, status=201)

    return JsonResponse({"error": "No file uploaded"}, status=400)

@csrf_exempt
def get_networks(request):
    """
    Retrieves a list of all uploaded networks.
    Parameters:
    request : HttpRequest
        The HTTP request object.
    Returns:
    JsonResponse
        A response containing a list of networks with their IDs and names.
    """
    if request.method != 'GET':
        return HttpResponse("Only GET method is allowed")

    # Get all networks from the database
    networks = UploadedModel.objects.all()

    # Create a list of networks with their id and name
    networks_list = []
    for network in networks:
        networks_list.append({
            "id": network.id,
            "name": network.name
        })

    return JsonResponse({"networks": networks_list})
