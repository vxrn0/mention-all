# Security policy

[Русская версия](ru/SECURITY.ru.md)

## Supported versions

**Use only the latest release.** Only the asset marked "Latest" on
https://github.com/vxrn0/mention-all/releases/latest is supported.

| Release | Supported |
| --- | --- |
| Latest GitHub release | Yes |
| Any earlier tag or asset | No |

Older versions are kept only as history. They may not work with current
client versions, are not tested, and receive no fixes — including security
fixes. Update to the latest release before reporting a problem.

## Trusted builds

- Download the `.plugin` file only from the official GitHub Releases page or
  the `@vxrn0` Telegram channel (https://t.me/vxrn0).
- Verify the asset against `SHA256SUMS` from the same release.
- Review the permissions shown on the install sheet: `messages.send` and
  `network` are needed to fetch members and send mentions; `hooks` enables the
  `@all` autocomplete and local display masking. `hooks` is a powerful
  permission — treat a plugin asking for more as suspicious.
- The plugin updates only when you install a new file; it does not download
  code by itself.

## Reporting a vulnerability

Prefer GitHub's private "Report a vulnerability" on the repository Security
tab. Alternatively, email `vxrn@tutamail.com` or write to
[@vxrn0](https://t.me/vxrn0) on Telegram.

Do not open a public issue with exploit details. Include the plugin version,
client and client version, steps to reproduce, and any relevant log. This is a
small side project: reports are handled best-effort, with no response SLA;
confirmed issues are fixed in the latest release.
