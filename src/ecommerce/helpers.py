# These values are the wire contract for the `type` field returned by the plugin_subscriptions
# endpoint. They must stay aligned with IW4MAdmin's PluginType enum ordinals
# (Application/Plugin/PluginImporter.cs): Binary=0, Script=1, CSharpScript=2, Bundle=3.
CONTENT_TYPE_UNKNOWN = -1
CONTENT_TYPE_BINARY = 0
CONTENT_TYPE_SCRIPT = 1
CONTENT_TYPE_BUNDLE = 3


def determine_content_type(content_name: str) -> int:
    if content_name.lower().endswith('.dll'):
        return CONTENT_TYPE_BINARY
    if content_name.lower().endswith('.js'):
        return CONTENT_TYPE_SCRIPT
    # plugin web-bundle: a zip of manifest.json + lib/ (dll) + wwwroot/ + optional gsc/.
    # encrypted and streamed verbatim like any other content; IW4MAdmin loads it in-memory.
    if content_name.lower().endswith('.zip'):
        return CONTENT_TYPE_BUNDLE
    return CONTENT_TYPE_UNKNOWN
