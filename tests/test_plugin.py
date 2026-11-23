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
    def __init__(self, strategy=None, params=None, **_):
        self.strategy = strategy
        self.params = params


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


class ArrayList(list):
    def size(self):
        return len(self)

    def add(self, *args):
        if len(args) == 1:
            self.append(args[0])
        else:
            self.insert(args[0], args[1])

    def get(self, i):
        return self[i]


class WeakHashMap(dict):
    def put(self, key, value):
        self[key] = value


java_util = types.ModuleType("java.util")
java_util.ArrayList = ArrayList
java_util.WeakHashMap = WeakHashMap


class _Mention:
    kind = "mention"

    def __init__(self):
        self.offset = self.length = 0


class _InputUser:
    def __init__(self, user_id, access_hash):
        self.user_id, self.access_hash = user_id, access_hash


class _InputMentionName:
    kind = "inputMessageEntityMentionName"

    def __init__(self):
        self.offset = self.length = 0
        self.user_id = None


class _InputUserEmpty:
    pass


tgnet = types.ModuleType("org.telegram.tgnet")
tgnet.TLRPC = types.SimpleNamespace(
    TL_messageEntityMention=_Mention,
    TL_inputMessageEntityMentionName=_InputMentionName,
    TL_inputUserEmpty=_InputUserEmpty)
for name in ("org", "org.telegram"):
    sys.modules[name] = types.ModuleType(name)
sys.modules.update({"java": types.ModuleType("java"), "java.util": java_util,
                    "org.telegram.tgnet": tgnet})

# ---- загрузка плагина ----

plugin_path = Path(__file__).resolve().parent.parent / "plugin" / "mention_all.plugin"
loader = SourceFileLoader("mention_all_plugin", str(plugin_path))
spec = importlib.util.spec_from_loader("mention_all_plugin", loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

build = mod.build_mentions
chat_id = mod.chat_id_from_dialog

# ---- build_mentions ----
# участники: (user_id, username|None, имя)
text, spans = build("hi @all, wake up",
                    [(1, "ann_x", "Ann"), (2, None, "Bob")], 100)
assert text == "hi @ann_x Bob, wake up", text
# юзернеймованные пишутся как @username, остальные — именем
assert spans == [(3, 6, 1, "ann_x"), (10, 3, 2, None)], spans

# повторные токены убираются
text, spans = build("@all @all", [(5, "x_user", "X")], 100)
assert text == "@x_user", repr(text)

# utf-16: emoji до токена занимает 2 кодовые единицы
text, spans = build("\U0001F44B @all", [(9, None, "Z")], 100)
assert spans == [(3, 1, 9, None)], spans

# лимит
text, spans = build("@all", [(i, "u%d" % i, "") for i in range(10)], 3)
assert text == "@u0 @u1 @u2" and len(spans) == 3

# пустой список участников / без токена — текст не меняется
assert build("no token here", [(1, "a_u", "A")], 100)[0] == "no token here"
assert build("@all", [], 100) == ("@all", [])

# имя, содержащее @all, не зациклит повторный хук
text, spans = build("@all", [(1, None, "@all fan")], 100)
assert text == "fan" and spans == [(0, 3, 1, None)]

# регистр и защита от @allinside / @@all
assert build("пишите @ALL", [(1, "a_u", "A")], 100)[0] == "пишите @a_u"
assert build("@allinside", [(1, "a_u", "A")], 100)[0] == "@allinside"

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

# ---- fallback_text: текст после сбоя никогда не пустой ----

fb = mod.fallback_text
assert fb("@all") == "@all"           # одни токены — оставляем как есть
assert fb("@all привет") == "привет"
assert fb("  @all  ") == "  @all  "   # пустой результат недопустим
assert fb("текст") == "текст"
assert fb("@all @all") == "@all @all"  # всё съедено — как напечатано

# ---- pick_members: кого упоминать ----

pick = mod.pick_members
# себя выкидываем, ботов и удалённых — в резерв
entries = [(1, "me_x", "Me", False), (2, "ann", "Ann", False),
           (3, "", "Bot", True), (4, "", "Gone", True)]
assert pick(entries, 1) == ([(2, "ann", "Ann")], False)
# живых нет — упоминаем ботов/удалённых, а не отказываем
assert pick([(1, "", "Me", False), (3, "", "Bot", True)], 1) == (
    [(3, "", "Bot")], False)
# сравнение id врёт: «это я» съело весь список — отдаём всех (баг 1.1.3)
assert pick([(0, "ann", "Ann", False), (0, "", "Bob", False)], 0) == (
    [(0, "ann", "Ann"), (0, "", "Bob")], True)
# обычный случай: свой id отсекается, остальные остаются
assert pick([(7, "ann", "Ann", False), (8, "", "Bob", False)], 7) == (
    [(8, "", "Bob")], False)
# пусто — пусто, без падения
assert pick([], 1) == ([], True)

# ---- _response_users: getUser(0) отдаёт текущего пользователя ----

client_utils = types.ModuleType("client_utils")


class _User:
    def __init__(self, uid, username="", first_name="", access_hash=1000):
        self.id, self.username, self.first_name = uid, username, first_name
        self.last_name = ""
        self.access_hash = access_hash


class _MC:
    """Кэш клиента, ведущий себя как настоящий: getUser(0) — это вы."""

    def __init__(self, cache):
        self.cache = cache

    def getUser(self, uid):
        if int(uid) == 0:
            return _User(8617084680, "", "")  # как MessagesController
        return self.cache.get(int(uid))

    def getInputUser(self, user):
        if user is None:
            return _InputUserEmpty()
        return _InputUser(user.id, user.access_hash)


client_utils.get_messages_controller = lambda account=None: _MC(
    {5: _User(5, "ann_x", "Ann")})
sys.modules["client_utils"] = client_utils

plugin_ru = mod.MentionAllPlugin()
# участник с id=0 не должен превратиться в «вас», а кэш уточняет юзернейм
got = plugin_ru._response_users(7, ArrayList(
    [_User(0), _User(5, "", "Ann"), _User(6, "", "Bob")]))
assert [u.id for u in got] == [5, 6], [u.id for u in got]
assert got[0].username == "ann_x", got[0].username
assert got[1].username == "", got[1].username

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

# ---- тёплый кэш: MODIFY, текст и entities в одном проходе ----

mod.MentionAllPlugin._recent_fail.clear()
mod.MentionAllPlugin._members[(7, -123)] = (
    time.monotonic(),
    [(5, "ann_x", "Ann"), (6, "", "Bob"), (7, "", "Cara")],
    {6: _InputUser(6, 606), 7: _InputUser(7, 707)})
p = Params(-123, "hi @all")
res = plugin.on_send_message_hook(7, p)
# штатный путь клиента: тот же объект params, стратегия MODIFY
assert res is not None and res.strategy == mod.HookStrategy.MODIFY
assert res.params is p
assert p.message == "hi @ann_x Bob Cara", p.message
ents = p.entities
assert ents.size() == 3, ents
assert ents[0].kind == "mention" and ents[0].offset == 3 and ents[0].length == 6
assert ents[1].kind == "inputMessageEntityMentionName" and ents[1].offset == 10
assert ents[1].length == 3
assert ents[1].user_id.user_id == 6 and ents[1].user_id.access_hash == 606
assert ents[2].kind == "inputMessageEntityMentionName" and ents[2].offset == 14
assert ents[2].length == 4
assert ents[2].user_id.user_id == 7 and ents[2].user_id.access_hash == 707

# If an unnamed member has no resolvable InputUser, don't silently send only
# the username-based subset as if everyone were mentioned.
incomplete = Params(-123, "hi @all")
assert plugin._apply(7, incomplete, "message", incomplete.message,
                     [(5, "ann_x", "Ann"), (6, "", "Bob")],
                     {}) is None
assert incomplete.message == "hi @all"

# просроченный кэш не используется: отправка снова отменяется на сбор
mod.MentionAllPlugin._members[(7, -123)] = (
    time.monotonic() - 10_000, [(5, "ann_x", "Ann")], {})
assert plugin.on_send_message_hook(7, Params(-123, "@all")).strategy == (
    mod.HookStrategy.CANCEL)
mod.MentionAllPlugin._members.clear()
mod.MentionAllPlugin._recent_fail.clear()

# ---- причина сбоя доходит до журнала латиницей ----

attempted = []
real_import = __import__


def spy(name, *args, **kwargs):
    attempted.append(name)
    return real_import(name, *args, **kwargs)


mod.__builtins__["__import__"] = spy
try:
    plugin._journal_tell("no_members него упоминать: получено 3, лимит 100")
finally:
    mod.__builtins__["__import__"] = real_import
# русский текст не должен съесть событие целиком: тег и числа остаются
assert attempted and attempted[-1].startswith(
    "mention_all_error_no_members"), attempted
assert all(ord(c) < 128 for c in attempted[-1]), attempted[-1]

# ---- невидимые имена (U+FE0E) не должны давать пустые упоминания ----

label = mod.clean_label
assert label("\ufe0e") == ""
assert label("\ufe0e \ufe0e \ufe0e") == ""
assert label("  Аня  " ) == "Аня"
assert label("A\u200bb") == "Ab"            # zero-width space
assert label("Аня\ufe0e") == "Аня"
assert label("सचिन") == "सचिन"              # комбинирующие знаки — не мусор

# имя из одних невидимых символов -> видимая подпись, но пинг сохраняется
text, spans = build("@all", [(1, None, "\ufe0e"), (2, None, "\ufe0e"), (3, "ann", "Ann")], 100)
assert text == "Без имени · 1 Без имени · 2 @ann", repr(text)
assert spans == [(0, 13, 1, None), (14, 13, 2, None), (28, 4, 3, "ann")], spans

# пробельное имя сохраняется буквально, entity покрывает пробелы
text, spans = build("@all", [(11, None, "   "), (22, None, "  ")], 100)
assert text == "      ", repr(text)
assert spans == [(0, 3, 11, None), (4, 2, 22, None)], spans

# обычное имя остаётся как было
assert build("@all", [(1, None, "Ann")], 100)[0] == "Ann"

# ---- @all mention autocomplete ----

suggestion = mod.is_all_suggestion_prefix
assert suggestion("@")
assert suggestion("hello @a")
assert suggestion("hello @AlL")
assert not suggestion("hello @@all")
assert not suggestion("hello@all")
assert not suggestion("@allx")
assert not suggestion("@xyz")


class FakeChat:
    channel = False
    megagroup = False


class FakeFragment:
    def getCurrentChat(self):
        return self.chat


class FakeAdapter:
    def __init__(self):
        self.parentFragment = FakeFragment()
        self.parentFragment.chat = FakeChat()
        self.results = ArrayList()

    def getFoundContextBot(self):
        return None

    def getItem(self, position):
        return self.results[position] if position < len(self.results) else None

    def isBotContext(self):
        return False

    def isStickers(self):
        return False

    def isBotCommands(self):
        return False


class FakeHookParam:
    def __init__(self, adapter, args=(), result=None):
        self.thisObject = adapter
        self.args = list(args)
        self.result = result


class FakeMentionCell:
    def setText(self, text):
        self.text = text


class FakeHolder:
    def __init__(self):
        self.itemView = FakeMentionCell()


autocomplete = mod.MentionAllPlugin()
adapter = FakeAdapter()
autocomplete._before_mention_search(
    FakeHookParam(adapter, ("hello @al", len("hello @al"), None, False, False)))
results = ArrayList(["Alice"])
adapter.results = results
autocomplete._before_show_users_result(
    FakeHookParam(adapter, (results, {}, True)))
assert results == ["@all", "Alice"]
autocomplete._before_show_users_result(
    FakeHookParam(adapter, (results, {}, True)))
assert results == ["@all", "Alice"]  # repeated updates don't duplicate it

holder = FakeHolder()
bind = FakeHookParam(adapter, (holder, 0))
autocomplete._before_mention_bind(bind)
assert holder.itemView.text == "@all — mention everyone"
assert bind.result is None
bind = FakeHookParam(adapter, (holder, 2), result="untouched")
autocomplete._before_mention_bind(bind)
assert bind.result == "untouched"

# Non-matching input and broadcast channels never get the synthetic row.
autocomplete._before_mention_search(
    FakeHookParam(adapter, ("hello @allx", len("hello @allx"), None, False, False)))
assert not autocomplete._has_all_suggestion(adapter)
results = ArrayList(["Alice"])
autocomplete._before_show_users_result(
    FakeHookParam(adapter, (results, {}, True)))
assert results == ["Alice"]
adapter.parentFragment.chat.channel = True
autocomplete._before_mention_search(
    FakeHookParam(adapter, ("@all", 4, None, False, False)))
assert not autocomplete._has_all_suggestion(adapter)

print("ok")
