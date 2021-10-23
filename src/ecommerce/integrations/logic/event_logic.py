import logging

from box import Box

from ecommerce.integrations.data.meta_data import MetaData


class EventLogic:
    def __init__(self, event_data: MetaData = None):
        self._logger = logging.getLogger(__name__)
        self._event_data = event_data or MetaData()

    def on_subscription_created(self, event: dict):
        self._logger.debug('handling subscription_created event')
        event_box = Box(event)
        plan_id = event_box.content.subscription.plan_id
        plan_meta = self._event_data.get('plans', plan_id)
        if plan_meta:
            plan_meta.subscription_count += 1
            if self._event_data.set('plans', plan_id, plan_meta):
                self._logger.debug(
                    f'plan with id "{plan_id}" subscription_count was updated to "{plan_meta.subscription_count}"')
                return True

    def on_subscription_cancelled(self, event: dict):
        self._logger.debug('handling subscription_cancelled event')
        event_box = Box(event)
        plan_id = event_box.content.subscription.plan_id
        plan_meta = self._event_data.get('plans', plan_id)
        if plan_meta:
            plan_meta.subscription_count -= 1
            if plan_meta.subscription_count < 0:
                self._logger.warning(f'plan id "{plan_id}" cannot have subscription_count less than 0')
                return True
            if self._event_data.set('plans', plan_id, plan_meta):
                self._logger.debug(
                    f'plan with id "{plan_id}" subscription_count was updated to "{plan_meta.subscription_count}"')
                return True

