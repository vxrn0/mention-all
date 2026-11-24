---
name: exteraless-plugin-dev
description: Build, debug, hook, test, and release Python (and DEX/Elyx) plugins for exteraGram, exteraless, and AyuGram. Use whenever writing or modifying `.plugin` files, Xposed/Java method hooks, `TLRPC` requests, `SendMessagesHelper` / `MessageObject` / `MentionsAdapter` / `ImageReceiver` hooks, plugin settings, permissions, or host-side mock tests.
---

# exteraGram / exteraless / AyuGram Plugin Development

Single-file Python plugins run on Chaquopy (Python 3.11) inside Android Telegram forks sharing the `BasePlugin` SDK (`exteraGram`, `exteraless`, `AyuGram`).

## Non-Negotiable Workflow

Follow this order every time. Skipping step 1 is the #1 cause of broken plugins.

1. **Verify Java/SDK contracts against source BEFORE writing code.**
   Never guess a `TLRPC` field name, Java method signature, overload, or permission key.
   If `exteraless` source is not on disk, sparse-clone only the files you need into `/tmp/opencode/exteraless-src`:
   ```sh
   git clone --quiet --filter=blob:none --depth=1 --sparse \
     https://github.com/exteraless/exteraless.git /tmp/opencode/exteraless-src
   cd /tmp/opencode/exteraless-src
   git sparse-checkout set TMessagesProj/src/main/python \
     TMessagesProj/src/main/java/app/exteraless/plugins \
     TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java --skip-checks
   ```
   Add any UI/messenger class you intend to hook (`MentionsAdapter.java`, `MessageObject.java`, `SendMessagesHelper.java`, `ChatActivity.java`, `ImageReceiver.java`) and `grep` exact field names and overloads before coding.

2. **Declare exact top-level literal metadata.**
   The loader parses metadata with `ast` — never compute it dynamically:
   ```python
   __id__ = "my_plugin"            # 2-32 chars, letters/digits/_/-
   __name__ = "My Plugin"
   __description__ = "Short English description."
   __author__ = "@vxrn0"
   __version__ = "1.0.0"           # strict MAJOR.MINOR.PATCH
   __icon__ = "exteraPlugins/1"    # StickerPackShortName/index (no bundled images)
   __app_version__ = ">=12.10.6"
   __sdk_version__ = ">=1.4.5.3"
   __permissions__ = ["messages.send", "network", "hooks"]  # exteraless gates
   ```

3. **Keep desktop-safe import hygiene.**
   Put all host/Java imports (`org.telegram.*`, `java.*`, `client_utils`, `android_utils`, `ui.alert`, `ui.bulletin`) **inside functions**, not at module top, so `py_compile` and host-side mock tests run without Chaquopy.

4. **Ship English-first bilingual UI.**
   Code, comments, `__description__`, and default labels are English. User-facing strings follow Telegram's language via `LocaleController.getLocaleStringIso639()` (`ru` → Russian, everything else → English).

5. **Test locally before claiming done.**
   Run `python3 -m py_compile plugin/<id>.plugin`, host-side mock tests (`python3 tests/test_*.py`), and metadata/release checks (`scripts/package_release.py --check`). Always state clearly that host mocks do not replace a phone test, and name which clients were actually verified.

## Top 10 Traps (Read Before Editing)

1. **Missing `__permissions__` on exteraless** → hooks/requests silently do nothing and land in the plugin activity log. Always declare every key you use: `messages.send`, `messages.read`, `network`, `files`, `intents`, `settings`, `hooks`, `native`.
2. **Guessing `TLRPC` fields** → `TLRPC.Chat` has **no** `.channel` field (use `ChatObject.isChannelAndNotMegaGroup(chat)`). `ChannelParticipant` has `peer`, not `user_id`. `channels.getParticipants` requires `TL_inputChannel`, not `TL_inputPeerChannel`.
3. **Forgetting `account=` in callbacks** → background accounts also fire hooks. Pass `account` to every `get_*_controller(account)` / `send_request(..., account=account)` or use `self.client(account)`.
4. **Iterating Java `ArrayList` in Python** → raises `TypeError` on Chaquopy proxies. Loop with `for i in range(lst.size()): lst.get(i)`. Conversely, assign a `java.util.ArrayList()` (not a Python `list`) to Java fields like `params.entities`.
5. **Breaking Java generic types** → putting a `String` into `ArrayList<TLObject>` (e.g. `MentionsAdapter.searchResultUsernames`) triggers `ClassCastException` on `CHECKCAST TLObject`. Insert a real synthetic `TLRPC.TL_user` instead.
6. **Python `len()` for Telegram entity offsets** → Telegram counts **UTF-16 code units** (`len(s.encode("utf-16-le")) // 2`), not Python code points. Emoji before an entity shifts offsets by +1.
7. **Wrong mention entity class on outgoing sends** → use `TL_inputMessageEntityMentionName` with `MessagesController.getInputUser(user)`, NOT `TL_messageEntityMentionName`. Mutate `params.message` and `params.entities` in place and return `HookStrategy.MODIFY`.
8. **`MessagesController.getUser(0)` returns the current user, not `None`** → skip `uid == 0` when reading users from TL responses.
9. **Supergroup `dialog_id` mismatch** → `SendMessageParams.peer` can be `-1000000000000 - id` while `MessageObject.getDialogId()` returns `-id`. Normalize both to a positive `chat_id` before keying caches/maps.
10. **Leaving mutated Java state behind or losing user messages** → any hook that mutates a Java object (radius/mark on `ImageReceiver`, `entities`/`message` on `MessageObject`) must save the baseline and restore it in `after_hooked_method` / `on_plugin_unload`. Any cancelled outgoing send that fails must resend the original message unchanged.

## References

Load only the reference file relevant to your task:

- **SDK, metadata, lifecycle, settings, bilingual UI, multi-account**: [references/sdk-and-lifecycle.md](references/sdk-and-lifecycle.md)
- **Xposed Java hooks, `HookFilter`, Chaquopy interop, class proxies, DEX/Elyx**: [references/hooks-and-chaquopy.md](references/hooks-and-chaquopy.md)
- **Telegram `TLRPC` / `SendMessagesHelper` / `MentionsAdapter` / `MessageObject` traps**: [references/telegram-api-traps.md](references/telegram-api-traps.md)
- **Host-side mock testing, packaging, `SHA256SUMS`, release verification**: [references/testing-and-release.md](references/testing-and-release.md)
