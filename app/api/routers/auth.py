"""
Authentication Routers
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm

from app.api.schemas import UserCreate, UserResponse, Token
from app.services.user_service import UserService
from app.utils.jwt import verify_email_verification_token, verify_password_reset_token, create_password_reset_token
from app.utils.mail import send_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
        user_service: UserService = Depends(),
):
    """Register a new user and send a verification email."""
    existing_user = user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    new_user = await user_service.create_user_with_verification(
        email=user_data.email, password=user_data.password, background_tasks=background_tasks
    )
    return UserResponse(id=new_user.id, is_active=new_user.is_active, email=new_user.email,
                        is_verified=new_user.is_verified)



@router.post("/login", response_model=Token, status_code=201)
def login_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        user_service: UserService = Depends(),
):
    """Authenticate the user and return an access token."""
    user = user_service.get_user_by_email(form_data.username)
    if not user or not user_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = user_service.generate_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/verify-email", status_code=200)
def verify_email(
        token: str,
        user_service: UserService = Depends(),
):
    """Verify user's email address using the provided token."""
    email = verify_email_verification_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        return {"message": "User is already verified"}

    user_service.verify_user_email(user)
    return {"message": "Email verified successfully"}


@router.post("/send-verification-email", status_code=201)
async def resend_verification_email(
        email: str,
        background_tasks: BackgroundTasks,
        user_service: UserService = Depends(),
):
    """Resend the verification email if the user is not yet verified."""
    user = user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="User is already verified")

    await user_service.resend_verification_email(user, background_tasks)
    return {"message": "Verification email sent successfully"}

@router.post("/request-password-reset")
async def request_password_reset(email: str, background_tasks: BackgroundTasks, user_service: UserService = Depends()):
    user = user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = create_password_reset_token(user.email)
    await send_reset_email(user.email, reset_token, background_tasks)
    return {"message": "Password reset email sent."}

@router.post("/reset-password")
def reset_password(token: str, new_password: str, user_service: UserService = Depends()):
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_service.update_password(user, new_password)
    return {"message": "Password reset successfully"}
