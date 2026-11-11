# Publish Credna's Creation Kit on GitHub

Use the **0.24 source ZIP** and, optionally, the **0.24 Windows x64 ZIP** from the project Drive folder. The official display name is **Credna's Creation Kit**; `crednas-creation-kit` is the suggested repository name. The Windows executable is `Crednas-Creation-Kit.exe`.

The source package contains the editor, tests, documentation, GitHub workflow and licenses. It does not contain game files. Upload this clean source package rather than your personal game/mod/project folder. Leave the included MIT license and third-party notices in place; the rename does not change the existing copyright attribution.

## Easiest method: GitHub in your browser

1. Extract **Crednas-Creation-Kit-0.24.zip**. Open the **Crednas-Creation-Kit** folder inside it.
2. Sign into GitHub and open <https://github.com/new>.
3. Set the repository name to **crednas-creation-kit**. Suggested description: **A Windows and Linux editor for Fortune's Weave 1.00.** Choose **Public** to share it with everyone, or **Private** for restricted access. Leave the initial README, `.gitignore` and license options unchecked: the source already includes them. Click **Create repository**.
4. On the empty repository page, select **uploading an existing file**. In an existing repository, use **Add file → Upload files**.
5. Upload the **contents** of the extracted Crednas-Creation-Kit folder, keeping their paths. Do not upload the source ZIP as the only repository file and do not nest everything inside another Crednas-Creation-Kit folder. `README.md`, `fw_editor.py`, `branding.py` and the other modules should be at the repository root.
6. GitHub limits browser uploads to **100 files per batch**. Upload the root files first and commit them. Upload the `tests`, `licenses` and `.github` folders in a second batch, preserving those folder names. On Linux, **Ctrl+H** shows hidden files/folders, including `.github` and `.gitignore`. You can drag folders onto the upload area. If a browser skips hidden files, use the terminal method below.
7. Use a commit message such as **Initial release of Credna's Creation Kit** and click **Commit changes**. Check that GitHub displays the README and that `.github/workflows/windows.yml`, `tests` and `licenses` exist at the expected paths.

The program's source is now on GitHub. Next, add convenient downloads under Releases.

## Add a downloadable release

1. In your repository, open **Releases → Draft a new release** or **Create a new release**.
2. Enter a new tag **v0.24**, targeting **main**. Set the release title to **Credna's Creation Kit 0.24**.
3. Suggested description:

   ```text
   Credna's Creation Kit 0.24

   Formerly FW Hacking Suite. The new name is used throughout the application,
   Linux shortcut, Windows executable and release packages. Existing projects,
   preferences and the translation glossary remain compatible.

   Includes all sixteen editing modules and the limited compiled-script editor.
   Game version: Fortune's Weave 1.00. No game data is included.

   Windows: download the Windows-x64 ZIP, extract it, and run
   Crednas-Creation-Kit.exe.
   Linux/source: download the source ZIP, extract it, and run bash install.sh.
   ```

4. Attach **Crednas-Creation-Kit-0.24.zip** and **Crednas-Creation-Kit-0.24-Windows-x64.zip** in the release's file-upload area. The Windows executable belongs inside its downloadable ZIP; it does not need to be committed into the source tree.
5. Publish the release. GitHub also generates its own source-code archives from the tag; your attached ZIPs are the ready-made distributions, especially the Windows executable package.
6. Share the repository or release page link. If the repository is private, its releases require access too.

## Terminal method on Pop!_OS / Ubuntu

Run these commands yourself from a terminal. This method includes hidden files automatically and avoids the browser's 100-file batch limit.

Install Git and GitHub CLI once:

```sh
sudo apt update
sudo apt install git gh
```

Sign in using the browser flow. Choose GitHub.com and HTTPS when asked, and allow the CLI to authenticate Git:

```sh
gh auth login
```

Extract the 0.24 source ZIP and open a terminal **inside its Crednas-Creation-Kit folder**. Replace the two example identity values below with your Git name and email; GitHub's account email settings can provide a private `noreply` address.

```sh
git init -b main
git config user.name "YOUR NAME"
git config user.email "YOUR GIT EMAIL"
git add .
git commit -m "Initial release of Credna's Creation Kit"
gh repo create crednas-creation-kit --public --source=. --remote=origin --push
```

Use `--private` instead of `--public` if you want a private repository. This command creates the repository, so do not first create another empty repository with the same name using the browser method. For a repository you already created, use that repository page's **push an existing repository** instructions instead.

Then follow the browser release steps above. For subsequent updates in this same checkout:

```sh
git add .
git commit -m "Update Credna's Creation Kit"
git push
```

Review `git status` before committing if you have added personal files to your software folder. Keep your game data, exports, edit-project JSON and preferences outside the software checkout.

## Optional: build Windows releases on GitHub

The included **Windows executable** workflow builds with Windows Python 3.12, runs synthetic tests, builds the executable, and checks its startup/native decompression. It requires no game files.

After uploading `.github/workflows/windows.yml`, open **Actions → Windows executable → Run workflow**, choose **main**, and run it. The finished run has a downloadable **Crednas-Creation-Kit-Windows-x64** artifact. Extract that artifact once to obtain the Windows release ZIP, then attach that release ZIP to a GitHub release.

The workflow also runs when a version tag is **pushed**. A tag created only in the GitHub release interface does not guarantee this push-triggered workflow will run; use **Run workflow** when needed. The workflow uploads a build artifact. It does **not** automatically publish release assets, and an Actions artifact is different from a normal release download.

## If you meant a gameplay mod rather than the editor

Create a separate repository or release for that mod, with its own name and README. Include the files and instructions needed for your mod, and exclude the complete game dump and personal saves. The instructions above publish the **editor program**, which is the software being renamed here.
