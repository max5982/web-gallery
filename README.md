# web-gallery

- Install required packages:
```
sudo apt install ffmpeg
sudo apt install mysql-server -y
sudo systemctl enable mysql
sudo systemctl start mysql

python3 -m venv venv_web
source venv_web/bin/activate
pip install -r requirements.txt
```

- DB init
```
sudo mysql

CREATE DATABASE webgallery CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'webuser'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON webgallery.* TO 'webuser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

- How to run
```
# run for dev version
uvicorn app.main:app --reload --host 0.0.0.0 --port 8090

# run for real use-cases
nohup gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 41 -b 0.0.0.0:8090 > log.txt 2>&1 &
```

- How to stop
```
ps aux | grep uvicorn
kill <PID>
killall gunicorn
```

- DB reset (PW: intel123)
```
rm -rf app/static/uploads/*
mysql -u max -p -D webgallery -e "DELETE FROM images;"
```
