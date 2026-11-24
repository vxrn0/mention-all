# Xposed Java Hooks, Chaquopy Interop, DEX & Elyx

## `BasePlugin.hook_method`

Two ways to register a Java method hook (requires `"hooks"` permission on exteraless):

1. **Simple `(class_name, method_name)` pair** (when there is a single overload, or you want all overloads):
   ```python
   hook = self.hook_method(
       ("org.telegram.ui.Adapters.MentionsAdapter", "showUsersResult"),
       before=self._before_show_users_result,
   )
   ```
2. **Exact overload via reflection** (required when hooking one specific overload, e.g. `ImageReceiver.setRoundRadius(int)` vs `setRoundRadius(int, int, int, int)`):
   Normalize the Chaquopy class proxy first with `hook_utils._as_class(clazz)`, inspect `getDeclaredMethods()`, match `method.getName()` + `getParameterTypes()`, call `method.setAccessible(True)`, then pass the `java.lang.reflect.Method` to `self.hook_method(method, handler, filters=...)`.

### Handler Protocol & `MethodHookParam`

- `before_hooked_method(param)` / `after_hooked_method(param)` (or `before=` / `after=` callables).
- `param.thisObject`, `param.args` (indexable/mutable), `param.result` (or `param.getResult()` / `param.setResult(val)`).
- Setting `param.result = value` (including `None`) inside `before_hooked_method` skips the original Java method.
- Always wrap hook callbacks in `try / except Exception` and log — an uncaught exception triggers the watchdog and disables the plugin.
- Register unrelated hook groups independently so one failing group unhooks only itself and does not break the rest of the plugin.

### Hot Paths & `HookFilter`

Never enter Python on every frame (`draw()`, `onDraw()`, `measure()`) for unrelated views. Gate hot hooks on the Java side with `HookFilter.condition(...)`:

```python
HookFilter.condition('thisObject.getMark() != null && thisObject.getMark().equals("botile:bot") && args[1] == null')
```

### State Preservation Rule

If a hook mutates a Java object:
- **Short-lived swap** (e.g. clearing `messageOwner.entities` during `MessageObject.generateLayout`): push `(msg, owner, saved)` onto a `threading.local()` stack in `before`, and pop/restore in `after` (match `stack[-1][0] is param.thisObject`).
- **Persistent UI override** (e.g. `ImageReceiver` radius/mark): store the app's baseline per receiver in a `WeakHashMap`, avoid clobbering marks set by other code, and restore baselines on clear and `on_plugin_unload()`.

## Chaquopy / Java Interop Traps

- **Java `List` is not Python-iterable**:
  ```python
  def _jlist(java_list) -> list:
      return [java_list.get(i) for i in range(java_list.size())] if java_list is not None else []
  ```
- **Python `list` does not convert to `java.util.ArrayList` for Java fields**: construct `from java.util import ArrayList` and call `.add(...)`.
- **Generic erasure still checks casts**: putting a `String` into `ArrayList<TLObject>` crashes when Java iterates `TLObject obj = it.next()`. Match the declared element type.
- **Signed 32-bit colors**: Android `Paint.setColor(int)` expects signed `int32`:
  ```python
  def _signed_color(value: int) -> int:
      value = int(value) & 0xFFFFFFFF
      return value - 0x100000000 if value & 0x80000000 else value
  ```
- **Private methods & R8/ART**: prefer `public` methods (`setType`, `generateLayout`, `generateCaption`, `searchUsernameOrHashtag`). If you must hook a `private` method (like `MentionsAdapter.showUsersResult`), verify in the client source that it has multiple/lambda callers and isn't trivially inlined, and verify on-device.

## Java Class Proxies, Elyx & DEX Plugins

- **Java Class Proxy (`extera_utils.classes`)**: use `@java_subclass`, `@joverride`, `@jmethod`, `jfield` when you must subclass an Android/Telegram Java class in Python.
- **Elyx (multi-file plugins, SDK `>=1.4.5.3`)**: use when a plugin needs multiple modules, bundled assets, localization files, or wheels (`refmap.yml` + `metainfo.yml`, built with `ElyxBuilder` / `elyb build`).
- **DEX plugins (Java/Kotlin compiled to `classes.dex`)**: use only when Python/Chaquopy hook overhead is unacceptable (e.g. heavy rendering/crypto). Compile an Android library against `exteragram.jar` stubs (generated via `exteralib`), run D8 to produce `classes.dex`, and load it from a thin Python loader plugin.
