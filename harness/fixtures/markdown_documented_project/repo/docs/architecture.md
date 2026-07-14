# Architecture

The public entry point is `build_report` in [report.py](../report.py).

## Rendering

Reports are deterministic.

```python
build_report("example")
```

## Limitations

Runtime plugins are not inspected.
