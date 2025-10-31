from __future__ import annotations

from typing import List

from .metrics import list_counters, list_counters_labelled


def _escape_label_value(val: str) -> str:
    # Prometheus exposition format requires backslash escaping for quotes and backslashes
    return val.replace("\\", "\\\\").replace("\"", "\\\"")


def export_text() -> str:
    """Render in-process counters to Prometheus text exposition format.

    - Unlabelled counters are exported as `<name> <value>` with a `# TYPE` header once per metric name.
    - Labelled counters are exported as `<name>{k="v",...} <value>` with a corresponding `# TYPE` header once.
    - Only non-zero counters are emitted to keep output concise.
    """
    lines: List[str] = []
    emitted_type: set[str] = set()

    # Unlabelled
    for name, val in list_counters():
        if val == 0:
            continue
        if name not in emitted_type:
            lines.append(f"# TYPE {name} counter")
            emitted_type.add(name)
        lines.append(f"{name} {val}")

    # Labelled
    for name, labels, val in list_counters_labelled():
        if val == 0:
            continue
        if name not in emitted_type:
            lines.append(f"# TYPE {name} counter")
            emitted_type.add(name)
        label_str = ",".join(f"{k}=\"{_escape_label_value(v)}\"" for k, v in labels)
        lines.append(f"{name}{{{label_str}}} {val}")

    return "\n".join(lines) + ("\n" if lines else "")

