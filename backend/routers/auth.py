from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import SalesRep
from schemas import LoginRequest, LoginResponse
from auth import verify_password, create_access_token

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    rep = db.query(SalesRep).filter(SalesRep.username == body.username).first()
    if not rep or not verify_password(body.password, rep.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": rep.id})
    return LoginResponse(access_token=token, rep_name=rep.name, rep_id=rep.id)
