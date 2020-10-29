import logging
from collections import Iterable

import chargebee
from box import BoxList


class PlanData:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def get_all_plans(self) -> Iterable:
        """
        retrieves all plans available to subscribe to
        :return:
        """
        try:
            plans_response = chargebee.Plan.list({'status[is]': 'active'}).response
            plans = BoxList(plan['plan'] for plan in plans_response)

            if not plans:
                self._logger.warning('no plans available')

            plan_ids = [plan.id for plan in plans]
            subscriptions_response = chargebee.Subscription.list({'plan_id[in]': f'[{",".join(plan_ids)}]'}).response
            subscriptions = BoxList(subscriptions_response)

            for plan in plans:
                plan.subscription_count = len([sub for sub in subscriptions if sub.subscription.plan_id == plan.id])

            return plans
        except chargebee.api_error.APIError as ex:
            self._logger.error('could not retrieve plans', exc_info=ex)
            return []



