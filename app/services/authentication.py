"""
Authentication Utilities.

This module provides authentication functionality, including user authentication and role validation.
"""
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.repository.models import User, UserRole
from app.services.user_service import UserService
from app.utils.jwt import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), user_service: UserService = Depends()):
    """
    Get the current user from the token.

    Args:
        token (str, optional): The authentication token. Defaults to Depends(oauth2_scheme).
        user_service (UserService, optional): The user service. Defaults to Depends().

    Raises:
        HTTPException: If the token is invalid or expired.

    Returns:
        User: The current user.
    """
    email = verify_access_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = user_service.get_user_by_email(email=email)
    if not user or not user.is_verified:
        raise HTTPException(status_code=403, detail="User is not verified")
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """
    Get the current admin user.

    Args:
        current_user (User, optional): The current user. Defaults to Depends(get_current_user).

    Raises:
        HTTPException: If the current user is not an admin.

    Returns:
        User: The current admin user.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied: Admins only")
    return current_user
