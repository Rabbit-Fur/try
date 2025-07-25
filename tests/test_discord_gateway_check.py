import types
import logging
import asyncio
import sys

import pytest


@pytest.mark.asyncio
async def test_analyze_warns_on_time_sleep(monkeypatch, caplog):
    from codex.diagnostics import discord_gateway_check as mod

    async def fake_check():
        import time

        time.sleep(1)

    fake_mod = types.SimpleNamespace(check_upcoming_events=fake_check)
    monkeypatch.setitem(sys.modules, "bot.dm_scheduler", fake_mod)

    with caplog.at_level(logging.WARNING):
        await mod.analyze_check_upcoming_events()
    assert "time.sleep()" in caplog.text


@pytest.mark.asyncio
async def test_analyze_handles_async_function(monkeypatch, caplog):
    from codex.diagnostics import discord_gateway_check as mod

    async def fake_check():
        await asyncio.sleep(0)

    fake_mod = types.SimpleNamespace(check_upcoming_events=fake_check)
    monkeypatch.setitem(sys.modules, "bot.dm_scheduler", fake_mod)

    with caplog.at_level(logging.INFO):
        await mod.analyze_check_upcoming_events()
    assert "Kein blockierender sleep" in caplog.text
