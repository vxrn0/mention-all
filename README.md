# Mention All

[Русская версия](ru/README.ru.md)

Mention All pings everyone in a group chat. Type `@all` and send: the plugin
replaces the token with a mention of every member — including people without
a username, via text-mention entities. Telegram itself has no such feature.

## Features

- `@all` as a standalone word, case-insensitive; `@allxxx` and `@@all` are
  left alone.
- Works in basic groups and supergroups, in message text and media captions.
- Members with a username are mentioned as `@username`; the rest get a
  text mention by user ID. Names made of spaces stay spaces as the clickable
  text; names made only of invisible non-space characters use `Без имени · ID`.
- Skips you, bots and deleted accounts.
- Adjustable mention cap (default 100) for large groups.
- If the member list cannot be fetched, your message is sent as typed —
  nothing is ever lost.

## Compatibility

- exteraGram and exteraless `>= 12.10.6` — same plugin API
- Plugin SDK `>= 1.4.5.3`
- Permissions: `messages.send` (outgoing-message hook, resend), `network`
  (TL request for the member list)
- Version `1.2.4`

## Install

1. Settings → Plugins: enable the plugin engine and developer mode.
2. Import `plugin/mention_all.plugin` (or just open the file from a chat).
3. Confirm the two permissions on the install sheet.

## License

MIT — see [LICENSE](LICENSE.md).
