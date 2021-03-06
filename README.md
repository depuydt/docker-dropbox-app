# docker-dropbox-app
:whale: Docker syncronization container for Dropbox using a token app 

[![](https://images.microbadger.com/badges/version/rbonghi/dropbox.svg)](https://microbadger.com/images/rbonghi/dropbox "Get your own version badge on microbadger.com") [![](https://images.microbadger.com/badges/image/rbonghi/dropbox.svg)](https://microbadger.com/images/rbonghi/dropbox "Get your own image badge on microbadger.com") 

Docker hub repos: https://hub.docker.com/r/rbonghi/dropbox

When your docker is ready, all files and folders will be sync in **realtime**. A watchdog check every time if a file or folder is created, deleted or modified, and will be update your dropbox folder.

If you add in your root a file `.dropboxignore` you can select witch type of file or folder you want exclude, look like your git repository.

## Start with docker
To use this docker is really easy:
1. Create your [App in dropbox](https://www.dropbox.com/developers/reference/getting-started#app%20console)
2. Generated access token
3. Pull this docker
```
docker pull rbonghi/dropbox
```
4. Run your docker
```
docker run -e DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE> -v <FOLDER YOU WANT SYNC>:/dropbox dropbox
```

## Start with docker-compose
How to start up the docker-dropbox app machine:
1. Create your [App in dropbox](https://www.dropbox.com/developers/reference/getting-started#app%20console)
2. Generated access token
3. Write your docker-compose.yml file or add:
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
4. start your docker:
```
docker-compose up
```

# Configuration
You have two option to run the dropboxsync:
* **--inverval** [_Default:_ 10s] Interval refresh folder from Dropbox
* **--fromLocal** Will be overwriten from your PC follder to Dropbox
* **--fromDropbox** Will be overwriten from Dropbox to your PC folder
* **--verbose** Show all debug messages

To select this option you can run the docker machine adding:
```
docker run -e DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE> -v <FOLDER YOU WANT SYNC>:/dropbox dropbox --fromDropbox
```
or
```yml
version: '3'
services:
  dropbox:
    image: rbonghi/dropbox:latest
    command: ["--fromDropbox", "-i", "120"]
    environment:
      - PYTHONUNBUFFERED=1
      - DROPBOX_TOKEN=<WRITE YOUR TOKEN HERE>
    volumes:
      - <FOLDER YOU WANT SYNC>:/dropbox
```

# Start without docker
If you want launch this script without start a docker container:
```
python DropboxSync.py <DROPBOX_FOLDER> <ROOT_FOLDER> --token <WRITE YOUR TOKEN HERE> [options]
```
For `[options]`:
* **--verbose** Show in detail all steps for each sync
* **--fromLocal** or **--fromDropbox** Read [Configuration](#configuration)
* **--interval** [default=60s] The Interval to sync from Dropbox in **--fromDropbox** mode

# Make manifest for amd64 and arm
Use this manifest for multi architect version
```
docker manifest create rbonghi/dropbox:latest rbonghi/dropbox:amd64-latest rbonghi/dropbox:arm64-latest
docker manifest annotate --os linux --arch arm64 --variant armv8 rbonghi/dropbox:latest rbonghi/dropbox:arm64-latest
docker manifest push rbonghi/dropbox:latest
```

