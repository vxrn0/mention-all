# SDK, Lifecycle, Permissions, Settings & Localization

## Metadata & Permissions

Metadata must be top-level literal assignments (AST-parsed):

- `__id__`: `2-32` chars (`[A-Za-z][A-Za-z0-9_-]*`).
- `__name__`, `__description__` (English, markdown allowed), `__author__` (`"@handle"`), `__version__` (`"MAJOR.MINOR.PATCH"`).
- `__icon__`: `"StickerPackShortName/index"` (e.g. `"exteraPlugins/1"`). Plugins cannot bundle image files; `PluginIcons` loads the sticker asynchronously from Telegram.
- `__app_version__` (e.g. `">=12.10.6"`), `__sdk_version__` (e.g. `">=1.4.5.3"`).
- `__requirements__`: pure-Python PEP 508 wheels only (optional).
- `__permissions__` (exteraless permission gates — omit unused keys, declare every used key):
  - `messages.send` — `add_on_send_message_hook`, `send_text`, `sendMessage`
  - `messages.read` — reading messages/history
  - `network` — `client_utils.send_request` and network calls
  - `hooks` — `hook_method`, `hook_all_methods`, `hook_all_constructors`, class proxies, `deoptimizeMethod` (powerful permission; warn in README)
  - `files`, `intents`, `settings`, `native` — only if actually used.

## `BasePlugin` Lifecycle & Event Hooks

Exactly one `BasePlugin` subclass per `.plugin` file.

- Register hooks in `on_plugin_load(self)`; clean up custom state/views in `on_plugin_unload(self)`.
- Remember: implementing `on_send_message_hook` does nothing until you call `self.add_on_send_message_hook()` in `on_plugin_load()`.
- Request hooks: `self.add_hook("TL_messages_setTyping")` → `pre_request_hook(self, request_name, account, request)` and `post_request_hook(self, request_name, account, response, error)`.
- Update hooks: `on_update_hook(self, update_name, account, update)` and `on_updates_hook(self, container_name, account, updates)`.
- Return `HookResult(strategy=HookStrategy.DEFAULT | CANCEL | MODIFY | MODIFY_FINAL, params=...)` (or `request=` / `response=` / `update=`). Returning `None` is equivalent to `DEFAULT`.
- Class-level dicts survive in-process plugin reloads; thread-local state (`threading.local()`) keeps hook stacks thread-safe.

## Multi-Account Rule

Every logged-in account fires hooks, including background accounts. Always pass `account` to every helper:

- `get_messages_controller(account)`
- `get_send_messages_helper(account)`
- `get_user_config(account)`
- `send_request(req, callback, account=account)`
- or `self.client(account)` (SDK `>=1.4.5.0`).

Never silently rely on `UserConfig.selectedAccount` inside an account-scoped hook.

## Threading & UI Helpers

- Never run network I/O, disk I/O, or heavy loops on the UI thread: offload with `client_utils.run_on_queue(fn)`.
- Never touch Android views, dialogs, or `SendMessagesHelper.sendMessage` from a background thread: dispatch with `android_utils.run_on_ui_thread(fn)`.
- Feedback: `ui.bulletin.BulletinHelper` for transient toasts; `ui.alert.AlertDialogBuilder` when the user must actually read an error or diagnostic report.

## Settings & Persistence (`ui.settings`)

Available items: `Header`, `Divider`, `Switch`, `Selector`, `Input`, `EditText`, `Text`, `Custom` (with `SimpleSettingFactory`).

- Read/write settings with `self.get_setting(key, default)` and `self.set_setting(key, value)`.
- Hidden internal keys (e.g. `"_masked_map"` storing compact JSON) work with `get_setting` / `set_setting` and persist across app restarts. Cap persisted collections (e.g. 200 entries) and avoid storing raw PII.

## Bilingual EN/RU Helper (English Default)

```python
def _app_language(self) -> str:
    try:
        from org.telegram.messenger import LocaleController
        code = str(LocaleController.getLocaleStringIso639() or "en").lower()
    except Exception:
        code = "en"
    return "ru" if code.split("-")[0].split("_")[0] == "ru" else "en"

def _text(self, english: str, russian: str) -> str:
    return russian if self._app_language() == "ru" else english
```

Use `self._text(en, ru)` for all settings labels, subtexts, dialogs, errors, and synthetic UI strings.
