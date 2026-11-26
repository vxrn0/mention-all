# Mention All

[Русская версия](ru/README.ru.md)

Mention All pings everyone in a group chat. Type `@all` and send: the plugin
sends mentions of every member to Telegram servers — including people without
a username, via text-mention entities — while keeping the message displayed as
`@all` for you locally. Telegram itself has no such feature.

## Features

- `@all` as a standalone word, case-insensitive; `@allxxx` and `@@all` are
  left alone.
- `@all` is offered in the `@` mention menu in groups.
- After sending, your local chat view displays `@all` while the full mentions
  are delivered to the server and other members.
- Works in basic groups and supergroups, in message text and media captions.
- Members with a username are mentioned as `@username`; the rest get a
  text mention by user ID. Names made of spaces stay spaces as the clickable
  text; names made only of invisible non-space characters use `Unnamed · ID`
  (or `Без имени · ID` in Russian).
- Skips you, bots and deleted accounts.
- Adjustable mention cap (default 100) for large groups.
- UI labels follow the client language: English by default, Russian when the
  client is set to Russian.
- If the member list cannot be fetched, your message is sent as typed —
  nothing is ever lost.

## Compatibility

- exteraless `>= 12.10.6` — verified target
- exteraGram and AyuGram use the same plugin API and are supported targets,
  but were not tested
- Plugin SDK `>= 1.4.5.3`
- Permissions: `messages.send` (outgoing-message hook, resend), `network`
  (TL request for the member list), and `hooks` (`@all` autocomplete and local
  masking in messages, chat-list and topic previews). `hooks` is a powerful
  permission.
- Version `1.4.1`

## Install

1. Settings → Plugins: enable the plugin engine and developer mode.
2. Import `plugin/mention_all.plugin` (or just open the file from a chat).
3. Confirm the requested permissions on the install sheet.

## Updates

New releases are posted in [@vxrn0](https://t.me/vxrn0).

## License

MIT — see [LICENSE](LICENSE.md).
