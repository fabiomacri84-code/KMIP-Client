# Build and release guide

[English overview](../../README.en.md)

## Native build

Build on the target operating system with Python 3.12:

```text
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python packaging/build.py
```

The build uses PyInstaller and pywebview with Qt. Windows, Linux and macOS builds are native; one Linux build does not produce Windows or macOS executables.

Linux needs the system graphics dependencies listed in `.github/workflows/desktop.yml`. The distributed Linux app needs a modern x86_64 glibc-based desktop with its normal X11/Wayland, EGL/OpenGL, NSS and audio libraries. Alpine/musl and headless-only systems are not targets. The macOS workflow produces Apple Silicon / ARM64 packages.

The build runs `--self-test` on the executable without connecting to CTM or using real credentials. It also rejects packages containing local identities, private keys or settings. The application window can be checked with the developer-only `--smoke-test` option on a machine with a graphical session.

## Versioning

The single version source is `app_version.py`. Use `MAJOR.MINOR.PATCH` and update the changelog and release notes when preparing a release.

1. Update `app_version.py`, `CHANGELOG.md` and `RELEASE-NOTES.md`.
2. Run the tests and commit the changes to `main`.
3. Create and push a matching version tag, such as `v1.0.2`.
4. GitHub Actions validates the version, creates a draft release and builds the three packages on their native operating systems.
5. Successful build jobs upload their package directly to that draft. This does not use GitHub Actions artifact storage.
6. After all three jobs succeed, the release job verifies that the expected archives exist, generates `SHA256SUMS.txt` and publishes the release.

Manual workflow runs perform build verification without publishing a release. Published versions are not silently replaced; create a new version for subsequent changes.

Certificates, private keys, passwords, tokens and local settings must not be committed or included in release packages.
