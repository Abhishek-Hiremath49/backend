from sqlalchemy import Column, Integer, String
from .database import Base

class Student(Base):
    __tablename__ = "Students List"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, unique=True, index=True)
    DoB = Column(String,index=True)
    gender= Column(String,index=True)
    course= Column(String,index=True)
    college= Column(String,index=True)