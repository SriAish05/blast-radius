# How to Add and Push Your Work to GitHub

This guide explains step-by-step how to upload your watcher code from your laptop to the team's GitHub repository.

---

## 📌 Repository Information
- **Team Repository URL:** `https://github.com/SriAish05/blast-radius`
- **Your Branch Name:** `feat/watcher`
- **Your Folder:** `watcher-kaveeswaran/` (and `watcher/`)

---

## 🚀 Steps to Push to GitHub

### Step 1: Open PowerShell or Command Prompt
Open a terminal in your project directory:
```powershell
cd C:\Users\Selvakumar\.gemini\antigravity\scratch\blast-radius
```

### Step 2: Push your branch to GitHub
Run this command:
```powershell
git push -u origin feat/watcher
```

### Step 3: Complete Browser Sign-in (if prompted)
1. Windows will open a prompt asking: **"Sign in with your browser"**.
2. Click the button to authorize Git on GitHub.
3. Once approved, the branch will upload to GitHub!

---

## 🔍 Step 4: Open a Pull Request (PR) for Review
1. Go to: [https://github.com/SriAish05/blast-radius](https://github.com/SriAish05/blast-radius)
2. Click the green **"Compare & pull request"** button for `feat/watcher`.
3. Add a short title: `feat(watcher): script change watcher (Section 9.2)`
4. Click **"Create pull request"**.

> **⚠️ Team Rule:** Do **NOT** click "Merge". Leave the Pull Request open for team lead review.

---

## ❓ What if it says "Permission Denied (403)"?
If GitHub blocks the push, it means you need collaborator access.
Ask Aish:
> *"Hey Aish, can you add my GitHub username (`Kaveeswaran`) as a collaborator to the `blast-radius` repo so I can push `feat/watcher`?"*
Once invited, run `git push -u origin feat/watcher` again.
