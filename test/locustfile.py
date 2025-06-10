from locust import HttpUser, task, between


class FullUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def full_flow(self):
        with open("test.jpg", "rb") as f:
            files = {'file': ("test.jpg", f, "image/jpeg")}
            self.client.post("/upload", files=files)

        self.client.get("/gallery")
        self.client.post("/like/1")
