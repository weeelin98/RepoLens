from catalog.repository import get_item


def describe_item(sku: str) -> str:
    item = get_item(sku)
    return item or "missing"
