from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from bnserverappV1.models import User
from bnserverappV1.auth import get_token, require_auth
from django.contrib.auth.hashers import check_password, make_password



def index(request):
    """
    Health check endpoint to verify the server is running.

    Returns:
        HttpResponse: A simple text message indicating the server is running
    """
    return HttpResponse("Bayesian Network Server is running.")

@csrf_exempt
def login(request):
    """
    Authenticate a user and return a JWT token.

    Endpoint: POST /login/

    Request Body:
    {
        "username": "string",
        "password": "string"
    }

    Returns:
        JsonResponse: On success:
            {
                "username": "string",
                "user_id": int,
                "role": "string",
                "token": "string"
            }
        On failure:
            {
                "error": "Invalid username or password"
            }
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
    Register a new user.

    Endpoint: POST /signup/

    Request Body:
    {
        "username": "string",
        "password": "string"
    }

    Returns:
        JsonResponse: On success:
            {
                "username": "string",
                "role": "string",
                "token": "string"
            }
    """
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
def change_password(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        json_data = json.loads(request.body)
        current_password = json_data.get('current_password')
        new_password = json_data.get('new_password')

        if not current_password or not new_password:
            return JsonResponse({"error": "Both current and new password are required"}, status=400)

        # Get user from database
        user = User.objects.get(id=request.user_id)

        # Verify current password
        if not check_password(current_password, user.password):
            return JsonResponse({"error": "Current password is incorrect"}, status=401)

        # Update password
        user.password = make_password(new_password)
        user.save()

        return JsonResponse({"message": "Password changed successfully"})

    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)