from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .. import models
from ..database import get_db
from ..auth import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["用户认证"])


class UserCreate(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已被注册")

    hashed_pwd = get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": "注册成功"}


@router.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    access_token = create_access_token(data={"sub": db_user.username})
    return {"status": "success", "access_token": access_token, "token_type": "bearer"}