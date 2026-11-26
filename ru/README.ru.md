![Mention All](../.github/preview.webp)

# Mention All

[![Built with OpenCode](https://opencode.ai/brand/badges/opencode-built-with-f-light-20.svg)](https://opencode.ai) [![Version](https://img.shields.io/github/v/release/vxrn0/mention-all?style=flat-square&label=Version&labelColor=4B4B4B&color=1F1F1F)](https://github.com/vxrn0/mention-all/releases/latest) [![Built for exteraGram](https://img.shields.io/badge/Built%20for-exteraGram-F54142.svg?style=flat-square&labelColor=1F1F1F&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxOTIgMTkyIiBmaWxsPSJub25lIj48cGF0aCBzdHJva2U9IiNGNTQxNDIiIHN0cm9rZS13aWR0aD0iMTIiIGQ9Ik0xNDQuODkgMzEuMjEyYzEyLjU3My00LjEwNyAyMC4wMjUgMi41NTMgMTYuMDI2IDE1LjA0NC0xMC4wMzggMzEuMzkxLTI5Ljc0OSA4OC42NTMtNDIuMjc3IDEyNC44MS0zLjI4MSA5LjQ1Ny0xOC40NjMgOS4wODctMjIuMjc1LS4xNzEtNi41NC0xNS44NzMtMTYuMTY4LTM0LjM1MS0yOS4zMDgtNDcuODE5LTEyLjU2NS0xMi44NzYtMzAuMTYtMjIuMTg1LTQ1Ljc4My0yOC41NS05LjUxNS0zLjg3Ny05Ljg1Mi0xOS43MDYtLjA3NS0yMi44OTVMMTQ0Ljg5IDMxLjIxWiIvPjwvc3ZnPg%3D%3D)](https://exteragram.app)

[English version](../README.md)

Mention All отмечает всех участников группы. Напишите `@all` и отправьте:
плагин отправляет на сервер Telegram упоминания каждого участника — включая тех,
у кого нет юзернейма, через text-mention — а у вас в интерфейсе сообщение
отображается как `@all`. В самом Telegram такой функции нет.

## Возможности

- `@all` отдельным словом, регистр не важен; `@allxxx` и `@@all` не трогаются.
- `@all` появляется в подсказках упоминаний при вводе `@` в группах.
- После отправки у вас в чате текст остаётся свёрнутым в `@all`, тогда как на
  сервер уходят полные упоминания всех участников.
- Работает в базовых группах и супергруппах, в тексте и в подписи к медиа.
- Участники с юзернеймом упоминаются как `@username`; остальные — текстовым
  упоминанием по ID. Имена из пробелов остаются пробелами под кликабельной
  entity; имена из одних невидимых не-пробельных символов получают подпись
  `Без имени · ID` (или `Unnamed · ID` на английском).
- Себя, ботов и удалённые аккаунты не упоминает.
- Настраиваемый лимит упоминаний (по умолчанию 100) для больших групп.
- Подписи интерфейса следуют языку клиента: английский по умолчанию, русский
  при русском языке клиента.
- Если список участников получить не удалось — сообщение уходит как
  напечатано, ничего не теряется.

## Совместимость

- exteraless `>= 12.10.6` — единственный клиент, в котором Mention All проверялся
- exteraGram и AyuGram используют тот же API плагинов, но не тестировались;
  считайте их поддержку непроверенной
- SDK плагинов `>= 1.4.5.3`
- Разрешения: `messages.send` (хук исходящих, повторная отправка), `network`
  (TL-запрос списка участников) и `hooks` (подсказка `@all` и локальное
  отображение `@all` в сообщениях, списке чатов и топиках). Разрешение `hooks`
  даёт широкие возможности.
- Версия `1.4.1`

## Установка

1. Настройки → Plugins: включить движок плагинов и режим разработчика.
2. Импортировать `plugin/mention_all.plugin` (или просто открыть файл из чата).
3. Подтвердить запрошенные разрешения на экране установки.

## Обновления

Новые версии публикуются в [@vxrn0](https://t.me/vxrn0).

## Лицензия

MIT — см. [LICENSE.ru.md](LICENSE.ru.md).
