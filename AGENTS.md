# AGENTS.md — mention-all

Single-file plugin for the Telegram client family sharing one Python plugin
host: **exteraGram**, **exteraless**, **AyuGram**. Typing `@all` in a group
replaces the token with a text mention of every member; Telegram itself has
no such feature.

Supported and tested only in exteraless; the hooks and permissions are also
verified against the exteraless engine sources. exteraGram is known not to work
(unsupported); AyuGram is untested (unverified).

Plugin API (hooks, permissions, mention entities, UTF-16 offsets):
[`docs/plugin-api.md`](docs/plugin-api.md). Load the `exteraless-plugin-dev`
skill (`.agents/skills/exteraless-plugin-dev/SKILL.md`) before editing code.

## Layout

| Path | Contents |
|------|----------|
| `plugin/mention_all.plugin` | The whole plugin: hook, member fetch, entities. Single file by contract. |
| `scripts/package_release.py` | Validates metadata, builds `dist/MentionAll-<version>.plugin` + `SHA256SUMS`. |
| `tests/test_plugin.py` | Host-side stubs for mention building, offsets, hook routing. |
| `docs/plugin-api.md` | How plugins for this host family are written. |
| `SECURITY.md` | Supported versions, trusted builds, vulnerability reporting. |
| `.github/` | CI workflow. |
| `ru/` | Russian README, license and security policy; English originals stay at the root. |

## Commands

```sh
python3 -m py_compile plugin/mention_all.plugin
python3 scripts/package_release.py --check
python3 tests/test_plugin.py
python3 scripts/package_release.py --output-dir dist
(cd dist && sha256sum -c SHA256SUMS)
```

## Rules

- The `.plugin` file stays at `plugin/mention_all.plugin`; CI, packaging and
  tests read that exact path.
- All Java/SDK imports (`org.telegram.*`, `client_utils`, `java.util`) live
  inside functions: the file must parse and test on a desktop without
  Chaquopy.
- Pure logic (UTF-16 offsets, token parsing, dialog-id math) stays in the
  module-level functions and is covered by `tests/test_plugin.py`; tests stub
  the SDK modules, they never import Chaquopy.
- `__permissions__` must match real usage — it is shown to the user on the
  install sheet: `messages.send` + `network` + `hooks`.
