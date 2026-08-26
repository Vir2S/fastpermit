# Releasing FastPermit

FastPermit publishes to PyPI from GitHub Actions using PyPI Trusted Publishing (OIDC). No long-lived PyPI API token is stored in GitHub.

## One-time setup

### 1. Create the GitHub environment

In `Vir2S/fastpermit`:

1. Open **Settings → Environments**.
2. Create an environment named `pypi`.
3. Optionally require manual approval for deployments to this environment.

### 2. Configure PyPI Trusted Publishing

In PyPI, configure a trusted publisher (or a pending trusted publisher for the first release) with:

- PyPI project name: `fastpermit`
- GitHub owner: `Vir2S`
- Repository: `fastpermit`
- Workflow: `release.yml`
- Environment: `pypi`

The workflow uses GitHub OIDC and therefore does not require a `PYPI_TOKEN` secret.

## Release process

1. Update the version in `pyproject.toml` and `src/fastpermit/__init__.py`.
2. Move release notes from `Unreleased` into a dated version section in `CHANGELOG.md`.
3. Run:

   ```bash
   make check
   ```

4. Merge the release changes into `master`.
5. Create a GitHub release with a tag matching the package version exactly, for example:

   ```text
   v0.1.0
   ```

6. Publish the GitHub release.

Publishing the release triggers `.github/workflows/release.yml`, which builds the wheel and source distribution in a non-privileged job, validates them with Twine, and publishes the resulting artifacts from a separate OIDC-enabled job.

## Important

PyPI release files are immutable. If `0.1.0` is published with a mistake, fix the issue and release a new version such as `0.1.1`; do not attempt to overwrite `0.1.0`.
