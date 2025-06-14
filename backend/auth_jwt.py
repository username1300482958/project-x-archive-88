from fastapi import APIRouter, Request, HTTPException
from .auth_jwt_utils import create_access_token
import requests
import os

router = APIRouter()

@router.post("/auth/google/jwt-login")
async def google_jwt_login(request: Request):
    body = await request.json()
    access_token = body.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="access_token is required")

    try:
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        user_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid Google token")

        token = create_access_token({"sub": user_id, "email": email, "name": name})

        return {"access_token": token, "token_type": "bearer", "user_id": user_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
