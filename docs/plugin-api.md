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
  `client_utils.send_request` need `network`, and Java method hooks need
  `hooks`. This last permission is powerful and is shown on the install sheet.
  A request without a grant is silently dropped and lands in the plugin
  activity log — declare what you use, or the plugin loads but does nothing.
- **Java method hooks (exteraless).** `BasePlugin.hook_method((class_name,
  method_name), before=callback, after=callback)` accepts a dotted class name;
  callbacks receive a `MethodHookParam` (`thisObject`, `args`, `result`) and
  `param.setResult(...)` can replace or skip the original call. The
  `MentionsAdapter` autocomplete inserts a `String` into its username results
  and renders it in the normal mention cell; selecting it follows
  `ChatActivity`'s normal text-replacement path. This hook surface is verified
  only against exteraless.
- **Outgoing messages.** `on_send_message_hook(account, params)` fires from
  `SendMessagesHelper.sendMessage` with the live
  `SendMessagesHelper.SendMessageParams`. Return
  `HookResult(strategy=HookStrategy.CANCEL)` to stop the send, or
  `HookStrategy.MODIFY` with `result.params` to replace it. Hooks fire for every
  account, including background ones: pass `account=` to every
  `get_*_controller` / `send_*` helper.
- **Mention entities.** The SDK markdown dialect has no `mention:` links and no
  text mentions. To ping a user without a username, build
  `TLRPC.TL_inputMessageEntityMentionName` (`offset`, `length`,
  `user_id` as an `InputUser` from `MessagesController.getInputUser(user)`); for
  `@username` spans build `TL_messageEntityMention`. Deliver them through the
  hook's own params: mutate `params.message` / `params.entities` and return
  `HookResult(strategy=HookStrategy.MODIFY, params=params)`. `sendMessage` reads
  `sendMessageParams.entities` **after** the hook returns (it does
  `sendMessageParams.entities` → `reqSend.entities`, `flags |= 8`), so entities
  set in place travel in the same client request. Do not cancel and re-send
  through the positional `sendMessage(message, peer, ..., entities, ...)`
  overload: 14 positional arguments are not marshalled reliably through
  Chaquopy, and a cancelled send loses the text the user typed. Chaquopy does
  not convert a Python list into the Java field: build a `java.util.ArrayList`.
- **Names can be invisible.** A Telegram profile can have a first name that is
  only variation selectors or format characters (`U+FE0E` is the common one).
  Such a name is non-empty as a string but renders as nothing, so a
  `mentionName` built on it turns into blank space. Preserve literal whitespace
  names as the entity text (the client supports clickable mentions over spaces);
  use a visible label containing the user ID only when the name has no visible
  text and is not whitespace.
- **Cache what the hook needs.** The hook is synchronous, participants come
  from the network. Fetch them on the first `@all`, keep them per
  `(account, peer)` with a TTL, cancel that one send while fetching, then
  re-send: the re-send passes the same hook, now with a warm cache, and hits
  the mutation path above.
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
