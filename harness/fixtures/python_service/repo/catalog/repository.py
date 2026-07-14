ITEMS = {"sku-1": "Notebook"}


def get_item(sku: str) -> str | None:
    return ITEMS.get(sku)
