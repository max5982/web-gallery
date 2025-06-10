from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from PIL import Image, ImageOps
import cv2
import os
import shutil
import subprocess

app = FastAPI()

# --------------------
# DB setup (MySQL)
# --------------------
DATABASE_URL = "mysql+pymysql://max:intel123@localhost:3306/webgallery?charset=utf8mb4"
Base = declarative_base()
VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=50,
    pool_recycle=3600,
    pool_pre_ping=True
)
SessionLocal = scoped_session(sessionmaker(bind=engine))

class ImageModel(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True)
    likes = Column(Integer, default=0)
    liked_ips = Column(String(1024), default="")
    is_video = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# --------------------
# Paths for uploads and thumbnails
# --------------------
UPLOAD_DIR = "app/static/uploads"
THUMBNAIL_DIR = "app/static/uploads/thumbs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

# --------------------
# Mount static and templates
# --------------------
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --------------------
# 1) Upload page
# --------------------
@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

# --------------------
# 2) Handle upload
# --------------------
def get_video_rotation(path: str) -> int:
    """
    ffprobe 를 이용해 비디오 첫 스트림의 'rotate' 태그를 읽어옵니다.
    (없으면 빈 문자열 → 회전 없음으로 간주)
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream_tags=rotate",
        "-of", "default=nw=1:nk=1",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = result.stdout.strip()
    return int(out) if out.isdigit() else 0

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0, os.SEEK_SET)
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="파일 크기가 너무 큽니다. 100MB 이하의 파일만 업로드 가능합니다!"
        )

    filename = file.filename
    thumbfilename = file.filename
    original_path = os.path.join(UPLOAD_DIR, filename)
    with open(original_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    is_video = any(filename.lower().endswith(ext) for ext in VIDEO_EXTS)
    if is_video:
        name, _ = os.path.splitext(filename)    # ("myvideo", ".mp4")
        thumbfilename = f"{name}.jpeg"             # "myvideo.jpeg"
    thumbnail_path = os.path.join(THUMBNAIL_DIR, thumbfilename)

    if not is_video:
        # Image processing
        try:
            img = Image.open(original_path)
            img = ImageOps.exif_transpose(img)
        except Exception:
            os.remove(original_path)
            raise HTTPException(status_code=400, detail="유효한 이미지 파일이 아닙니다.")

        width, height = img.size
        # 4:3 central crop
        if height > width and (height / width) > (4 / 3):
            target_h = int(width * 4 / 3)
            crop_y = (height - target_h) // 2
            img = img.crop((0, crop_y, width, crop_y + target_h))
        elif width > height and (width / height) > (4 / 3):
            target_w = int(height * 4 / 3)
            crop_x = (width - target_w) // 2
            img = img.crop((crop_x, 0, crop_x + target_w, height))

        img.thumbnail((img.width // 4, img.height // 4), Image.LANCZOS)
        img.save(thumbnail_path)
    else:
        # Video processing
        cap = cv2.VideoCapture(original_path)
        if not cap.isOpened():
            raise RuntimeError("비디오를 열 수 없습니다. 경로를 확인하세요.")
        ret, frame = cap.read()
        cap.release()  # 반드시 해제

        if not ret:
            raise RuntimeError("첫 프레임을 읽어올 수 없습니다.")

        rot = get_video_rotation(original_path)
        if rot:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        width, height = img.size
        if height > width and (height / width) > (4 / 3):
            print(f"111 h: {height}, w: {width}")
            target_h = int(width * 4 / 3)
            crop_y = (height - target_h) // 2
            img = img.crop((0, crop_y, width, crop_y + target_h))
        elif width > height and (width / height) > (4 / 3):
            print(f"222 h: {height}, w: {width}")
            target_w = int(height * 4 / 3)
            crop_x = (width - target_w) // 2
            img = img.crop((crop_x, 0, crop_x + target_w, height))

        img.thumbnail((img.width // 4, img.height // 4), Image.LANCZOS)
        img.save(thumbnail_path)

    # Save to DB
    db = SessionLocal()
    exists = db.query(ImageModel).filter(ImageModel.filename == filename).first()
    if not exists:
        db.add(ImageModel(filename=filename, is_video=is_video))
        db.commit()
    db.close()

    return RedirectResponse(url="/gallery", status_code=303)

# --------------------
# 3) Gallery page
# --------------------
@app.get("/gallery", response_class=HTMLResponse)
def gallery_page(request: Request):
    db = SessionLocal()
    images = db.query(ImageModel).all()
    db.close()
    return templates.TemplateResponse("gallery.html", {"request": request, "images": images})

# --------------------
# 4) Like endpoint
# --------------------
@app.post("/like/{image_id}")
def like_image(image_id: int, request: Request):
    client_ip = request.client.host
    db = SessionLocal()
    img = db.query(ImageModel).filter(ImageModel.id == image_id).first()
    if img and client_ip not in (img.liked_ips or "").split(","):
        img.likes += 1
        img.liked_ips = (img.liked_ips + "," + client_ip) if img.liked_ips else client_ip
        db.commit()
    likes = img.likes if img else 0
    db.close()
    return JSONResponse(content={"likes": likes})

