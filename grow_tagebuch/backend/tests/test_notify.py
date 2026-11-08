import os
import tempfile
from datetime import date, datetime, timedelta

os.environ.setdefault("GROW_DATA_DIR", tempfile.mkdtemp())

from app import notify  # noqa: E402
from app.models import ClimateSample  # noqa: E402

CFG = {**notify.DEFAULTS, "topic_effective": "t", "server_effective": "https://ntfy.sh"}


def _s(temp, rh):
    return ClimateSample(setup_id=99, ts=datetime.now(), temp=temp, rh=rh)


def test_climate_alarm_after_delay_and_recovery():
    notify._state.clear()
    t0 = datetime(2026, 11, 8, 12, 0)
    # 31 °C ist für Sämlinge (22–27) deutlich zu hoch
    assert notify.climate_messages(99, _s(31, 85), "seedling", CFG, t0) == []
    assert notify.climate_messages(99, _s(31, 85), "seedling", CFG, t0 + timedelta(minutes=20)) == []
    m = notify.climate_messages(99, _s(31, 85), "seedling", CFG, t0 + timedelta(minutes=30))
    assert len(m) == 1 and "Temperatur zu hoch" in m[0]["title"] and m[0]["priority"] == 4
    # keine Wiederholung vor Ablauf der Sperrzeit
    assert notify.climate_messages(99, _s(31, 85), "seedling", CFG, t0 + timedelta(minutes=60)) == []
    back = notify.climate_messages(99, _s(25, 85), "seedling", CFG, t0 + timedelta(minutes=70))
    assert len(back) == 1 and "wieder im Bereich" in back[0]["title"]


def test_mild_deviation_only_in_strict_mode():
    notify._state.clear()
    t0 = datetime(2026, 11, 8, 12, 0)
    # 28 °C liegt knapp über 27 → grenzwertig
    for i in range(4):
        assert notify.climate_messages(99, _s(28, 70), "seedling", CFG, t0 + timedelta(minutes=10 * i)) == []
    notify._state.clear()
    strict = {**CFG, "climate_strict": True}
    msgs = []
    for i in range(4):
        msgs += notify.climate_messages(99, _s(28, 70), "seedling", strict, t0 + timedelta(minutes=10 * i))
    assert any("Temperatur" in m["title"] for m in msgs)


def test_sensor_offline():
    notify._state.clear()
    t0 = datetime(2026, 11, 8, 12, 0)
    assert notify.climate_messages(99, None, "seedling", CFG, t0) == []
    m = notify.climate_messages(99, None, "seedling", CFG, t0 + timedelta(minutes=30))
    assert len(m) == 1 and "keine Werte" in m[0]["title"]
    back = notify.climate_messages(99, _s(24, 70), "seedling", CFG, t0 + timedelta(minutes=40))
    assert any("wieder da" in x["title"] for x in back)


def test_no_alarm_without_phase():
    notify._state.clear()
    t0 = datetime(2026, 11, 8, 12, 0)
    for i in range(5):
        assert notify.climate_messages(99, _s(35, 20), None, CFG, t0 + timedelta(minutes=10 * i)) == []


def test_tasks_due_now():
    cfg = {**CFG, "tasks_time": "08:00"}
    assert not notify._tasks_due_now(cfg, None, datetime(2026, 11, 8, 7, 59))
    assert notify._tasks_due_now(cfg, None, datetime(2026, 11, 8, 8, 0))
    assert notify._tasks_due_now(cfg, "2026-11-07", datetime(2026, 11, 8, 14, 0))
    assert not notify._tasks_due_now(cfg, "2026-11-08", datetime(2026, 11, 8, 14, 0))
