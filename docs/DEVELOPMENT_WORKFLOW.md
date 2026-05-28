# Development Workflow

This project is shared by multiple collaborators. Use this rhythm every day.

## Start of Day

```bash
git status --short --branch
git fetch origin main --prune
git pull --ff-only origin main
```

Read the fetched commits before starting if the branch moved:

```bash
git log --oneline --decorate --max-count=10
```

## During Development

Use feature branches for larger changes:

```bash
git switch -c feat/<short-name>
```

For small coordinated changes on `main`, commit frequently and push after tests pass.

## End of Day

```bash
python -m pytest
cd frontend && npm run build
cd ..
git status --short
git add .
git commit -m "<clear message>"
git push
```

Generated outputs under `data/outputs/`, `.env`, `.references/`, `node_modules/`, and build caches are ignored.

## WSL Notes

- Prefer cloning inside the WSL filesystem, for example `~/projects/TrustSci-Agent`, instead of `/mnt/c/...`.
- Enable Docker Desktop WSL integration for the target distro.
- Run Docker commands from the WSL shell.
- If file watching is slow, keep `WATCHPACK_POLLING=true` and `CHOKIDAR_USEPOLLING=true` in `.env`.
- Do not commit `.env`; use `.env.example` as the shared template.

