"""Saída da área segura e objeto crítico no campo."""
from __future__ import annotations


def _center(bbox):
    x, y, width, height = bbox
    return (x + width / 2, y + height / 2)


def _inside(point, rect) -> bool:
    x, y, width, height = rect
    px, py = point
    return x <= px <= x + width and y <= py <= y + height


def zone_events(
    detections,
    *,
    safe_rect,
    field_rect,
    critical_labels=("cell phone", "knife"),
) -> list[dict]:
    events = []
    labels = {name.casefold() for name in critical_labels}
    for det in detections:
        label = det["label"]
        center = _center(det["bbox"])
        if label.casefold() == "person" and not _inside(center, safe_rect):
            events.append({
                "kind": "left_safe_zone",
                "label": label,
                "detail": "pessoa fora da area segura",
            })
        if label.casefold() in labels and _inside(center, field_rect):
            events.append({
                "kind": "critical_object",
                "label": label,
                "detail": f"{label} dentro do campo critico",
            })
    return events
