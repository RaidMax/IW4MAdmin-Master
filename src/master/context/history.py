import time


class History:
    sample_rate = 30
    max_history_count = int((3600 * 24 * 7) / sample_rate)  # total seconds in a week period at 30 second sample rate

    def __init__(self):
        self.client_history = list()
        self.instance_history = list()
        self.server_history = list()

    def add_client_history(self, client_num, override_time=None):
        if len(self.client_history) >= History.max_history_count:
            self.client_history = self.client_history[1:]
        self.client_history.append({
            'count': client_num,
            'time': int(override_time if override_time is not None else time.time())
        })

    def add_server_history(self, server_num, override_time=None):
        if len(self.server_history) >= History.max_history_count:
            self.server_history = self.server_history[1:]
        self.server_history.append({
            'count': server_num,
            'time': int(override_time if override_time is not None else time.time())
        })

    def add_instance_history(self, instance_num, override_time=None):
        if len(self.instance_history) >= History.max_history_count:
            self.instance_history = self.instance_history[1:]
        self.instance_history.append({
            'count': instance_num,
            'time': int(override_time if override_time is not None else time.time())
        })

    def fill_empty_history(self):
        if len(self.instance_history) > 0:
            current_time = time.time()
            last_history_time = self.instance_history[-1]['time']
            while last_history_time < current_time:
                self.add_client_history(0)
                self.add_server_history(0)
                self.add_instance_history(0)
                last_history_time = last_history_time + History.sample_rate
