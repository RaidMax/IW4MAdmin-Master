from ecommerce import api
from ecommerce.resources.plugin_event import PluginEvent
from ecommerce.resources.plugin_subscriptions import PluginSubscription

api.add_resource(PluginSubscription, '/plugin_subscriptions')
api.add_resource(PluginEvent, '/api/plugin/event')
