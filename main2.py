from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from starlette.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

#i modified
from sqlalchemy.orm import Session
from sql_app.database import SessionLocal , engine
from sql_app import models,schemas
from typing import List
# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#depend on database
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

app = FastAPI()

@app.get("/")
def main():
    return RedirectResponse(url="/docs/")

# i need to delete this 
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}

## NOT STABLE CODE
@app.get('/users/', response_model=List[schemas.User])
def show_users(db: Session=Depends(get_db)):
    users = db.query(models.User).all( )
    return users

@app.post('/users/', response_model=schemas.User)
def create_users(enter: schemas.User, db: Session=Depends(get_db)):
    user = models.User(username = enter.username, fullname=enter.fullname, 
                             email=enter.email, hashed_password=enter.hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.put('/users/{user_id}', response_model=schemas.User)
def update_users(user_id: int, enter: schemas.UserUpdate, db: Session=Depends(get_db)):
    user = db.query(models.User).filter_by(id=user_id).first( )
    user.fullname=enter.fullname
    db.commit()
    db.refresh(user)
    return user

@app.delete('/users/{user_id}', response_model=schemas.response)
def delete_users(user_id: int, db: Session=Depends(get_db)):
    user = db.query(models.User).filter_by(id=user_id).first( )
    db.delete(user)
    db.commit()
    response = schemas.response(message="Successfully removed!")
    return response

## HERE IS PROTOTYPE 





class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db : SessionLocal , username: str):
    if username in  db.query(models.User).filter_by(id=id).first( ):
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db : Session , username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": "Foo", "owner": current_user.username}]