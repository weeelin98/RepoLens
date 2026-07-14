from catalog.service import describe_item


def test_describe_item() -> None:
    assert describe_item("sku-1") == "Notebook"
