import json
import logging
from urllib import request

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .history import History

import jsonpickle
import time
import os

from ..models.instancemodel import InstanceModel
from ..schema.instanceschema import InstanceSchema


class Base:
    def __init__(self):
        self.debug = False
        self.instance_list = {}
        self.history = self._load_persistence()
        self._update_history_count(True)
        self.token_list = {}
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.scheduler.add_job(
            func=self._remove_staleinstances,
            trigger=IntervalTrigger(seconds=300),
            id='stale_instance_remover',
            name='Remove stale instances if no heartbeat in 5 minutes',
            replace_existing=True
        )
        self.scheduler.add_job(
            func=self._update_history_count,
            trigger=IntervalTrigger(seconds=30),
            id='update history',
            name='update client and instance count every 30 seconds',
            replace_existing=True
        )
        self.scheduler.add_job(
            func=self._persist,
            trigger=IntervalTrigger(seconds=15),
            id='persist history',
            name='persists the history to disk',
            replace_existing=True
        )

    def _update_history_count(self, fill_empty=False):
        if fill_empty:
            self.history.fill_empty_history()
        else:
            servers = [instance.servers for instance in self.instance_list.values()]
            servers = [inner for outer in servers for inner in outer]
            client_num = 0
            # force it being a number
            for server in servers:
                client_num += server.clientnum
            self.history.add_client_history(client_num)
            self.history.add_instance_history(len(self.instance_list))
            self.history.add_server_history(len(servers))

    def _remove_staleinstances(self):
        for key, value in list(self.instance_list.items()):
            if int(time.time()) - value.last_heartbeat > 60:
                logging.debug('[_remove_staleinstances] removing stale instance {id}'.format(id=key))
                del self.instance_list[key]
                del self.token_list[key]
        logging.debug('[_remove_staleinstances] {count} active instances'.format(count=len(self.instance_list.items())))

    def get_instances(self):
        return self.instance_list.values()

    def get_instance_count(self):
        return len(self.instance_list)

    def get_instance(self, instance_id):
        return self.instance_list[instance_id]

    def instance_exists(self, instance_id):
        if instance_id in self.instance_list.keys():
            return instance_id
        else:
            return False

    def add_instance(self, instance):
        if instance.id in self.instance_list:
            logging.debug('[add_instance] instance {id} already added, updating instead'.format(id=instance.id))
            return self.update_instance(instance)
        else:
            logging.debug('[add_instance] adding instance {id}'.format(id=instance.id))
            self.instance_list[instance.id] = instance

    def update_instance(self, instance):
        if instance.id not in self.instance_list:
            logging.debug('[update_instance] instance {id} not added, adding instead'.format(id=instance.id))
            return self.add_instance(instance)
        else:
            logging.debug('[update_instance] updating instance {id}'.format(id=instance.id))
            self.instance_list[instance.id] = instance

    def add_token(self, instance_id, token):
        logging.debug('[add_token] adding {token} for id {id}'.format(token=token, id=instance_id))
        self.token_list[instance_id] = token

    def get_token(self, instance_id):
        try:
            return self.token_list[instance_id]
        except KeyError:
            return False

    def _persist(self):
        if not os.path.exists('./persistence'):
            os.makedirs('./persistence')
        with open('./persistence/history.json', 'w') as out_json:
            history_json = jsonpickle.encode(self.history)
            out_json.write(history_json)

    def _load_persistence(self):
        history = History()
        if os.path.exists('./persistence/history.json'):
            with open('./persistence/history.json', 'r') as in_json:
                history_json = in_json.read()
                if len(history_json) > 0:
                    history = jsonpickle.decode(history_json)

        self._fill()

        return history

    def _fill(self):
        is_debug = False
        try:
            is_debug = os.environ.get('IW4MADMIN_DEBUG') is not None
        except KeyError:
            pass
        self.debug = is_debug

        if self.debug:
            with request.urlopen('http://192.223.26.190:5000/instance/') as response:
                data = response.read()
                encoding = response.info().get_content_charset('utf-8')
                decoded = json.loads(data.decode(encoding))
                self.instance_list = {instance['id']: InstanceSchema().load(instance)for instance in decoded}
