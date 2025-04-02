from typing import Union

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

app = FastAPI()

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fullname = Column(String)
    email = Column(String)
    age = Column(Integer)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/sum")
def sum():
    a = 6
    b = 8
    sum_ = a + b
    return {"a": a, "b": b, "sum": sum_}


class Addbody(BaseModel):
    num_1: float
    num_2: float
    name: str


@app.post("/add")
def add(body: Addbody):
    sum = body.num_1 + body.num_2
    return {"sum": sum, "name": "your name is: " + body.name}


class Adduser(BaseModel):
    fullname: str
    email: str
    age: int


@app.post("/user")
def adduser(data: Adduser, db: Session = Depends(get_db)):
    user = User(fullname=data.fullname, email=data.email, age=data.age)
    db.add(user)
    db.commit()
    return {"message": f"user {data.fullname} was added"}


@app.get("/user")
def getuser(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


@app.delete("/user/{user_id}")
def deleteuser(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    db.delete(user)
    db.commit()

    return {"message": f"user {user.fullname} has been deleted"}
