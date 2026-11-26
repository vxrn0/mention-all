"""Host-side self-check for mention_all.plugin without JVM.

Run: python3 tests/test_plugin.py (failure raises, silence means ok).
"""

import importlib.util
import json
import sys
import time
import types
from importlib.machinery import SourceFileLoader
from pathlib import Path

# ---- SDK stubs unavailable on desktop ----

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

    def set_setting(self, key, value, reload_settings=False):
        if not hasattr(self, "_settings"):
            self._settings = {}
        self._settings[key] = value

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


class _TLUser:
    def __init__(self):
        self.id = 0
        self.username = None
        self.first_name = None
        self.last_name = None
        self.bot = False
        self.self = False


tgnet = types.ModuleType("org.telegram.tgnet")
tgnet.TLRPC = types.SimpleNamespace(
    TL_messageEntityMention=_Mention,
    TL_inputMessageEntityMentionName=_InputMentionName,
    TL_inputUserEmpty=_InputUserEmpty,
    TL_user=_TLUser)


class _LocaleController:
    code = "en"

    @classmethod
    def getLocaleStringIso639(cls):
        return cls.code


class _ChatObject:
    @staticmethod
    def isChannelAndNotMegaGroup(chat):
        return bool(getattr(chat, "broadcast", False)) and not bool(getattr(chat, "megagroup", False))


messenger = types.ModuleType("org.telegram.messenger")
messenger.LocaleController = _LocaleController
messenger.ChatObject = _ChatObject

for name in ("org", "org.telegram"):
    sys.modules[name] = types.ModuleType(name)
sys.modules.update({
    "java": types.ModuleType("java"),
    "java.util": java_util,
    "org.telegram.tgnet": tgnet,
    "org.telegram.messenger": messenger,
})

# ---- load plugin ----

plugin_path = Path(__file__).resolve().parent.parent / "plugin" / "mention_all.plugin"
loader = SourceFileLoader("mention_all_plugin", str(plugin_path))
spec = importlib.util.spec_from_loader("mention_all_plugin", loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

assert mod.__icon__ == "exteraPlugins/1"
assert mod.__author__ == "@vxrn0"

build = mod.build_mentions
chat_id = mod.chat_id_from_dialog

# ---- build_mentions ----
text, spans = build("hi @all, wake up",
                    [(1, "ann_x", "Ann"), (2, None, "Bob")], 100)
assert text == "hi @ann_x Bob, wake up", text
assert spans == [(3, 6, 1, "ann_x"), (10, 3, 2, None)], spans

# duplicate tokens are removed
text, spans = build("@all @all", [(5, "x_user", "X")], 100)
assert text == "@x_user", repr(text)

# UTF-16 offsets: emoji before token takes 2 code units
text, spans = build("\U0001F44B @all", [(9, None, "Z")], 100)
assert spans == [(3, 1, 9, None)], spans

# mention cap
text, spans = build("@all", [(i, "u%d" % i, "") for i in range(10)], 3)
assert text == "@u0 @u1 @u2" and len(spans) == 3

# empty members / no token leaves text untouched
assert build("no token here", [(1, "a_u", "A")], 100)[0] == "no token here"
assert build("@all", [], 100) == ("@all", [])

# @all inside a member's display name cannot loop the resend hook
text, spans = build("@all", [(1, None, "@all fan")], 100)
assert text == "fan" and spans == [(0, 3, 1, None)]

# case-insensitive and avoids @allinside / @@all
assert build("ping @ALL", [(1, "a_u", "A")], 100)[0] == "ping @a_u"
assert build("@allinside", [(1, "a_u", "A")], 100)[0] == "@allinside"

# ---- chat_id_from_dialog ----
assert chat_id(-123) == 123            # basic group or -channel_id
assert chat_id(-1000000000123) == 123  # supergroup dialog_id
assert chat_id(12345) is None          # private chat
assert chat_id(0) is None

# ---- _jlist ----
class FakeJavaList:
    def __init__(self, *items):
        self._items = list(items)

    def size(self):
        return len(self._items)

    def get(self, i):
        return self._items[i]


assert mod._jlist(FakeJavaList(1, 2, 3)) == [1, 2, 3]
assert mod._jlist(None) == []

# ---- fallback_text ----
fb = mod.fallback_text
assert fb("@all") == "@all"
assert fb("@all hello") == "hello"
assert fb("  @all  ") == "  @all  "
assert fb("plain") == "plain"
assert fb("@all @all") == "@all @all"

# ---- pick_members ----
pick = mod.pick_members
entries = [(1, "me_x", "Me", False), (2, "ann", "Ann", False),
           (3, "", "Bot", True), (4, "", "Gone", True)]
assert pick(entries, 1) == ([(2, "ann", "Ann")], False)
assert pick([(1, "", "Me", False), (3, "", "Bot", True)], 1) == (
    [(3, "", "Bot")], False)
assert pick([(0, "ann", "Ann", False), (0, "", "Bob", False)], 0) == (
    [(0, "ann", "Ann"), (0, "", "Bob")], True)
assert pick([(7, "ann", "Ann", False), (8, "", "Bob", False)], 7) == (
    [(8, "", "Bob")], False)
assert pick([], 1) == ([], True)

# ---- _response_users ----
client_utils = types.ModuleType("client_utils")


class _User:
    def __init__(self, uid, username="", first_name="", access_hash=1000):
        self.id, self.username, self.first_name = uid, username, first_name
        self.last_name = ""
        self.access_hash = access_hash


class _MC:
    def __init__(self, cache):
        self.cache = cache

    def getUser(self, uid):
        if int(uid) == 0:
            return _User(8617084680, "", "")
        return self.cache.get(int(uid))

    def getInputUser(self, user):
        if user is None:
            return _InputUserEmpty()
        return _InputUser(user.id, user.access_hash)


client_utils.get_messages_controller = lambda account=None: _MC(
    {5: _User(5, "ann_x", "Ann")})
sys.modules["client_utils"] = client_utils

plugin_ru = mod.MentionAllPlugin()
got = plugin_ru._response_users(7, ArrayList(
    [_User(0), _User(5, "", "Ann"), _User(6, "", "Bob")]))
assert [u.id for u in got] == [5, 6], [u.id for u in got]
assert got[0].username == "ann_x", got[0].username
assert got[1].username == "", got[1].username

# ---- outgoing hook routing ----
class Params:
    def __init__(self, peer, message, caption=None):
        self.peer, self.message, self.caption = peer, message, caption


plugin = mod.MentionAllPlugin()

assert plugin.on_send_message_hook(0, Params(123, "@all")) is None
assert plugin.on_send_message_hook(0, Params(-123, "hi")) is None
assert plugin.on_send_message_hook(0, Params(-123, None, None)) is None
plugin._settings = {"enabled": False}
assert plugin.on_send_message_hook(0, Params(-123, "@all")) is None

plugin._settings = {"enabled": True}
seen = []
plugin._mention_all = lambda *a: seen.append(a)
res = plugin.on_send_message_hook(7, Params(-123, "go @all"))
assert res is not None and res.strategy == mod.HookStrategy.CANCEL
assert seen and seen[0][0] == 7

res = plugin.on_send_message_hook(7, Params(-123, None, "cap @all"))
assert res is not None and res.strategy == mod.HookStrategy.CANCEL

# failure latch prevents infinite retry loops
p = Params(-123, "go @all")
plugin._mention_all = lambda *a: seen.append(a)
assert plugin.on_send_message_hook(7, p).strategy == mod.HookStrategy.CANCEL
mod.MentionAllPlugin._recent_fail.clear()
mod.MentionAllPlugin._recent_fail[(int(p.peer), "go @all")] = time.monotonic()
seen.clear()
assert plugin.on_send_message_hook(7, p) is None
assert not seen

# ---- warm cache: MODIFY + entities + frontend mask remembered ----
mod.MentionAllPlugin._recent_fail.clear()
mod.MentionAllPlugin._masked.clear()
mod.MentionAllPlugin._masked_loaded = True
mod.MentionAllPlugin._members[(7, -1000000000123)] = (
    time.monotonic(),
    [(5, "ann_x", "Ann"), (6, "", "Bob"), (7, "", "Cara")],
    {6: _InputUser(6, 606), 7: _InputUser(7, 707)})
p = Params(-1000000000123, "hi @all")
res = plugin.on_send_message_hook(7, p)
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

# unresolvable InputUser aborts cleanly
incomplete = Params(-123, "hi @all")
assert plugin._apply(7, incomplete, "message", incomplete.message,
                     [(5, "ann_x", "Ann"), (6, "", "Bob")],
                     {}) is None
assert incomplete.message == "hi @all"

# expired cache triggers fresh fetch
mod.MentionAllPlugin._members[(7, -123)] = (
    time.monotonic() - 10_000, [(5, "ann_x", "Ann")], {})
assert plugin.on_send_message_hook(7, Params(-123, "@all")).strategy == (
    mod.HookStrategy.CANCEL)
mod.MentionAllPlugin._members.clear()
mod.MentionAllPlugin._recent_fail.clear()

# ---- frontend masking (MessageObject hooks + persistence) ----
class FakeMessageOwner:
    def __init__(self, message, out=True, entities=None):
        self.message = message
        self.out = out
        self.entities = entities if entities is not None else ArrayList(["e1", "e2"])


class FakeMessageObject:
    def __init__(self, dialog_id, message, out=True):
        self._dialog_id = dialog_id
        self.messageOwner = FakeMessageOwner(message, out=out)
        self.messageText = message

    def getDialogId(self):
        return self._dialog_id


class FakeHookParam:
    def __init__(self, target, args=(), result=None):
        self.thisObject = target
        self.args = list(args)
        self.result = result


# Works across supergroup dialog_id formats (-1000000000123 at send vs -123 on MessageObject).
msg = FakeMessageObject(-123, "hi @ann_x Bob Cara", out=True)
orig_entities = msg.messageOwner.entities
plugin._after_message_set_type(FakeHookParam(msg))
assert msg.messageText == "hi @all", msg.messageText

# Layout hook temporarily clears entities and restores them afterward.
plugin._before_message_layout(FakeHookParam(msg))
assert msg.messageText == "hi @all"
assert msg.messageOwner.entities.size() == 0
plugin._after_message_layout(FakeHookParam(msg))
assert msg.messageOwner.entities is orig_entities
assert msg.messageOwner.message == "hi @ann_x Bob Cara"  # server/DB text untouched

# Caption hook swaps both message and entities temporarily and restores both.
cap_msg = FakeMessageObject(-123, "hi @ann_x Bob Cara", out=True)
cap_entities = cap_msg.messageOwner.entities
plugin._before_message_caption(FakeHookParam(cap_msg))
assert cap_msg.messageOwner.message == "hi @all"
assert cap_msg.messageOwner.entities.size() == 0
plugin._after_message_caption(FakeHookParam(cap_msg))
assert cap_msg.messageOwner.message == "hi @ann_x Bob Cara"
assert cap_msg.messageOwner.entities is cap_entities

# Incoming messages (out=False) are never masked.
incoming = FakeMessageObject(-123, "hi @ann_x Bob Cara", out=False)
plugin._after_message_set_type(FakeHookParam(incoming))
assert incoming.messageText == "hi @ann_x Bob Cara"

# DialogCell preview hook swaps messageOwner.message/entities and restores both.
class FakeDialogCell:
    def __init__(self, msg):
        self._msg = msg

    def getMessage(self):
        return self._msg


dlg_msg = FakeMessageObject(-123, "hi @ann_x Bob Cara", out=True)
dlg_entities = dlg_msg.messageOwner.entities
dlg_cell = FakeDialogCell(dlg_msg)
plugin._before_dialog_preview(FakeHookParam(dlg_cell))
assert dlg_msg.messageOwner.message == "hi @all"
assert dlg_msg.messageOwner.entities.size() == 0
plugin._after_dialog_preview(FakeHookParam(dlg_cell))
assert dlg_msg.messageOwner.message == "hi @ann_x Bob Cara"
assert dlg_msg.messageOwner.entities is dlg_entities

# Persisted masked map reloads cleanly after restart.
saved_json = plugin._settings[mod._MASK_KEY]
assert isinstance(json.loads(saved_json), dict)
mod.MentionAllPlugin._masked.clear()
mod.MentionAllPlugin._masked_loaded = False
reloaded = FakeMessageObject(-123, "hi @ann_x Bob Cara", out=True)
plugin._after_message_set_type(FakeHookParam(reloaded))
assert reloaded.messageText == "hi @all"

# ---- ASCII journal tag ----
attempted = []
real_import = __import__


def spy(name, *args, **kwargs):
    attempted.append(name)
    return real_import(name, *args, **kwargs)


mod.__builtins__["__import__"] = spy
try:
    plugin._journal_tell("no_members некого упоминать: 3, 100")
finally:
    mod.__builtins__["__import__"] = real_import
assert attempted and attempted[-1].startswith("mention_all_error_no_members"), attempted
assert all(ord(c) < 128 for c in attempted[-1]), attempted[-1]

# ---- invisible & whitespace names ----
label = mod.clean_label
assert label("\ufe0e") == ""
assert label("\ufe0e \ufe0e \ufe0e") == ""
assert label("  Ann  ") == "Ann"
assert label("A\u200bb") == "Ab"
assert label("Ann\ufe0e") == "Ann"
assert label("सचिन") == "सचिन"

text, spans = build("@all", [(1, None, "\ufe0e"), (2, None, "\ufe0e"), (3, "ann", "Ann")], 100)
assert text == "Unnamed · 1 Unnamed · 2 @ann", repr(text)
assert spans == [(0, 11, 1, None), (12, 11, 2, None), (24, 4, 3, "ann")], spans

text, spans = build("@all", [(11, None, "   "), (22, None, "  ")], 100)
assert text == "      ", repr(text)
assert spans == [(0, 3, 11, None), (4, 2, 22, None)], spans

assert build("@all", [(1, None, "Ann")], 100)[0] == "Ann"

# ---- bilingual localization (English default, Russian when client is ru) ----
_LocaleController.code = "en"
en_items = plugin.create_settings()
assert en_items[1].text == "Enable"
assert en_items[2].text == "Mention limit"
assert en_items[3].text == "Self-test"

_LocaleController.code = "ru-RU"
ru_items = plugin.create_settings()
assert ru_items[1].text == "Включить"
assert ru_items[2].text == "Максимум упоминаний"
assert ru_items[3].text == "Самопроверка"
_LocaleController.code = "en"

# ---- @all mention autocomplete ----
suggestion = mod.is_all_suggestion_prefix
assert suggestion("@")
assert suggestion("hello @a")
assert suggestion("hello @AlL")
assert not suggestion("hello @@all")
assert not suggestion("hello@all")
assert not suggestion("@allx")
assert not suggestion("@xyz")


class FakeSupergroup:
    # Real TLRPC.TL_channel has broadcast/megagroup and NO .channel attribute.
    broadcast = False
    megagroup = True


class FakeBroadcastChannel:
    broadcast = True
    megagroup = False


class FakeFragment:
    def __init__(self, chat):
        self.chat = chat

    def getCurrentChat(self):
        return self.chat


class FakeAdapter:
    def __init__(self, chat):
        self.parentFragment = FakeFragment(chat)

    def getFoundContextBot(self):
        return None

    def isBotContext(self):
        return False

    def isStickers(self):
        return False

    def isBotCommands(self):
        return False


autocomplete = mod.MentionAllPlugin()
adapter = FakeAdapter(FakeSupergroup())
autocomplete._before_mention_search(
    FakeHookParam(adapter, ("hello @al", len("hello @al"), None, False, False)))
results = ArrayList([_User(1, "alice", "Alice")])
autocomplete._before_show_users_result(
    FakeHookParam(adapter, (results, {}, True)))
assert results.size() == 2
assert results[0].id == mod._ALL_USER_ID
assert results[0].username == "all"
assert results[0].first_name == "Mention everyone"
# Repeated calls do not duplicate the synthetic @all row.
autocomplete._before_show_users_result(
    FakeHookParam(adapter, (results, {}, True)))
assert results.size() == 2

# Russian client gets Russian label for the synthetic @all row.
_LocaleController.code = "ru"
ru_results = ArrayList()
autocomplete._before_show_users_result(
    FakeHookParam(adapter, (ru_results, {}, True)))
assert ru_results[0].first_name == "Упомянуть всех"
_LocaleController.code = "en"

# Non-matching input and broadcast channels never get @all.
autocomplete._before_mention_search(
    FakeHookParam(adapter, ("hello @allx", len("hello @allx"), None, False, False)))
assert not autocomplete._has_all_suggestion(adapter)
other = ArrayList([_User(1, "alice", "Alice")])
autocomplete._before_show_users_result(
    FakeHookParam(adapter, (other, {}, True)))
assert other.size() == 1

channel_adapter = FakeAdapter(FakeBroadcastChannel())
autocomplete._before_mention_search(
    FakeHookParam(channel_adapter, ("@all", 4, None, False, False)))
assert not autocomplete._has_all_suggestion(channel_adapter)

print("ok")
