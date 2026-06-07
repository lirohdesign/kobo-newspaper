# liroh newspaper 🗞️

A personal automated newspaper service that curates content from The Guardian, NYT, and Weather AFD. Optimized for the **Kobo** eReader via **Instapaper**.

## 🏗️ Architecture

| Workflow | Frequency (CST) | Purpose |
| :--- | :--- | :--- |
| **Daily Newspaper** | 6:30 AM (M-F) / 7:45 AM (S-S) | Builds `index.html`. Weekend lag handles NYT publishing delays. |

## 📂 Persistent Storage

* **`old_issues/`**: Stores historical HTML builds and `sent_articles.json` (Guardian IDs). This folder is synced from `gh-pages` during the build to maintain state.

## 🚧 Shelved

A private Substack sync used to run alongside the daily build but was removed —
Substack/Cloudflare blocks GitHub Actions' IPs and there was no reliable way
around it. See [`project_substack_sync_blocked.md`](project_substack_sync_blocked.md)
for the diagnosis and the lead worth following if this gets revisited.

## 🛠️ Maintenance

### Create a Stable Build Tag
To lock in a version of the code (Current: v2.1-stable):
```bash
git tag -a v2.1-stable -m "Morning cron sync and persistent logging in old_issues"
git push origin v2.1-stable