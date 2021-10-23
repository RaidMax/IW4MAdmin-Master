import re
import time

from netaddr import IPAddress, AddrFormatError

url_regex = re.compile(
    r'^(https?://'
    r'((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}))'
    r'((?::\d+)?'
    r'(?:/?|[/?]\S+))$', re.IGNORECASE)


class InstanceModel(object):
    def __init__(self, id, version, uptime, servers, ip_address, webfront_url, **kwargs):
        self.id = id
        self.version = version
        self.uptime = uptime
        self.servers = servers
        self.last_heartbeat = int(time.time())
        self.ip_address = ip_address
        self.webfront_url = self.__check_if_non_public(webfront_url, ip_address)

    @staticmethod
    def __check_if_non_public(url, ip):
        # version is old and not sending webfront url, so we assume default port
        if url is None:
            return f'http://{ip}:1624'

        # make sure they're actually sending us an address and not trying to inject something
        match = re.match(url_regex, url)

        if not match or not match.groups():
            return None

        address = match.groups()[1]
        port = match.groups()[2]

        parsed_ip = None

        try:
            parsed_ip = IPAddress(address)
        except AddrFormatError:
            pass

        if parsed_ip is not None and (parsed_ip.is_private() or parsed_ip.is_loopback()):
            return f'http://{ip}{port}'

        return url

    def __repr__(self):
        return '<InstanceModel(id={id})>'.format(id=self.id)
