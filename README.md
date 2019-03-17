# docker-dropbox-app
Syncronization dropbox app

[![](https://images.microbadger.com/badges/image/rbonghi/dropbox.svg)](https://microbadger.com/images/rbonghi/dropbox "Get your own image badge on microbadger.com") [![](https://images.microbadger.com/badges/version/rbonghi/dropbox.svg)](https://microbadger.com/images/rbonghi/dropbox "Get your own version badge on microbadger.com") 

How to start up the docker-dropbox app machine:
1. Create your App in dropbox
2. Write your docker-compose.yml file or add:
```yml
version: '3'
services:
  dropbox:
    image: rbonghi/dropbox:latest
    environment:
      - PYTHONUNBUFFERED=1
      - DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE>
    volumes:
      - <FOLDER YOU WANT SYNC>:/dropbox
```
3. start your docker:
```
docker-compose up
```
 
# Make manifest for amd64 and arm
Use this manifest for multi architect version
```
docker manifest create rbonghi/dropbox:latest rbonghi/dropbox:amd64-latest rbonghi/dropbox:arm64-latest
docker manifest annotate --os linux --arch arm64 --variant armv8 rbonghi/dropbox:latest rbonghi/dropbox:arm64-latest
docker manifest push rbonghi/dropbox:latest
```

