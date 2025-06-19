from functools import wraps
from django.http import JsonResponse
import jwt
from .models import User
from datetime import datetime, timedelta, timezone

def get_token(user: User) -> str:
    """
    Generate a JWT token for the given user.

    Args:
        user (User): The user object containing username, role and id

    Returns:
        str: A JWT token encoded with the user's information
    """
    return jwt.encode(dict(
        username=user.username,
        role=user.role,
        exp=datetime.now(tz=timezone.utc) + timedelta(days=7),
        user_id=user.id), "secret", algorithm="HS256")

def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token (str): The JWT token to decode

    Returns:
        dict: The decoded token payload if valid, None if invalid
    """
    try:
        return jwt.decode(token, "secret", algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
    except jwt.ExpiredSignatureError:
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
    """
    Verify if a token belongs to an admin user.

    Args:
        token (str): The JWT token to verify

    Returns:
        bool: True if the token is valid and belongs to an admin, False otherwise
    """
    decoded_token = decode_token(token)
    user_id = decoded_token.get('user_id')
    role = decoded_token.get('role')
    if not user_id:
        return False
    if role != 'admin':
        return False
    return True


