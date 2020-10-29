from ecommerce import api
from ecommerce.resources.plugin_subscriptions import PluginSubscription

api.add_resource(PluginSubscription, '/plugin_subscriptions')
