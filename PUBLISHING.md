# Publishing & release setup

One-time setup to make `welchost` installable via `pipx`/`pip` and Homebrew.
After this, **releases are fully automatic**: merge conventional commits to
`main` and `release.yml` versions, tags, publishes to PyPI, and bumps the
Homebrew formula.

The end goal:

```bash
pipx install welchost                          # or pip install welchost
brew install scoobynko/welchost/welchost       # Homebrew
```

Homebrew installs **from PyPI**, so PyPI must be wired first.

---

## 0. Prerequisites (you)

```bash
gh auth refresh -h github.com    # the stored token is expired
```

Accounts you need: a **PyPI** account (https://pypi.org) and the GitHub user/org
**`scoobynko`** (the workflows reference it — change all `scoobynko` refs if you
use a different owner).

---

## 1. Create the GitHub repo and push (Claude can do this once `gh` is authed)

```bash
gh repo create scoobynko/welchost --public --source=. --remote=origin --push
```

This triggers `ci.yml`. `release.yml` also runs on the push to `main`; it will
no-op on publishing until the secrets below exist, but should still tag the
first version from the conventional-commit history.

---

## 2. PyPI (so `pip`/`pipx`/`brew` have something to install)

Token-based, matching `release.yml` (`password: ${{ secrets.PYPI_TOKEN }}`):

1. https://pypi.org/manage/account/token/ → create a token.
   - First publish: scope it to "Entire account" (the project doesn't exist yet);
     after the first release, replace it with a project-scoped token for `welchost`.
2. Store it as a repo secret:
   ```bash
   gh secret set PYPI_TOKEN --repo scoobynko/welchost
   ```

> More secure alternative (optional): PyPI **Trusted Publishing** (OIDC) removes
> the stored token. Add a pending publisher on PyPI (owner `scoobynko`, repo
> `welchost`, workflow `release.yml`) and delete the `password:` line in
> `release.yml`. `release.yml` already has `id-token: write`.

---

## 3. Homebrew tap (the `brew install` front door)

1. Create the tap repo (must be named `homebrew-<tap>`):
   ```bash
   gh repo create scoobynko/homebrew-welchost --public --add-readme
   ```
2. Create a **classic** PAT with the **`public_repo`** scope only (the tap is
   public) and store it on the **main** repo so `release.yml` can push the formula
   bump. Use a *classic* token — `bump-homebrew-formula-action` fails with
   `invalid ref: refs/heads/main` against fine-grained PATs. Don't grant `repo`
   (private access) or `workflow` (the bump never edits workflow files):
   ```bash
   gh secret set HOMEBREW_TAP_TOKEN --repo scoobynko/welchost
   ```
3. **Generate the initial formula once** — only possible after the package is on
   PyPI (Homebrew needs the real tarball URL + sha256 for welchost and every
   dependency). After the first PyPI release:
   ```bash
   brew tap homebrew/core            # for resources tooling
   pipx run homebrew-pypi-poet welchost > welchost-resources.txt   # generate `resource` blocks
   brew create --python --set-name welchost \
     https://files.pythonhosted.org/.../welchost-<version>.tar.gz
   # paste the poet resource blocks in, commit to scoobynko/homebrew-welchost
   # as Formula/welchost.rb
   ```
   From then on `release.yml`'s `bump-homebrew-formula-action` keeps the
   url + sha256 current on every release. (Re-run poet only when *dependencies*
   change.)

`homebrew-test.yml` smoke-tests `brew install welchost` on each GitHub release.

---

## 4. Branch protection (after the first green release)

```bash
gh api -X PUT repos/scoobynko/welchost/branches/main/protection \
  -f required_status_checks.strict=true \
  -f 'required_status_checks.contexts[]=lint-test' \
  -f enforce_admins=true \
  -f required_pull_request_reviews.required_approving_review_count=0 \
  -f restrictions=
```

(`release.yml` runs on push to `main`, which still fires when a PR merges — so
PR-gated `main` and automated releases coexist.)

---

## Secrets summary (on `scoobynko/welchost`)

| Secret | Where from | Used by |
|---|---|---|
| `GITHUB_TOKEN` | automatic | release, formula bump |
| `PYPI_TOKEN` | pypi.org token | publish to PyPI |
| `HOMEBREW_TAP_TOKEN` | classic PAT, `public_repo` scope | bump the formula |

## After setup: how a release happens

1. Merge a `feat:`/`fix:`/… commit to `main`.
2. `release.yml`: test → semantic-release bumps version, tags `vX.Y.Z`, writes
   `CHANGELOG.md`, creates the GitHub release → publishes to PyPI → bumps the
   Homebrew formula.
3. Users get it via `pipx install welchost` or `brew install scoobynko/welchost/welchost`.
