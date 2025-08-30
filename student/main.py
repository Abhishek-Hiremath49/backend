from fastapi import FastAPI, Depends, status, HTTPException #, Response
from . import schemas, models
from .database import engine, SessionLocal
from sqlalchemy.orm import Session

app = FastAPI()

models.Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["Student_Dashboard"])
def read_Student_Dashboard():
    return 'Message: Welcome to the Student API!'

@app.post("/Student", tags=["Student_Dashboard"], status_code=status.HTTP_201_CREATED)
def create_student(request: schemas.student, db:Session = Depends(get_db)):
    new_student = models.Student(
        name=request.name,
        email=request.email,
        phone=request.phone,
        DoB=request.DoB,
        gender=request.gender,
        course=request.course,
        college=request.college
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

@app.get("/Student",tags=["Student_Dashboard"])
def get_all_students(db:Session = Depends(get_db)):
    students = db.query(models.Student).all()
    return students

@app.get("/Student/{student_id}",tags=["Student_Dashboard"], status_code=status.HTTP_200_OK )
def get_student(student_id:int, db:Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with the id {student_id} is not available")
        # response.status_code = status.HTTP_404_NOT_FOUND
        # return {"Message": f"Student with the id {student_id} is not available"}
    return student

@app.put("/student/{student_id}",tags=["Student_Dashboard"], status_code=status.HTTP_202_ACCEPTED)
def update_student(student_id:int, request:schemas.student,db:Session=Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id)
    if not student.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with the id {student_id} is not available")
    student.update({
        models.Student.name: request.name,
        models.Student.email: request.email,
        models.Student.phone: request.phone,
        models.Student.DoB: request.DoB,
        models.Student.course: request.course,
        models.Student.college: request.college,
        models.Student.gender: request.gender
    })
    db.commit()
    return f"Student with the id {student_id} is updated successfully"

@app.delete("/Student/{student_id}",tags=["Student_Dashboard"], status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id:int, db:Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id)
    if not student.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with the id {student_id} is not available")
    student.delete(synchronize_session=False)
    db.commit()
    return {"Message": "Deleted Successfully"}
