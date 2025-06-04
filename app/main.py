# app/main.py
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import shutil

app = FastAPI()

# DB setup
DATABASE_URL = "sqlite:///./images.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    likes = Column(Integer, default=0)
    liked_ips = Column(String, default="")  # comma-separated IPs

Base.metadata.create_all(bind=engine)

# Paths
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
def upload_image(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    db = SessionLocal()
    if not db.query(Image).filter(Image.filename == file.filename).first():
        db.add(Image(filename=file.filename))
        db.commit()
    db.close()
    return RedirectResponse(url="/gallery", status_code=303)

@app.get("/gallery", response_class=HTMLResponse)
def gallery_page(request: Request):
    db = SessionLocal()
    images = db.query(Image).all()
    db.close()
    return templates.TemplateResponse("gallery.html", {"request": request, "images": images})

@app.post("/like/{image_id}")
def like_image(image_id: int, request: Request):
    client_ip = request.client.host
    db = SessionLocal()
    image = db.query(Image).filter(Image.id == image_id).first()
    if image and client_ip not in image.liked_ips.split(","):
        image.likes += 1
        image.liked_ips += f",{client_ip}"
        db.commit()
    db.close()
    return RedirectResponse(url="/gallery", status_code=303)

