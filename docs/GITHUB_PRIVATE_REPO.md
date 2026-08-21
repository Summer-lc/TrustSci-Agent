# GitHub Private Repository Setup

The repository is now connected to:

```bash
git@github.com:Summer-lc/TrustSci-Agent.git
```

Keep the GitHub repository private and invite collaborators with push permission only when needed.

If another machine needs to recreate the setup, use one of these options.

## Option A: GitHub CLI

```bash
gh auth login
gh repo create AI_Scientist --private --source=. --remote=origin --push
```

Add your friend after the repo exists:

```bash
gh api -X PUT repos/:owner/AI_Scientist/collaborators/<github_username> \
  -f permission=push
```

## Option B: Personal Access Token

Create a fine-grained token with permission to create repositories and push contents, then run:

```bash
export GITHUB_TOKEN=<token>
OWNER=<your_github_username>
REPO=AI_Scientist

curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO\",\"private\":true}"

git remote add origin "https://$GITHUB_TOKEN@github.com/$OWNER/$REPO.git"
git push -u origin main
git remote set-url origin "https://github.com/$OWNER/$REPO.git"
```

Then invite a collaborator:

```bash
curl -sS -X PUT -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$OWNER/$REPO/collaborators/<github_username>" \
  -d '{"permission":"push"}'
```

Never commit `.env` or tokens. The repo already ignores `.env`, `node_modules`, build outputs, local reference clones, and generated reports.
