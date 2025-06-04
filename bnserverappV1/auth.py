from functools import wraps
from django.http import JsonResponse
import jwt
from .models import User

def get_token(user: User) -> str:
    return jwt.encode(dict(username=user.username, role=user.role, user_id=user.id), "secret", algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, "secret", algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None

def get_user_info(request):
    """Retrieves user information from the request headers.

    Args:
        request (Request): The HTTP request object.

    Returns:
        tuple: A tuple containing the user ID and role.
    """
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, None

    token = auth_header.split(' ')[1]
    decoded_token = decode_token(token)
    user_id = None
    if decoded_token:
        user_id = decoded_token.get('user_id')
        role = decoded_token.get('role')
    return user_id, role

def require_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user_id, role = get_user_info(request)
        if not user_id:
            return JsonResponse({"error": "Invalid token: missing user_id"}, status=401)

        request.user_id = user_id
        request.user_role = role

        return view_func(request, *args, **kwargs)
    return wrapper

def require_admin(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get token from Authorization header
        user_id, role = get_user_info(request)
        if not user_id:
            return JsonResponse({"error": "Invalid token: missing user_id"}, status=401)

        if role != 'admin':
            return JsonResponse({"error": "Admin privileges required"}, status=403)

        request.user_id = user_id
        request.user_role = role

        return view_func(request, *args, **kwargs)
    return wrapper

def require_admin_token(token: str):
    decoded_token = decode_token(token)
    user_id = decoded_token.get('user_id')
    role = decoded_token.get('role')
    if not user_id:
        return False
    if role != 'admin':
        return False
    return True


