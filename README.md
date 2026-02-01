# liroh newspaper 🗞️

A personal automated newspaper service that curates content from The Guardian, NYT, and Weather AFD, plus a private Substack synchronization engine. Optimized for the **Kobo** eReader via **Instapaper**.

## 🏗️ Architecture

The system is split into two independent workflows to ensure reliability, handle specific publishing windows, and bypass rate limits.

| Workflow | Frequency (CST) | Purpose |
| :--- | :--- | :--- |
| **Substack Sync** | 6:00 AM Daily | Sequestered check for private feeds. Handles Sunday backlog. |
| **Daily Newspaper** | 6:30 AM (M-F) / 7:45 AM (S-S) | Builds `index.html`. Weekend lag handles NYT publishing delays. |

## 📂 Persistent Storage

* **`old_issues/`**: Stores historical HTML builds and `sent_articles.json` (Guardian IDs). This folder is synced from `gh-pages` during the build to maintain state.
* **GitHub Cache**: Stores hashed URLs for the Substack workflow (`sent_substack.json`) to maintain state and privacy without cluttering the repository history.

## ⚙️ Logic & Rules

### Sunday Substack Backlog
* **Daily**: Any post published after **Jan 31, 2026** is sent immediately.
* **Sunday**: The script pulls the next **two oldest** unread articles from the backlog (pre-Feb 2026) until the archive is fully processed.

### Privacy & Security
* **Hashing**: Substack URLs are hashed (SHA-256) before storage. This ensures private feed links never appear in plain text within GitHub Action logs or public-facing files.
* **Proxy**: Uses AllOrigins to bypass `403 Forbidden` errors on private Substack RSS feeds.

## 🛠️ Maintenance

### Create a Stable Build Tag
To lock in a version of the code (Current: v2.1-stable):
```bash
git tag -a v2.1-stable -m "Morning cron sync and persistent logging in old_issues"
git push origin v2.1-stable