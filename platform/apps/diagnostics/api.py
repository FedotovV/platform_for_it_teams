from decimal import Decimal

from apps.cycles.api import survey_cycle_ids
from apps.diagnostics.models import ColorBound, SurveySnapshot

FILL_BELOW_36 = "#c4453c"
FILL_BELOW_51 = "#e07a2f"
FILL_BELOW_66 = "#d6a11a"
FILL_BELOW_85 = "#2fa84a"
FILL_FROM_85 = "#1d6b34"

BAND_LEGEND = (
    {"fill": FILL_BELOW_36, "label": "меньше 36%"},
    {"fill": FILL_BELOW_51, "label": "с 36% и меньше 51%"},
    {"fill": FILL_BELOW_66, "label": "с 51% и меньше 66%"},
    {"fill": FILL_BELOW_85, "label": "с 66% и меньше 85%"},
    {"fill": FILL_FROM_85, "label": "85% и больше"},
)


def color_for(score):
    bounds = list(ColorBound.objects.all())
    if not bounds:
        return None
    for bound in bounds:
        if bound.min_score <= score <= bound.max_score:
            return bound.label
    return None


def share_paint(score, maximum):
    """Доля балла от максимума шкалы. Нет балла или максимума — сектор не красится."""
    score = _number(score)
    maximum = _number(maximum)
    if score is None or maximum is None or maximum <= 0:
        return None
    percent = (Decimal(str(score)) / Decimal(str(maximum))) * Decimal(100)
    if percent > 100:
        percent = Decimal(100)
    ratio = percent / Decimal(100)
    if ratio < 0:
        ratio = Decimal(0)
    return {
        "fill": fill_for_percent(percent),
        "ratio": float(ratio),
        "percent_text": _percent_text(percent),
    }


def fill_for_percent(percent):
    if percent < 36:
        return FILL_BELOW_36
    if percent < 51:
        return FILL_BELOW_51
    if percent < 66:
        return FILL_BELOW_66
    if percent < 85:
        return FILL_BELOW_85
    return FILL_FROM_85


def present_blocks(snapshot):
    maximum = snapshot.get("scale_maximum")
    blocks = []
    for block in snapshot["blocks"]:
        row = dict(block)
        painted = share_paint(block.get("score"), maximum)
        if painted is not None:
            row["chart_fill"] = painted["fill"]
            row["chart_ratio"] = painted["ratio"]
            row["chart_percent"] = painted["percent_text"]
        blocks.append(row)
    return {**snapshot, "blocks": blocks}


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if text == "":
            return None
        try:
            value = float(text) if "." in text else int(text)
        except ValueError:
            return None
    if not isinstance(value, (int, float)):
        return None
    return value


def _percent_text(percent):
    shown = percent.quantize(Decimal("0.01"))
    text = format(shown, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _json_number(value):
    if value is None:
        return None
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


def _blocks(raw, *, with_color):
    painted = []
    for block in raw:
        item = {"code": block["code"], "score": block["score"]}
        if with_color:
            item["color"] = color_for(block["score"])
        painted.append(item)
    return painted


def snapshot_for(cycle_id, *, with_color=True):
    row = SurveySnapshot.objects.filter(cycle_id=cycle_id).first()
    if row is None:
        return None
    return {
        "cycle_id": str(row.cycle_id),
        "scale_version": row.scale_version,
        "scale_maximum": _json_number(row.scale_maximum),
        "blocks": _blocks(row.blocks, with_color=with_color),
    }


def team_snapshot_pair(team_id, *, with_color):
    found = []
    for cycle_id in survey_cycle_ids(team_id):
        payload = snapshot_for(cycle_id, with_color=with_color)
        if payload is not None:
            found.append(payload)
    latest = found[-1] if found else None
    previous = found[-2] if len(found) > 1 else None
    return latest, previous
