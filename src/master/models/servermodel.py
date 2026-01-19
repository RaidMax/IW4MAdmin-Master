class ServerModel(object):
    def __init__(self, id, port, game, hostname, clientnum, maxclientnum, map, gametype, ip, version, resolved_external_ip_address):
        self.id = id
        self.port = port
        self.version = version
        self.game = game
        self.hostname = hostname
        self.clientnum = clientnum
        self.maxclientnum = maxclientnum
        self.map = map
        self.gametype = gametype
        self.ip = ip
        self.instance = None
        self.resolved_external_ip_address = resolved_external_ip_address

    def set_instance(self, instance):
        self.instance = instance
        return self

    def __repr__(self):
        return '<ServerModel(id={id})>'.format(id=self.id)
