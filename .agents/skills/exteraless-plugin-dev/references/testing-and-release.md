# Host-Side Testing, Packaging & Releases

## Host-Side Mock Tests (No JVM / No Android)

Keep all pure logic (UTF-16 offsets, regex parsing, `dialog_id` normalization, prefix matching, hash keys) in module-level functions, and test both pure logic and hook callbacks on desktop using `sys.modules` stubs:

- Stub `base_plugin`, `ui.settings`, `java.util` (`ArrayList`, `WeakHashMap`), `org.telegram.tgnet` (`TLRPC`), `org.telegram.messenger` (`LocaleController`, `ChatObject`), `client_utils`.
- **Match real Java object shapes in mocks** — e.g. give `FakeSupergroup` only `broadcast` and `megagroup` (NO `.channel` attribute!) so an invented attribute raises `AttributeError` in desktop tests before ever reaching a phone.
- Test:
  - Both positive and negative cases (DMs, broadcast channels, disabled switch, expired cache, incoming `out=False` messages).
  - State restoration (`after_hooked_method` restores `entities`, `message`, radius, marks).
  - Both English default and Russian (`LocaleController` returning `"ru"` / `"ru-RU"`).
  - Failure paths (missing `InputUser`, empty member list, retry latch).

## Verification Commands

Run all of these before committing:

```sh
python3 -m py_compile plugin/<id>.plugin
python3 scripts/package_release.py --check
python3 tests/test_*.py
git diff --check
```

## Release Flow (`.plugin` + `SHA256SUMS`)

1. Bump `__version__` in `plugin/<id>.plugin` and sync `README.md` + `ru/README.ru.md`.
2. Build and verify locally:
   ```sh
   python3 scripts/package_release.py --output-dir dist
   (cd dist && sha256sum -c SHA256SUMS)
   ```
3. Commit with a conventional message, push `main`, tag `v<version>`, push tag.
4. Publish GitHub release with both assets:
   ```sh
   gh release create v<version> dist/<Name>-<version>.plugin dist/SHA256SUMS \
     --repo <owner>/<repo> --title "<Name> <version>" --generate-notes
   ```
5. Download the uploaded release into a temp directory and verify `sha256sum -c SHA256SUMS` + `cmp` against `dist/<Name>-<version>.plugin`.

## Honesty Rule

Desktop mocks prove Python logic and hook routing, **not** Android/ART/Chaquopy runtime behavior. Always report what was verified on desktop vs. against `exteraless` sources vs. on a real device, and treat untested clients (`exteraGram`, `AyuGram`) as unverified until run there.
