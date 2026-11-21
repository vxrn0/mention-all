# Writing plugins for the exteraGram host family

One `.plugin` file is the whole plugin: plain Python, loaded by Chaquopy at
runtime, no build step. The same file is expected to load in exteraGram,
exteraless and AyuGram; a client-specific API is the exception, not the rule.

- **Entry point and metadata.** Exactly one `BasePlugin` subclass plus
  module-level literals: `__id__`, `__name__`, `__description__`, `__author__`,
  `__version__`, `__app_version__`, `__sdk_version__`, `__permissions__`. The
  host parses them with AST; never compute them.
- **Permissions (exteraless).** Declared keys gate the plugin at registration
  points: the outgoing-message hook needs `messages.send`, raw TL requests via
  `client_utils.send_request` need `network`. A request without a grant is
  silently dropped and lands in the plugin activity log — declare what you use,
  or the plugin loads but does nothing.
- **Outgoing messages.** `on_send_message_hook(account, params)` fires from
  `SendMessagesHelper.sendMessage` with the live
  `SendMessagesHelper.SendMessageParams`. Return
  `HookResult(strategy=HookStrategy.CANCEL)` to stop the send, or
  `HookStrategy.MODIFY` with `result.params` to replace it. Hooks fire for every
  account, including background ones: pass `account=` to every
  `get_*_controller` / `send_*` helper.
- **Mention entities.** The SDK markdown dialect has no `mention:` links and no
  text mentions. To ping a user without a username, build
  `TLRPC.TL_messageEntityMentionName` yourself (`offset`, `length`, `user_id`)
  and attach the list to `params.entities` — `SendMessagesHelper` carries that
  field into the TL request. Chaquopy does not convert a Python list into the
  Java field: build a `java.util.ArrayList`.
- **Offsets are UTF-16.** Telegram counts entity offsets and lengths in UTF-16
  code units, not characters: `len(s.encode("utf-16-le")) // 2`.
- **TL field types are not interchangeable.** `channels.getParticipants`
  takes `TL_inputChannel`, not `TL_inputPeerChannel`: the `channel` field is
  `InputChannel`, and `TL_inputPeerChannel` is an `InputPeer` — Chaquopy
  throws `TypeError: Cannot convert ...` at request build time, killing the
  whole send. Check the declared field type in TLRPC before assigning.
- **Reentrancy.** A resend passes through the same outgoing hook. Strip the
  trigger token from any text you splice in, or the send loops forever.
- **Async only.** The hook runs synchronously on the send path; anything
  network-bound (fetching participants) must cancel the send, collect data via
  `send_request`, then resend from `run_on_ui_thread`. On failure resend the
  original params unchanged — a cancelled send that never comes back is lost
  user input.
- **Import hygiene.** Keep `org.telegram.*` and other host imports inside
  functions, not at module top: the file also has to parse and test on a
  desktop without Chaquopy.
