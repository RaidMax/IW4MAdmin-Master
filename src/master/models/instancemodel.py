import time

class InstanceModel(object):
    def __init__(self, id, version, uptime, servers, ip_address, webfront_url):
        self.id = id
        self.version = version
        self.uptime = uptime
        self.servers = servers
        self.last_heartbeat = int(time.time())
        self.ip_address = ip_address
        self.webfront_url = webfront_url or f'http://{ip_address}:1624'

    def __repr__(self):
        return '<InstanceModel(id={id})>'.format(id=self.id)