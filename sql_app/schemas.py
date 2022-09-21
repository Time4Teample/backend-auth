from pydantic import BaseModel


class UserBase(BaseModel):
    email: str

    class Config:
        orm_mode = True
    

class UserCreate(UserBase):
    password: str
    username : str
    
    class Config:
        orm_mode = True


class User(UserBase):
    id: int
    disabled: bool
    class Config:
        orm_mode = True