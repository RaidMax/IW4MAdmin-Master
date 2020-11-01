from typing import Iterable

from ecommerce.integrations.data.meta_data import MetaData
from ecommerce.integrations.data.plan_data import PlanData


class PlanLogic:
    def __init__(self, customer_data: PlanData = None, external_meta_data: MetaData = None):
        self._customer_data = customer_data or PlanData()
        self._external_meta_data = external_meta_data or MetaData()

    def get_plans(self) -> Iterable:
        """
        performs any mapping logic from subscription api
        :return:
        """
        plans = self._customer_data.get_all_plans()
        plans_meta = self._external_meta_data.get('plans', '')
        return [{
            'name': plan.name,
            'description': plan.description,
            'price': '{:.2f}'.format(plan.price / 100.0),
            'period_unit': plan.period_unit,
            'id': plan.id,
            'meta': plans_meta[plan.id],
            'subscription_count': self.get_value_or_none_for_dict_entry(plans_meta, plan.id, 'subscription_count')
        } for plan in plans]

    @staticmethod
    def get_value_or_none_for_dict_entry(dictionary: dict, key: str, attribute: str):
        dict_value = dictionary.get(key, None)
        if dict_value and hasattr(dict_value, attribute):
            return getattr(dict_value, attribute)
        return None


