# IW4MAdmin-Master
### Purpose
**IW4MAdmin-Master** is the master list for all running instance of [IW4MAdmin](https://github.com/RaidMax/IW4M-Admin/)
Each **IW4MAdmin** instance sends a heartbeat approximately every 30 seconds which is recieved by this service and stored.
**IW4MAdmin-Master** is also responsible for maintaining the version information and providing current translation strings.

### Requirements
`Python 3.8.x` or newer

### Environment
| Name               | Description                                        |
|--------------------|----------------------------------------------------|
| IA_MASTER_AUTH_KEY | Authorization secret key used to validate clients  |
| IA_BIND_ADDRESS    | Listen address to bind to                          |
| IA_BIND_PORT       | Port to bind to                                    |
| IA_DATA_SOURCE_URL | URL of persistent data source                      |

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

## Notes
Due to a compatibility issue with the `python-firebase` pip package and python 3.7+, the package installed in the virtual environment must be modified.  
Modifications outlined at [Receiving .async error when trying to import the firebase package](https://stackoverflow.com/questions/52133031/receiving-async-error-when-trying-to-import-the-firebase-package)