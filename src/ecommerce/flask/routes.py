from ecommerce import api
from ecommerce.resources.plugin_event import PluginEvent
from ecommerce.resources.plugin_subscriptions import PluginSubscription
from ecommerce.resources.plugin_entitlement import PluginEntitlement
from ecommerce.resources.plugin_sharing_report import PluginSharingReport

api.add_resource(PluginSubscription, '/plugin_subscriptions')
api.add_resource(PluginEvent, '/api/plugin/event')
api.add_resource(PluginEntitlement, '/plugin/entitlement')
api.add_resource(PluginSharingReport, '/plugin/sharing_report')
