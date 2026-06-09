# Authentication routes for admin login
# Provides endpoint to validate admin credentials

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from admin_database import validate_admin_credentials
from logger_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    """Request body for admin login"""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Response body for successful login"""
    success: bool
    message: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Validate admin credentials
    
    Endpoint: POST /login
    
    Args:
        request: LoginRequest with email and password
        
    Returns:
        LoginResponse with success status
        
    Raises:
        HTTPException with 401 status if credentials are invalid
    """
    # Validate credentials against admin database
    if not validate_admin_credentials(request.email, request.password):
        logger.warning(f"Failed login attempt for email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    logger.info(f"Successful login for email: {request.email}")
    return LoginResponse(
        success=True,
        message="Login successful"
    )
