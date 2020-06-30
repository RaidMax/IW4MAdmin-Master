# IW4MAdmin-Master
### Purpose
**IW4MAdmin-Master** is the master list for all running instance of [IW4MAdmin](https://github.com/RaidMax/IW4M-Admin/)
Each **IW4MAdmin** instance sends a heartbeat approximately every 30 seconds which is recieved by this service and stored.
**IW4MAdmin-Master** is also responsible for maintaining the version information and providing current translation strings.

### Requirements
`Python 3.8.x` or newer

### Start (local)
```bash
chmod +x launch.sh
./launch.sh
```

### Endpoints
Unless otherwise specified, all endpoints return JSON
#### /Health
Health status of the master 
#### /Instance
All active instances
#### /Version
Current stable and pre-release version
#### /History
Client and server count history
#### /Localization
Latest translation strings

### UI
#### Home
Zoomable plot of servers, client, and instance counts over an interval
#### /servers
Simple list of all server information grouped by game name
