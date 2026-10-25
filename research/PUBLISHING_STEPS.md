# Publishing FlashWAF v1.0.0

These steps describe external actions after the owner explicitly authorizes publication. No GitHub tag, release, or Zenodo record has been created.

## Enable Zenodo archiving

1. Sign in to Zenodo and connect the GitHub account that owns `apandya55/flash-waf-sim`.
2. Open Zenodo's GitHub page, click **Sync now**, enable `apandya55/flash-waf-sim`, and confirm that it appears in the enabled repository list. Enable it before creating the GitHub release. Zenodo says it automatically ingests and archives new releases from enabled repositories.

The current instructions are at [Enable a repository](https://help.zenodo.org/docs/github/enable-repository/) and [Archive a release from GitHub](https://help.zenodo.org/docs/github/archive-software/github-upload/). Zenodo's [metadata guide](https://help.zenodo.org/docs/github/describe-software/zenodo-json/) says `.zenodo.json` takes precedence over `CITATION.cff` when both files are present.

## GitHub release

1. Confirm the account and repository permissions. From the repository root, run `git status --short`, `git diff --check`, and inspect `git show --stat --oneline HEAD` plus `git show --name-status --format=fuller HEAD` for the exact release commit.
2. Run the clean-install and reproduction commands in `README.md`. Confirm the generated results, figures, and archived legacy plots are in the reviewed tree.
3. Commit the approved release tree locally if it has not already been committed. Then create an annotated tag:

   ```sh
   git tag -a v1.0.0 -m "FlashWAF v1.0.0"
   git show --stat --oneline v1.0.0
   ```

4. Push the tag to GitHub:

   ```sh
   git push origin v1.0.0
   ```

5. On `https://github.com/apandya55/flash-waf-sim/releases`, choose the `v1.0.0` tag, paste the contents of `RELEASE_NOTES_v1.0.0.md`, inspect the generated source archive, and publish the release. Do not describe the project as peer reviewed or claim a novel general scientific result.
6. Confirm that the GitHub release page, tag, and downloadable archive point to the intended commit.

## Zenodo software record

1. After the GitHub release, return to Zenodo's GitHub page and wait for the release to finish processing. Open the resulting record and confirm the title, creator, version `1.0.0`, software resource type, MIT license, description, keywords, and source archive. Check that Zenodo imported `.zenodo.json` metadata.
2. The GitHub integration processes and archives a detected release automatically. Inspect the public record and DOI; correct metadata through Zenodo's record controls where available, or prepare a corrected new version if the archive metadata or files cannot be changed.
3. Describe the deposit as software with synthetic simulator experiments. Do not label it a journal article, peer-reviewed work, or a novel general scientific finding.
4. Add the version DOI to the GitHub README and citation metadata in a later commit. A published release archive is immutable; make a new software version if its contents need changes.

## After publication

Check the GitHub release, Zenodo landing page, DOI, and downloadable files in a signed-out browser session. Record the release URL, DOI, publication date, and archive checksum in the release log.
