from datetime import date
from typing import List, Optional, Union

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

app = FastAPI()

DATABASE_URL = "sqlite:///./library.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Books(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, auto_increment=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    published_year = Column(Integer, nullable=False)
    available = Column(Boolean, default=True)


class Members(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, auto_increment=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    joined_date = Column(Date, nullable=False)


class BorrowedBooks(Base):
    __tablename__ = "borrowed_books"
    id = Column(Integer, primary_key=True, auto_increment=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    borrow_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BookCreate(BaseModel):
    title: str
    author: str
    published_year: int
    available: bool


class MemberCreate(BaseModel):
    full_name: str
    email: str
    joined_date: date  # YYYY-MM-DD


class BorrowBook(BaseModel):
    book_id: int
    member_id: int
    borrow_date: date
    return_date: date


@app.post("/books/")
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_books = Books(
        title=book.title,
        author=book.title,
        published_year=book.published_year,
        available=book.available,
    )
    db.add(db_books)
    db.commit()
    db.refresh(db_books)
    return {"message": f" '{book.title}' by {book.author} was added"}


@app.post("/members/")
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    db_members = Members(
        full_name=member.full_name, email=member.email, joined_date=member.joined_date
    )
    db.add(db_members)
    db.commit()
    db.refresh(db_members)
    return {"message": f"Member '{member.full_name}' was added"}


@app.post("/borrowbook")
def borrow_book(borrowedbook: BorrowBook, db: Session = Depends(get_db)):
    db_borrowedbooks = BorrowedBooks(
        book_id=borrowedbook.book_id,
        member_id=borrowedbook.member_id,
        borrow_date=borrowedbook.borrow_date,
        return_date=borrowedbook.return_date,
    )
    db.add(db_borrowedbooks)
    db.commit()
    db.refresh(db_borrowedbooks)
    return {"message": f"Book: {borrowedbook.book_id} has succesfully been borrowed"}


@app.get("/availablebooks")
def available_books(db: Session = Depends(get_db)):
    borrowed_books = db.query(BorrowedBooks.book_id).all()
    borrowed_books = {id_tuple[0] for id_tuple in borrowed_books}
    availablebooks = db.query(Books).filter(Books.id.notin_(borrowed_books)).all()
    return availablebooks


@app.get("/membersborrowed")
def members_borrowed(db: Session = Depends(get_db)):
    members_borrowedID = db.query(BorrowedBooks.member_id).all()
    members_borrowedID = {idTuple[0] for idTuple in members_borrowedID}
    members_borrowed = (
        db.query(Members).filter(Members.id.in_(members_borrowedID)).all()
    )
    return members_borrowed


@app.delete(
    "/books"
)  # to delete all books that were published before the year 2000 and have never been borrowed.
def delete_books(db: Session = Depends(get_db)):
    db_Oldbook = db.query(Books).filter(Books.published_year < 2000).all()
    borrowed_books = db.query(BorrowedBooks.book_id).all()
    borrowed_books = {id_tuple[0] for id_tuple in borrowed_books}

    for book in db_Oldbook:
        if book.id not in borrowed_books:
            db.delete(book)

    db.commit()
    return db_Oldbook


@app.delete("/members/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(Members).filter(Members.id == member_id).first()
    borrow_record = (
        db.query(BorrowedBooks).filter(BorrowedBooks.member_id == member_id).first()
    )
    db.delete(borrow_record)
    db.delete(member)
    db.commit()
    return {"message": f"member {member.full_name} has been deleted"}
