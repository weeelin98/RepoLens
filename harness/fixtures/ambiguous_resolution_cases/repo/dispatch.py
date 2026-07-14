def dispatch(handler_name: str, value: str) -> str:
    handler = globals()[handler_name]
    return handler(value)
