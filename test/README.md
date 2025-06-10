# How to test
```
locust -f locustfile.py --host http://222.234.38.99:8090
locust -f locustfile.py --host http://222.234.38.99:8090 --headless -u 100 -r 10 -t 1m
```

