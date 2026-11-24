# Verified Telegram / exteraless API Traps

Every item below was verified directly against `exteraless` Java sources (`TLRPC.java`, `ChatObject.java`, `UserObject.java`, `SendMessagesHelper.java`, `MentionsAdapter.java`, `MessageObject.java`).

## Outgoing Messages & Mention Entities (`SendMessagesHelper`)

- **Do not call the 14-arg positional `sendMessage(...)` overload** through Chaquopy — marshalling fails or drops fields. Instead, mutate `params.message` (or `params.caption`) and `params.entities` (`java.util.ArrayList`) in place inside `on_send_message_hook` and return `HookResult(strategy=HookStrategy.MODIFY, params=params)`. `SendMessagesHelper.sendMessage` reads `sendMessageParams.entities` **after** the hook returns.
- **Mention entities**:
  - Users with a username: `@username` + `TLRPC.TL_messageEntityMention` (`offset`, `length`).
  - Users without a username: display name + `TLRPC.TL_inputMessageEntityMentionName` (`offset`, `length`, `user_id = MessagesController.getInputUser(user)`). **Never** use `TL_messageEntityMentionName` on outgoing sends, and verify `input_user` is not `None` or `TL_inputUserEmpty`.
- **UTF-16 offsets**: Telegram counts entity offsets and lengths in UTF-16 code units:
  ```python
  def utf16len(s: str) -> int:
      return len(s.encode("utf-16-le")) // 2
  ```
- **Async fetch-and-resend**: `on_send_message_hook` is synchronous. If you need network data:
  1. Cache per `(account, peer)` with a TTL.
  2. On cache miss, kick off `send_request(...)` and return `HookResult(strategy=HookStrategy.CANCEL)`.
  3. On completion, populate cache and resend via `run_on_ui_thread(lambda: get_send_messages_helper(account).sendMessage(params))` — the resend re-enters the hook with a warm cache and takes the `MODIFY` path.
  4. Strip trigger tokens from any spliced text to prevent re-entrancy loops, keep a `(peer, text)` failure TTL latch, and on failure resend the original text (never an empty string) so user input is never lost.

## `TLRPC` & `MessagesController` Gotchas

- **`TLRPC.Chat` has NO `.channel` field.** Check group vs broadcast channel with `ChatObject.isChannelAndNotMegaGroup(chat)` (true for broadcast channels, false for basic groups and supergroups/megagroups).
- **`channels.getParticipants` takes `TL_inputChannel`**, not `TL_inputPeerChannel` (assigning an `InputPeer` throws `TypeError` in Chaquopy).
- **`ChannelParticipant` has `peer`, not `user_id`.** Read users from `response.users` and enrich from `MessagesController.getUser(uid)` only when `uid != 0` and `cached.id == uid`.
- **`MessagesController.getUser(0)` returns the current logged-in user**, NOT `None`. Always skip `uid == 0`.
- **Supergroup `dialog_id` formats**: `SendMessageParams.peer` can be `-1000000000000 - id` while `MessageObject.getDialogId()` sets `-channel_id`. Normalize both via:
  ```python
  SUPERGROUP_FLAG = -1000000000000
  def chat_id_from_dialog(dialog_id: int):
      if SUPERGROUP_FLAG < dialog_id < 0:
          return -dialog_id
      if dialog_id <= SUPERGROUP_FLAG:
          return -dialog_id + SUPERGROUP_FLAG
      return None
  ```
- **Invisible profile names**: names made only of variation selectors / format chars (`U+FE0E`, `Cf`/`Cc`/`Cs`/`Co`) render blank under `mentionName` → replace with a visible fallback like `Unnamed · <id>`. Literal whitespace names (`"   "`) are valid clickable mentions in Telegram and can be preserved verbatim.

## Mention Autocomplete (`MentionsAdapter`)

- Hook `searchUsernameOrHashtag(CharSequence, int, ArrayList, boolean, boolean)` (`before`) to check `enabled`, group chat (`not ChatObject.isChannelAndNotMegaGroup(chat)`), `not usernameOnly`, `not forSearch`, and cursor prefix (`args[0]` sliced to `args[1]`). Store per-adapter state in a `WeakHashMap`.
- Hook `showUsersResult(ArrayList, LongSparseArray, boolean)` (`before`) and prepend a synthetic `TLRPC.TL_user` (`id = -5`, `username = "all"`, `first_name = ...`, `bot = False`, `self = False`) when not already at index 0.
- Because `TL_user` is a `TLObject` with a public username, `MentionCell.setUser`, `AvatarDrawable.getColorIndex` (uses `Math.abs`), `ChatActivity`, and `MentionsContainerView` all render and insert `@all ` natively with no `onBindViewHolder` hack.

## Local Frontend Display Masking (`MessageObject`)

To display different text locally for outgoing messages (`owner.out == True`) while sending full text + entities to Telegram servers:
- Hook `MessageObject.setType()` (`after`): if `str(msg.messageText or "") != original`, set `msg.messageText = original` (avoid overwriting `Emoji.replaceEmoji` spans on the second `setType()` call in the constructor).
- Hook `MessageObject.generateLayout(TLRPC.User)` (`before` / `after`): swap `owner.entities = ArrayList()` during layout so server entity offsets don't collide with the shorter local text, then restore `owner.entities` in `after`.
- Hook `MessageObject.generateCaption()` (`before` / `after`): swap `owner.message` and `owner.entities` during caption generation, then restore both in `after`.
