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
from .hugin.inference import infer, bif_to_net
from .hugin import hugin_output_parser
from .auth import require_auth, get_token, decode_token
import subprocess
from globals import PYTHONPATH




#view
def index(request):
    return HttpResponse("Bayesian Network Server is running.")

@csrf_exempt
def login(request):
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
    if request.method != 'POST':
        return HttpResponse("Only POST method is allowed")

    json_data = json.loads(request.body)

    new_user = User(
        username = json_data['username'],
        password = make_password(json_data['password']),
        role = "user"
    )

    new_user.save()

    out = dict(
        username = new_user.username,
        role = new_user.role,
        token = get_token(new_user)
    )
    return JsonResponse(out)

@csrf_exempt
@require_auth
def get_metadata(request, network_id):
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
@require_auth
def predict(request):
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
            bif_to_net(bif_file_path, converted_filename, folder_path)
        elif file_ext == '.net':
            file_path = file_path
        else:
            return JsonResponse({"error": f"Unsupported file type: {file_ext}"}, status=400)

        # --------------------------------------------------------

        # run inference (see example usage in inference.py for more info)
        res = resolve_inference_call(file_name, file_path, query, evidence)
        print(res)
        # os.system(f"py {os.path.join(os.path.dirname(__file__), 'hugin', 'inference.py')} --filename {net_filename} --path {net_file_path} --targetname {query} --evidence {json.dumps(evidence_list)}")
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
@require_auth
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
        try:
            import pyAgrum as gum
        except ImportError:
            try:
                import pyagrum as gum
            except ImportError:
                return JsonResponse({"error": "pyAgrum or pyagrum is not installed. Please install it using 'pip install pyAgrum' or 'pip install pyagrum'."}, status=500)

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
@require_auth
def upload_model(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()

        if file_ext not in [".bif", ".net"]:
            return HttpResponse("Invalid file type. Only .bif and .net files are allowed.", status=400)

        # Get the name from the form data
        name = request.POST.get("name", "Unnamed Network")

        if file_ext == '.bif':
            # Convert .bif to .net
            bif_file_path = uploaded_file.name
            converted_filename = os.path.splitext(os.path.basename(uploaded_file.name))[0] + "_converted.net"
            folder_path = os.path.dirname(uploaded_file.name)
            file_path = os.path.join(folder_path, converted_filename)
            file_name = converted_filename

            # Call your bif_to_net converter
            bif_to_net(bif_file_path, converted_filename, folder_path)
            uploaded_file = file_path

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
@require_auth
def get_networks(request):
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


def resolve_inference_call(net_filename, net_file_path, query, evidence):
    print("PYTHONPATH", PYTHONPATH)
    python_call = PYTHONPATH
    path_to_inference = "./bnserverappV1/hugin/inference.py"
    args = ["--filename", net_filename, "--path", net_file_path, "--targetname", query, "--evidence", json.dumps(evidence)]
    print(args)
    try:
        res = subprocess.check_output([python_call, path_to_inference] + args)
    except Exception as e:
        if str(e) == f"[Errno 2] No such file or directory: '{python_call}'":
            # cannot find python
            python_call = "python"
            path_to_inference = "/app/bnserverappV1/hugin/inference.py"
            res = subprocess.check_output([python_call, path_to_inference] + args)
            print("res", res)
        else:
            print(str(e))
            raise e
    return res