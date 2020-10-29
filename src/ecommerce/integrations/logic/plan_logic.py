from typing import Iterable

from ecommerce.integrations.data.plan_data import PlanData


class PlanLogic:
    def __init__(self, customer_data: PlanData = None):
        self._customer_data = customer_data or PlanData()

    def get_plans(self) -> Iterable:
        """
        performs any mapping logic from subscription api
        :return:
        """
        plans = self._customer_data.get_all_plans()
        return [{
            'name': plan.name,
            'description': plan.description,
            'price': '{:.2f}'.format(plan.price / 100.0),
            'period_unit': plan.period_unit,
            'id': plan.id,
            'meta': plan.meta_data,
            'subscription_count': plan.subscription_count
        } for plan in plans]
