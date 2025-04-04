from collections import Counter
from datetime import date
from typing import List, Optional, Union

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    create_engine,
    func,
)
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


#  An Endpoint to create a record and insert at least 5 record into each table.
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

    db_book_available = (
        db.query(Books)
        .filter(Books.id == borrowedbook.book_id, Books.available == True)
        .first()
    )
    if db_book_available is None:
        raise HTTPException(status_code=404, detail="Book not found")
    else:
        db_book_available.available = False
        db.add(db_borrowedbooks)
        db.commit()
        db.refresh(db_borrowedbooks)
    return {"message": f"Book: {borrowedbook.book_id} has succesfully been borrowed"}


# an endpoint to retrieve all books that are currently available for borrowing. change judge from the availability
@app.get("/availablebooks")
def available_books(db: Session = Depends(get_db)):
    availablebooks = db.query(Books).filter(Books.available == True).all()
    return availablebooks


# Retrieve a list of members who have borrowed at least 2 books. Add the member's ID to the output
@app.get("/membersborrowed")
def members_borrowed(db: Session = Depends(get_db)):
    members_borrowed = (
        db.query(
            BorrowedBooks.member_id, func.count(BorrowedBooks.member_id).label("count")
        )
        .group_by(BorrowedBooks.member_id)
        .having(func.count(BorrowedBooks.member_id) > 1)
        .order_by(func.count(BorrowedBooks.member_id).desc())
        .all()
    )

    members_borrowed = {id_tuple[0] for id_tuple in members_borrowed}
    borrowed_atleast2 = db.query(Members).filter(Members.id.in_(members_borrowed)).all()

    return borrowed_atleast2


#  To find the most borrowed book)
@app.get("/borrowedbooks")
def most_borrowed_books(db: Session = Depends(get_db)):
    db_borrowedbooks = db.query(BorrowedBooks.book_id).all()
    db_borrowedbooks = {id_tuple[0] for id_tuple in db_borrowedbooks}

    db_books = (
        db.query(Books.title, func.count(Books.title).label("count"))
        .filter(Books.id.in_(db_borrowedbooks))
        .group_by(Books.title)
        .order_by(func.count(Books.title).desc())
        .first()
    )

    if not db_books:
        return {"message": "No items found"}
    book_details = db.query(Books).filter(Books.title == db_books[0]).first()

    return book_details


# to delete all books that were published before the year 2000 and have never been borrowed.
@app.delete("/books")
def delete_books(db: Session = Depends(get_db)):
    db_Oldbook = db.query(Books).filter(Books.published_year < 2000).all()
    db_borrowed_books = db.query(BorrowedBooks.book_id).all()
    db_borrowed_books = {id_tuple[0] for id_tuple in db_borrowed_books}

    for book in db_Oldbook:
        if book.id not in db_borrowed_books:
            db.delete(book)

    db.commit()
    return db_Oldbook


# Delete a member but ensure all their borrowed records are also deleted to maintain referential integrity.
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
