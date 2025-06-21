from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import UploadedModel
import os
from .metadata_extractor import get_metadata_for_network
from .hugin.inference import bif_to_net
from .hugin import hugin_output_parser
from .auth import require_auth
import subprocess
from .globals import PYTHONPATH



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

        # Get metadata using the unified extractor
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
    except ValueError as e:
        return JsonResponse({
            "error": f"Unsupported file format: {str(e)}"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "error": f"Failed to get metadata: {str(e)}"
        }, status=500)

@csrf_exempt
@require_auth
def predict(request):
    """
    Perform inference on a Bayesian network.

    Endpoint: POST /predict/

    Request Body:
    {
        "network": "string",  # Network ID
        "query": "string",    # Target node name
        "evidence": {         # Dictionary of evidence nodes and their states
            "node1": state1,
            "node2": state2
        }
    }

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        JsonResponse: The inference results from the Hugin parser
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
    """
    Find the Most Probable Explanation (MPE) in a Bayesian network.

    Endpoint: POST /predict_MPE/

    Request Body:
    {
        "network": "string",  # Network ID
        "evidence": {         # Dictionary of evidence nodes and their states
            "node1": state1,
            "node2": state2
        }
    }

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        JsonResponse: On success:
            {
                "MPE": {
                    "node1": state1,
                    "node2": state2,
                    ...
                }
            }
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
        print("evidence", evidence)
        if not evidence:
            evidence = {}
            for variable in bn.names():
                dist = ie.posterior(variable)
                domain_size = bn.variable(variable).domainSize()
                best_prob = -1
                best_index = -1

                for i in range(domain_size):
                    if dist[i] > best_prob:
                        best_prob = dist[i]
                        best_index = i

                max_index = best_index
                evidence[variable] = max_index
            ie.setEvidence(evidence)
        if evidence:
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

@csrf_exempt
@require_auth
def upload_model(request):
    """
    Upload a Bayesian network model file.

    Endpoint: POST /upload_model/

    Request Body (multipart/form-data):
        file: .bif or .net file
        name: string (optional, defaults to "Unnamed Network")

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        JsonResponse: On success:
            {
                "message": "Upload successful",
                "file_url": "string",
                "network_id": int,
                "name": "string"
            }
    """
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()

        # File size validation (5MB limit)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
        if uploaded_file.size > MAX_FILE_SIZE:
            return JsonResponse({"error": "File too large. Max size is 5MB."}, status=400)

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
    """
    Get a list of all uploaded Bayesian networks.

    Endpoint: GET /networks/

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        JsonResponse: {
            "networks": [
                {
                    "id": int,
                    "name": "string"
                },
                ...
            ]
        }
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