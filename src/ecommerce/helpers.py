CONTENT_TYPE_BINARY = 0
CONTENT_TYPE_SCRIPT = 1


def determine_content_type(content_name: str) -> int:
    if content_name.lower().endswith('.dll'):
        return CONTENT_TYPE_BINARY
    if content_name.lower().endswith('.js'):
        return CONTENT_TYPE_SCRIPT
