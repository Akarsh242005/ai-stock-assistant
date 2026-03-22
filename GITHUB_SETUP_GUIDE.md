# GitHub Setup Guide

Since Git is not currently installed on your system, follow these steps to get your project onto GitHub.

---

## 1. Install Git
1.  Download the Git installer for Windows from: **[git-scm.com/download/win](https://git-scm.com/download/win)**.
2.  Run the `.exe` and follow the setup. (You can keep all the default settings).
3.  Restart your computer (or just close and reopen your terminal/powershell) so the `git` command becomes available.

---

## 2. Initialize your local Repository
Once Git is installed, open your project folder in the terminal and run these commands one by one:

```bash
# 1. Initialize git
git init

# 2. Add all files (the .gitignore I created will skip the junk)
git add .

# 3. Create your first commit
git commit -m "Initial commit: AI Stock Market Assistant with Dashboard"
```

---

## 3. Create a Repo on GitHub
1.  Go to [github.com/new](https://github.com/new).
2.  Name your repository: `ai-stock-assistant`.
3.  Keep it **Public** (good for resumes!) or Private.
4.  **Do NOT** check any "Initialize with README/gitignore" boxes (we already have them).
5.  Click **Create repository**.

---

## 4. Push to GitHub
Copy the commands from the GitHub "Quick Setup" page, or use these:

```bash
# 1. Add the link to your remote repo (Replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/ai-stock-assistant.git

# 2. Rename branch to main
git branch -M main

# 3. Push the code!
git push -u origin main
```

---

## 5. Verify
Refresh your GitHub page. You should now see all your folders (`backend`, `frontend`, etc.) live on GitHub! 🚀
