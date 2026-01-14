# Release Process

This document describes how to create and publish a new release of recipe-clipper to PyPI.

## Versioning Strategy

We use **semantic versioning** (semver) with git tags:
- **Major version** (X.0.0): Breaking changes
- **Minor version** (0.X.0): New features, backward compatible
- **Patch version** (0.0.X): Bug fixes, backward compatible

Examples: `v0.1.0`, `v0.2.0`, `v1.0.0`, `v1.2.3`

## Automated Publishing Workflow

The publish workflow (`.github/workflows/publish.yml`) automatically:
1. ✅ Validates that the git tag matches `pyproject.toml` version
2. ✅ Runs full test suite across Python 3.10-3.14
3. ✅ Runs linting checks
4. ✅ Builds source distribution and wheel
5. ✅ Publishes to PyPI using trusted publishing
6. ✅ Creates a GitHub Release with build artifacts

## How to Release

### Prerequisites

1. Ensure you're on the `main` branch and it's up to date:
   ```bash
   git checkout main
   git pull origin main
   ```

2. Ensure all CI checks pass on master

### Step-by-Step Release Process

1. **Update the version** in `packages/recipe_clipper/pyproject.toml`:
   ```toml
   [project]
   name = "recipe-clipper"
   version = "0.2.0"  # Update this line
   ```

2. **Update `__version__` in `packages/recipe_clipper/src/recipe_clipper/__init__.py`**:
   ```python
   __version__ = "0.2.0"  # Keep in sync with pyproject.toml
   ```

3. **Commit the version bump**:
   ```bash
   git add packages/recipe_clipper/pyproject.toml packages/recipe_clipper/src/recipe_clipper/__init__.py
   git commit -m "chore: bump version to 0.2.0"
   git push
   ```

4. **Create and push a git tag**:
   ```bash
   # Create an annotated tag
   git tag -a v0.2.0 -m "Release version 0.2.0"

   # Push the tag to GitHub
   git push origin v0.2.0
   ```

5. **Monitor the workflow**:
   - Go to https://github.com/zduey/kitchenmate/actions
   - Watch the "Publish to PyPI" workflow run
   - Verify all jobs pass (validate → test → build → publish)

6. **Verify the release**:
   - Check PyPI: https://pypi.org/project/recipe-clipper/
   - Check GitHub Releases: https://github.com/zduey/recipe-clipper/releases
   - Test installation: `pip install recipe-clipper==0.2.0`

## Pre-release Versions

For alpha/beta releases, use pre-release version numbers:

```bash
# Alpha release
git tag -a v0.2.0a1 -m "Release version 0.2.0-alpha.1"

# Beta release
git tag -a v0.2.0b1 -m "Release version 0.2.0-beta.1"

# Release candidate
git tag -a v0.2.0rc1 -m "Release version 0.2.0-rc.1"
```

Update `pyproject.toml` accordingly:
```toml
version = "0.2.0a1"  # or "0.2.0b1", "0.2.0rc1"
```

## Rolling Back a Release

If a release has issues:

1. **Delete the git tag** (if not yet published):
   ```bash
   git tag -d v0.2.0
   git push origin :refs/tags/v0.2.0
   ```

2. **Yank the PyPI release** (if already published):
   - Go to https://pypi.org/project/recipe-clipper/
   - Click on the problematic version
   - Click "Options" → "Yank release"
   - Add a reason (e.g., "Critical bug in recipe parsing")

3. **Fix the issue and release a new version** (e.g., v0.2.1)
