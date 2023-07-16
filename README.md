# Web-scrape
simple web scrape using python script, and all the code base is containerized.

1. clone the reop
2. move to the path `cd Web-scrape` >
3. `docker compose up --build -d`
4. afetr the containers are up `docker start web-scrape-web-scrape-app-1`
5. after the container exited `docker cp web-scrape-web-scrape-app-1:/app/track_data ./` 
