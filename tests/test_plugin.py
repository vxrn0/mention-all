"""Самопроверка логики mention_all.plugin без JVM.

Запуск: python3 tests/test_plugin.py (падение = ошибка, тишина = всё ок).
"""

import importlib.util
import sys
import time
import types
from pathlib import Path
from importlib.machinery import SourceFileLoader

# ---- заглушки SDK, которых нет на десктопе ----

base_plugin = types.ModuleType("base_plugin")
base_plugin.HookStrategy = types.SimpleNamespace(
    DEFAULT="DEFAULT", CANCEL="CANCEL", MODIFY="MODIFY", MODIFY_FINAL="MODIFY_FINAL")


class HookResult:
    def __init__(self, strategy=None, **_):
        self.strategy = strategy


class BasePlugin:
    def get_setting(self, key, default=None):
        return getattr(self, "_settings", {}).get(key, default)

    def log(self, message):
        pass


base_plugin.HookResult = HookResult
base_plugin.BasePlugin = BasePlugin

ui = types.ModuleType("ui")
ui_settings = types.ModuleType("ui.settings")


class _Item:
    def __init__(self, **kw):
        self.__dict__.update(kw)


for cls in ("Header", "Switch", "Input", "Text", "Divider", "Selector"):
    setattr(ui_settings, cls, lambda **kw: _Item(**kw))
ui.settings = ui_settings
sys.modules.update({"base_plugin": base_plugin, "ui": ui, "ui.settings": ui_settings})

# ---- загрузка плагина ----

plugin_path = Path(__file__).resolve().parent.parent / "plugin" / "mention_all.plugin"
loader = SourceFileLoader("mention_all_plugin", str(plugin_path))
spec = importlib.util.spec_from_loader("mention_all_plugin", loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

build = mod.build_mentions
chat_id = mod.chat_id_from_dialog

# ---- build_mentions ----

text, spans = build("hi @all, wake up", [(1, "Ann"), (2, "Bob")], 100)
assert text == "hi Ann Bob, wake up", text
assert spans == [(3, 3, 1), (7, 3, 2)], spans  # utf16 offsets по словам

# повторные токены убираются
text, spans = build("@all @all", [(5, "X")], 100)
assert text == "X", repr(text)

# utf-16: emoji до токена занимает 2 кодовые единицы
text, spans = build("\U0001F44B @all", [(9, "Z")], 100)
assert spans == [(3, 1, 9)], spans

# лимит
text, spans = build("@all", [(i, f"u{i}") for i in range(10)], 3)
assert text == "u0 u1 u2" and len(spans) == 3

# пустой список участников / без токена — текст не меняется
assert build("no token here", [(1, "A")], 100)[0] == "no token here"
assert build("@all", [], 100) == ("@all", [])

# имя, содержащее @all, не зациклит повторный хук
text, spans = build("@all", [(1, "@all fan")], 100)
assert text == "fan" and spans == [(0, 3, 1)]

# регистр и защита от @allinside / @@all
assert build("пишите @ALL", [(1, "A")], 100)[0] == "пишите A"
assert build("@allinside", [(1, "A")], 100)[0] == "@allinside"

# ---- chat_id_from_dialog ----

assert chat_id(-123) == 123            # базовая группа
assert chat_id(-1000000000123) == 123  # супергруппа
assert chat_id(12345) is None          # личка
assert chat_id(0) is None

# ---- _jlist: Java-список читается по индексу, None не роняет ----


class FakeJavaList:
    def __init__(self, *items):
        self._items = list(items)

    def size(self):
        return len(self._items)

    def get(self, i):
        return self._items[i]


assert mod._jlist(FakeJavaList(1, 2, 3)) == [1, 2, 3]
assert mod._jlist(None) == []

# ---- маршрутизация хука (до Java-кода) ----


class Params:
    def __init__(self, peer, message, caption=None):
        self.peer, self.message, self.caption = peer, message, caption


plugin = mod.MentionAllPlugin()

assert plugin.on_send_message_hook(0, Params(123, "@all")) is None  # личка
assert plugin.on_send_message_hook(0, Params(-123, "hi")) is None   # без токена
assert plugin.on_send_message_hook(0, Params(-123, None, None)) is None  # пустое
plugin._settings = {"enabled": False}
assert plugin.on_send_message_hook(0, Params(-123, "@all")) is None  # выключен

plugin._settings = {"enabled": True}
seen = []
plugin._mention_all = lambda *a: seen.append(a)
res = plugin.on_send_message_hook(7, Params(-123, "go @all"))
assert res is not None and res.strategy == mod.HookStrategy.CANCEL
assert seen and seen[0][0] == 7  # аккаунт протащен без искажений

res = plugin.on_send_message_hook(7, Params(-123, None, "cap @all"))
assert res is not None and res.strategy == mod.HookStrategy.CANCEL  # подпись тоже работает

# защёлка: после сбоя тот же текст уходит как есть, без повторного цикла
p = Params(-123, "go @all")
plugin._mention_all = lambda *a: seen.append(a)
assert plugin.on_send_message_hook(7, p).strategy == mod.HookStrategy.CANCEL
mod.MentionAllPlugin._recent_fail.clear()
mod.MentionAllPlugin._recent_fail[(int(p.peer), "go @all")] = time.monotonic()
seen.clear()
assert plugin.on_send_message_hook(7, p) is None  # сбой запомнен — не отменяем
assert not seen  # и даже не пытаемся собрать участников

print("ok")
