from pydantic import BaseModel, EmailStr, Field

class student(BaseModel):
    name: str
    email: EmailStr
    phone: str = Field(...,pattern=r'^\+91\d{1,12}$',description="with country code")
    DoB: str = Field(...,pattern=r'^\d{4}-\d{2}-\d{2}$',description="YYYY-MM-DD format")
    gender: str = Field(...,pattern="^(Male|Female|Other)$")
    course: str 
    college: str
    