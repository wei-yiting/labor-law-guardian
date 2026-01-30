# Git Worktree Management Script

This script helps manage git worktrees for parallel development in the Labor Law Guardian project.

## Overview

Git worktrees allow you to have multiple working directories attached to the same repository, enabling parallel development without affecting your main workspace.

### How Git Worktrees Work

**Important:** All worktrees share the same Git repository (`.git` directory). This means:

- ✅ Commits made in any worktree are immediately available in the main worktree
- ✅ Branches created in worktrees exist in the main repository
- ✅ You can checkout the same branch in the main worktree after finishing work on it
- ⚠️ You cannot checkout the same branch in multiple worktrees simultaneously

**Example:**
1. Create worktree with `feature/new-feature` branch
2. Make commits in that worktree
3. Finish work (remove worktree)
4. Switch to `feature/new-feature` in main worktree - all commits are there!
5. Merge `feature/new-feature` into `dev` when ready

**Visual Workflow:**
```
Main Worktree                    Feature Worktree
(labor-law-guardian)             (labor-law-guardian-wt-feature-x)
     [dev]                              [feature/x]
       |                                     |
       |-- create worktree --------------->[create branch]
       |                                     |
       |                                   [commit A]
       |                                   [commit B]
       |                                   [commit C]
       |                                     |
       |<-- finish (remove worktree) -------|
       |                                     ✗ (removed)
       |
    [checkout feature/x]
       |
    [commit A, B, C] ← All commits are here!
       |
    [merge into dev]
```

## Features

- ✅ Create new worktrees with automatic branch creation
- ✅ Automatically copy `.env` and other gitignored files to new worktrees
- ✅ Optional dependency installation with `uv sync`
- ✅ Optional Docker services startup
- ✅ Finish work on worktree and make branch available in main worktree
- ✅ List all active worktrees
- ✅ Remove worktrees safely
- ✅ Sync environment files between main repo and worktrees

## Installation

The script is located at `scripts/manage_worktree.sh` and is already executable.

For convenience, you can create an alias in your shell profile:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias wt='/path/to/labor-law-guardian/scripts/manage_worktree.sh'
```

Then reload your shell or run `source ~/.bashrc` (or `~/.zshrc`).

## Usage

### Create a New Worktree

```bash
# Basic usage - creates worktree in ../labor-law-guardian-wt-feature-add-auth
./scripts/manage_worktree.sh create feature/add-auth

# Create from specific base branch
./scripts/manage_worktree.sh create feature/add-auth --base dev

# Create with automatic dependency installation
./scripts/manage_worktree.sh create feature/add-auth --sync-deps

# Create with Docker services startup
./scripts/manage_worktree.sh create feature/add-auth --start-docker

# Combine options
./scripts/manage_worktree.sh create feature/refactor-rag --base dev --sync-deps --start-docker
```

**What happens during creation:**
1. Creates a new git worktree at `../labor-law-guardian-wt-<sanitized-branch-name>`
2. Creates a new branch based on specified base (or current branch)
3. Copies `.env` files from main repo to worktree
4. Optionally runs `uv sync` to install dependencies
5. Optionally starts Docker services with `docker-compose up -d`

### Finish Work on Worktree

When you finish working on a feature, use the `finish` command to make the branch available in your main worktree:

```bash
# Finish work and remove worktree
./scripts/manage_worktree.sh finish feature/add-auth

# Finish and automatically switch to the branch in main worktree
./scripts/manage_worktree.sh finish feature/add-auth --switch

# Finish but keep the worktree
./scripts/manage_worktree.sh finish feature/add-auth --no-remove
```

**What happens during finish:**
1. Checks for uncommitted changes (fails if any exist)
2. Confirms that all commits are saved to the branch
3. Removes the worktree directory (unless `--no-remove` is specified)
4. The branch with all your commits is now available in the main worktree
5. Optionally switches to the branch in main worktree (with `--switch`)

**Important:** All commits you made in the worktree are already in the repository! Git worktrees share the same repository, so your branch exists in both places.

**After finishing, you can:**
```bash
# Option 1: Switch to the branch in main worktree
cd /path/to/main/labor-law-guardian
git checkout feature/add-auth

# Option 2: Merge it into another branch (e.g., dev)
cd /path/to/main/labor-law-guardian
git checkout dev
git merge feature/add-auth

# Option 3: Push to remote for PR
git push origin feature/add-auth
```

### List All Worktrees

```bash
./scripts/manage_worktree.sh list
```

Shows all active worktrees with their paths and branches.

### Remove a Worktree

```bash
# Remove worktree (fails if uncommitted changes exist)
./scripts/manage_worktree.sh remove feature/add-auth

# Force remove even with uncommitted changes
./scripts/manage_worktree.sh remove feature/add-auth --force
```

**Note:** This only removes the worktree directory. The branch still exists in the repository.

### Sync Environment Files

If you update `.env` in the main repo and want to sync it to worktrees:

```bash
./scripts/manage_worktree.sh sync-env feature/add-auth
```

## Directory Structure

Worktrees are created as siblings to the main project directory:

```
parent-directory/
├── labor-law-guardian/          # Main repository
├── labor-law-guardian-wt-feature-add-auth/
├── labor-law-guardian-wt-feature-refactor-rag/
└── labor-law-guardian-wt-fix-bug-123/
```

## Typical Workflow

### Starting a New Feature

```bash
# 1. Create worktree for new feature (from dev branch)
./scripts/manage_worktree.sh create feature/implement-agents --base dev --sync-deps --start-docker

# 2. Switch to the worktree
cd ../labor-law-guardian-wt-feature-implement-agents

# 3. Work on your feature
# ... make changes, commit as usual ...
git add .
git commit -m "Implement agents functionality"
git commit -m "Add tests for agents"

# 4. When done, finish work on worktree
./scripts/manage_worktree.sh finish feature/implement-agents --switch

# Now you're back in main worktree on the feature/implement-agents branch!
# All your commits are here

# 5. Merge into dev or create PR
git checkout dev
git merge feature/implement-agents
git push origin feature/implement-agents

# Or push for PR
git push origin feature/implement-agents
# Then create PR on GitHub/GitLab
```

### Parallel Development

```bash
# Create multiple worktrees for different features
./scripts/manage_worktree.sh create feature/task-a --sync-deps
./scripts/manage_worktree.sh create feature/task-b --sync-deps
./scripts/manage_worktree.sh create bugfix/issue-123 --sync-deps

# Each worktree is independent
# Switch between them by changing directories
cd ../labor-law-guardian-wt-feature-task-a
# Work on task A...

cd ../labor-law-guardian-wt-feature-task-b
# Work on task B simultaneously...
```

### Complete Example with Real Commands

```bash
# Step 1: Create a worktree for new feature
~/labor-law-guardian $ ./scripts/manage_worktree.sh create feature/add-api --base dev --sync-deps
[INFO] Creating worktree for branch 'feature/add-api' at: ../labor-law-guardian-wt-feature-add-api
[SUCCESS] Worktree created successfully!

# Step 2: Move to the worktree
~/labor-law-guardian $ cd ../labor-law-guardian-wt-feature-add-api

# Step 3: Work on your feature
~/labor-law-guardian-wt-feature-add-api $ git status
On branch feature/add-api

~/labor-law-guardian-wt-feature-add-api $ # ... make changes ...
~/labor-law-guardian-wt-feature-add-api $ git add backend/app/api/
~/labor-law-guardian-wt-feature-add-api $ git commit -m "Add FastAPI routes for RAG endpoints"
~/labor-law-guardian-wt-feature-add-api $ git commit -m "Add API tests"

# Step 4: Finish work and return to main worktree
~/labor-law-guardian-wt-feature-add-api $ cd ../labor-law-guardian
~/labor-law-guardian $ ./scripts/manage_worktree.sh finish feature/add-api --switch
[SUCCESS] All changes from worktree are committed to branch 'feature/add-api'
[INFO] Removing worktree directory...
[SUCCESS] Worktree removed
[INFO] Switching to branch 'feature/add-api' in main worktree...
[SUCCESS] Now on branch 'feature/add-api' in main worktree

# Step 5: You're now in main worktree with all your commits!
~/labor-law-guardian $ git log --oneline -2
abc1234 Add API tests
def5678 Add FastAPI routes for RAG endpoints

# Step 6: Merge into dev
~/labor-law-guardian $ git checkout dev
~/labor-law-guardian $ git merge feature/add-api
~/labor-law-guardian $ git push origin feature/add-api

# Step 7: Clean up the feature branch (optional)
~/labor-law-guardian $ git branch -d feature/add-api
```

## Important Notes

### Shared Docker Volumes

Docker volumes (like `qdrant_data`) are shared between the main repo and all worktrees by default. If you need isolated Docker environments:

1. Modify `docker-compose.yml` in each worktree to use different volume names
2. Or manually manage Docker containers per worktree

### Environment Files

The script automatically copies:
- `.env` (root level)
- `backend/.env`

Add more files to sync by modifying the `sync_gitignored_files()` function in the script.

### Branch Naming Conventions

Follow the project's branch naming conventions:
- `feature/<description>` - New features
- `bugfix/<description>` - Bug fixes
- `refactor/<description>` - Code refactoring
- `docs/<description>` - Documentation updates

### Cleanup

Periodically review and remove old worktrees:

```bash
# List all worktrees
./scripts/manage_worktree.sh list

# Remove unused ones
./scripts/manage_worktree.sh remove feature/old-feature
```

## Troubleshooting

### "Worktree has uncommitted changes"

```bash
# Option 1: Commit your changes
cd /path/to/worktree
git add .
git commit -m "Your commit message"

# Option 2: Stash changes
git stash

# Option 3: Force remove (loses uncommitted changes)
./scripts/manage_worktree.sh remove feature/branch --force
```

### ".env file not syncing"

Manually sync environment files:

```bash
./scripts/manage_worktree.sh sync-env feature/your-branch
```

### "Dependencies out of sync"

```bash
cd /path/to/worktree/backend
uv sync
```

## Advanced Usage

### Custom Worktree Location

If you need to create a worktree at a custom location, use git directly:

```bash
git worktree add /custom/path/my-worktree -b my-branch

# Then manually sync env files
./scripts/manage_worktree.sh sync-env my-branch
```

### Pruning Stale Worktrees

Git may track removed worktrees as stale entries:

```bash
cd /path/to/labor-law-guardian
git worktree prune
```

## See Also

- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- Project CLAUDE.md for development guidelines
