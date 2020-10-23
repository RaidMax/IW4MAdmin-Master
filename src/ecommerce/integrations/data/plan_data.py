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
            plans = chargebee.Plan.list({'status[is]': 'active'}).response
        except chargebee.api_error.APIError as ex:
            self._logger.error('could not retrieve plans', exc_info=ex)
            return []

        if not plans:
            self._logger.warning('no plans available')

        return BoxList(plan['plan'] for plan in plans)
