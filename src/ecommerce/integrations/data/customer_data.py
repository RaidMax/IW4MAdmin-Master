import logging
from typing import Iterable

import chargebee
from box import Box, BoxList


class CustomerData:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def get_customer_content_urls_by_email(self, email: str) -> Iterable[Box]:
        """
        retrieves the content urls for all subscriptions tied to the given email
        :param email: unique subscription email
        :return: Iterable[str] of content urls
        """
        try:
            customer_response = chargebee.Customer.list({
                'email[is]': email,
                'limit': 4
            }).response
        except chargebee.api_error.APIError as ex:
            self._logger.error(f'could not get customer with email "{email}"', exc_info=ex)
            return[]

        # no customer found
        if not customer_response:
            self._logger.info(f'no customer found with "{email}"')
            return []

        customer = Box(customer_response[0]['customer'])

        try:
            subscription_response = chargebee.Subscription.list({
                'customer_id[is]': customer.id,
                'status[is]': 'active'
            }).response
        except chargebee.api_error.APIError as ex:
            self._logger.error(f'could not get subscription list for customer_id "{customer.id}"', exc_info=ex)
            return []

        # customer has no active subscriptions
        if not subscription_response:
            self._logger.info(f'no active subscriptions found for "{customer.id}"')
            return []

        subscriptions = BoxList([subscription['subscription'] for subscription in subscription_response])
        subscription_ids = [subscription.plan_id for subscription in subscriptions]

        # get the plans attached to the subscription
        try:
            plans_response = chargebee.Plan.list({
                'id[in]': f'[{",".join(subscription_ids)}]'
            }).response
        except chargebee.api_error.APIError as ex:
            self._logger.error(f'could not get plans for subscription ids "{subscription_ids}"', exc_info=ex)
            return []

        # no plans are tied to the subscription (shouldn't happen)
        if not plans_response:
            self._logger.info(f'no plans found for for subscription ids "{subscription_ids}"')
            return []

        plans = BoxList(plans_response)

        content_data = []
        for plan in plans:
            if hasattr(plan.plan, 'meta_data'):
                meta = plan.plan.meta_data
                content_data.append(Box(meta))

        return content_data
