import json
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .history import History

import jsonpickle
import time
import os

from ..models.instancemodel import InstanceModel
from ..schema.instanceschema import InstanceSchema
from ..database import db
from ..config import config

logger = logging.getLogger(__name__)


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
            trigger=IntervalTrigger(seconds=config.history_sample_rate),
            id='update history',
            name='update client and instance count every 30 seconds',
            replace_existing=True
        )
        # Only schedule JSON persistence if database is not connected
        if not db.is_connected:
            self.scheduler.add_job(
                func=self._persist,
                trigger=IntervalTrigger(seconds=15),
                id='persist history',
                name='persists the history to disk',
                replace_existing=True
            )
            logger.info("JSON persistence enabled (database not connected)")
        else:
            logger.info("Using PostgreSQL for persistence (JSON disabled)")

    def _update_history_count(self, fill_empty=False):
        if fill_empty:
            self.history.fill_empty_history()
        else:
            # Single pass - no intermediate list allocations
            instance_count = 0
            server_count = 0
            client_count = 0
            
            for instance in self.instance_list.values():
                instance_count += 1
                for server in instance.servers:
                    server_count += 1
                    client_count += server.clientnum
            
            # Update in-memory history
            self.history.add_client_history(client_count)
            self.history.add_instance_history(instance_count)
            self.history.add_server_history(server_count)
            
            # Also record to database if connected
            if db.is_connected:
                try:
                    db.record_history(
                        instance_count=instance_count,
                        server_count=server_count,
                        client_count=client_count
                    )
                    db.update_daily_metrics()
                except Exception as e:
                    logger.debug(f"Failed to record history to database: {e}")

    def _remove_staleinstances(self):
        for key, value in list(self.instance_list.items()):
            if int(time.time()) - value.last_heartbeat > 60:
                logger.debug(f'[_remove_staleinstances] removing stale instance {key}')
                del self.instance_list[key]
                if key in self.token_list:
                    del self.token_list[key]
        logger.debug(f'[_remove_staleinstances] {len(self.instance_list)} active instances')

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
            logger.debug(f'[add_instance] instance {instance.id} already added, updating instead')
            return self.update_instance(instance)
        else:
            logger.debug(f'[add_instance] adding instance {instance.id}')
            self.instance_list[instance.id] = instance

    def update_instance(self, instance):
        if instance.id not in self.instance_list:
            logger.debug(f'[update_instance] instance {instance.id} not added, adding instead')
            return self.add_instance(instance)
        else:
            logger.debug(f'[update_instance] updating instance {instance.id}')
            self.instance_list[instance.id] = instance

    def add_token(self, instance_id, token):
        logger.debug(f'[add_token] adding token for id {instance_id}')
        self.token_list[instance_id] = token

    def get_token(self, instance_id):
        try:
            return self.token_list[instance_id]
        except KeyError:
            return False

    def _persist(self):
        """Persist history to JSON (only used when database is not connected)."""
        if db.is_connected:
            return  # Skip JSON persistence when database is active
            
        if not os.path.exists('./persistence'):
            os.makedirs('./persistence')
        with open('./persistence/history.json', 'w') as out_json:
            history_json = jsonpickle.encode(self.history)
            out_json.write(history_json)

    def _load_persistence(self):
        history = History()
        # Only load from JSON if database is not connected
        if not db.is_connected and os.path.exists('./persistence/history.json'):
            with open('./persistence/history.json', 'r') as in_json:
                history_json = in_json.read()
                if len(history_json) > 0:
                    history = jsonpickle.decode(history_json)
                    logger.info("Loaded history from JSON persistence")

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
            from urllib import request
            with request.urlopen('http://192.223.26.190:5000/instance/') as response:
                data = response.read()
                encoding = response.info().get_content_charset('utf-8')
                decoded = json.loads(data.decode(encoding))
                self.instance_list = {instance['id']: InstanceSchema().load(instance) for instance in decoded}

