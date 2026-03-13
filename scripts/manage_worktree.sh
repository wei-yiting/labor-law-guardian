#!/bin/bash

# Git Worktree Management Script
# Provides commands to create, merge, list, and remove git worktrees for parallel development

set -e

PROJECT_NAME="labor-law-guardian"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKTREE_PREFIX="${PROJECT_NAME}-wt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    cat << EOF
Usage: $(basename "$0") <command> [options]

Commands:
    create <branch-name>        Create a new worktree with the specified branch name
                                Options:
                                  --base <branch>       Base branch to create from (default: current branch)
                                  --sync-deps           Run 'uv sync' after creation
                                  --start-docker        Run 'docker-compose up -d' after creation

    finish <worktree-name>      Finish work on worktree - the branch will be available in main worktree
                                Options:
                                  --no-remove          Keep worktree after finishing
                                  --switch             Switch to the branch in main worktree after removal

    list                        List all active worktrees

    remove <worktree-name>      Remove a worktree
                                Options:
                                  --force              Force remove even if worktree has uncommitted changes

    sync-env <worktree-name>    Sync .env and other gitignored files to worktree

    help                        Show this help message

Examples:
    $(basename "$0") create feature/add-auth
    $(basename "$0") create feature/refactor-rag --base dev --sync-deps
    $(basename "$0") finish feature/add-auth
    $(basename "$0") finish feature/add-auth --switch
    $(basename "$0") list
    $(basename "$0") remove feature/add-auth
    $(basename "$0") sync-env feature/add-auth

EOF
}

# Get worktree directory path from branch name
get_worktree_path() {
    local branch_name="$1"
    local sanitized_name=$(echo "$branch_name" | sed 's/\//-/g')
    echo "$(dirname "$PROJECT_ROOT")/${WORKTREE_PREFIX}-${sanitized_name}"
}

# Copy gitignored files to worktree
sync_gitignored_files() {
    local worktree_path="$1"

    log_info "Syncing gitignored files to worktree..."

    # List of files to sync
    local files_to_sync=(
        ".env"
        "backend/.env"
    )

    for file in "${files_to_sync[@]}"; do
        local src="$PROJECT_ROOT/$file"
        local dst="$worktree_path/$file"

        if [ -f "$src" ]; then
            mkdir -p "$(dirname "$dst")"
            cp "$src" "$dst"
            log_success "Copied $file"
        else
            log_warn "File not found: $file (skipping)"
        fi
    done

    # Copy qdrant_data if it exists (for local vector DB)
    if [ -d "$PROJECT_ROOT/qdrant_data" ]; then
        log_info "Qdrant data detected - will be shared via docker-compose"
    fi
}

# Create a new worktree
cmd_create() {
    local branch_name=""
    local base_branch=""
    local sync_deps=false
    local start_docker=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --base)
                base_branch="$2"
                shift 2
                ;;
            --sync-deps)
                sync_deps=true
                shift
                ;;
            --start-docker)
                start_docker=true
                shift
                ;;
            *)
                if [ -z "$branch_name" ]; then
                    branch_name="$1"
                    shift
                else
                    log_error "Unknown argument: $1"
                    return 1
                fi
                ;;
        esac
    done

    if [ -z "$branch_name" ]; then
        log_error "Branch name is required"
        show_usage
        return 1
    fi

    # Use current branch as base if not specified
    if [ -z "$base_branch" ]; then
        base_branch=$(cd "$PROJECT_ROOT" && git branch --show-current)
        log_info "Using current branch '$base_branch' as base"
    fi

    local worktree_path=$(get_worktree_path "$branch_name")

    # Check if worktree already exists
    if [ -d "$worktree_path" ]; then
        log_error "Worktree already exists at: $worktree_path"
        return 1
    fi

    log_info "Creating worktree for branch '$branch_name' at: $worktree_path"

    # Create worktree
    cd "$PROJECT_ROOT"
    git worktree add -b "$branch_name" "$worktree_path" "$base_branch"

    # Sync gitignored files
    sync_gitignored_files "$worktree_path"

    # Sync dependencies if requested
    if [ "$sync_deps" = true ]; then
        log_info "Installing dependencies with uv..."
        cd "$worktree_path/backend"
        uv sync
    fi

    # Start docker services if requested
    if [ "$start_docker" = true ]; then
        log_info "Starting Docker services..."
        cd "$worktree_path"
        docker-compose up -d
    fi

    log_success "Worktree created successfully!"
    log_info "To start working:"
    echo "    cd $worktree_path"

    if [ "$sync_deps" = false ]; then
        log_info "To install dependencies:"
        echo "    cd $worktree_path/backend && uv sync"
    fi

    if [ "$start_docker" = false ]; then
        log_info "To start Docker services:"
        echo "    cd $worktree_path && docker-compose up -d"
    fi
}

# Finish work on worktree and return to main worktree
cmd_finish() {
    local worktree_name=""
    local remove_worktree=true
    local switch_to_branch=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-remove)
                remove_worktree=false
                shift
                ;;
            --switch)
                switch_to_branch=true
                shift
                ;;
            *)
                if [ -z "$worktree_name" ]; then
                    worktree_name="$1"
                    shift
                else
                    log_error "Unknown argument: $1"
                    return 1
                fi
                ;;
        esac
    done

    if [ -z "$worktree_name" ]; then
        log_error "Worktree name is required"
        show_usage
        return 1
    fi

    local worktree_path=$(get_worktree_path "$worktree_name")

    if [ ! -d "$worktree_path" ]; then
        log_error "Worktree not found at: $worktree_path"
        return 1
    fi

    # Check if worktree has uncommitted changes
    cd "$worktree_path"
    if ! git diff-index --quiet HEAD --; then
        log_error "Worktree has uncommitted changes. Please commit or stash them first."
        return 1
    fi

    local branch_name="$worktree_name"

    log_success "All changes from worktree are committed to branch '$branch_name'"
    log_info "This branch is now available in your main worktree at: $PROJECT_ROOT"

    if [ "$remove_worktree" = true ]; then
        log_info "Removing worktree directory..."
        cd "$PROJECT_ROOT"
        git worktree remove "$worktree_path"
        log_success "Worktree removed"
    else
        log_info "Worktree kept at: $worktree_path"
        cd "$PROJECT_ROOT"
    fi

    if [ "$switch_to_branch" = true ]; then
        log_info "Switching to branch '$branch_name' in main worktree..."
        git checkout "$branch_name"
        log_success "Now on branch '$branch_name' in main worktree"
        log_info "Current location: $PROJECT_ROOT"
    else
        log_info "To work with this branch in main worktree:"
        echo "    cd $PROJECT_ROOT"
        echo "    git checkout $branch_name"
        echo ""
        log_info "To merge into another branch (e.g., dev):"
        echo "    cd $PROJECT_ROOT"
        echo "    git checkout dev"
        echo "    git merge $branch_name"
        echo ""
        log_info "To push to remote:"
        echo "    git push origin $branch_name"
    fi
}

# List all worktrees
cmd_list() {
    cd "$PROJECT_ROOT"
    log_info "Active worktrees:"
    git worktree list
}

# Remove a worktree
cmd_remove() {
    local worktree_name=""
    local force=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force=true
                shift
                ;;
            *)
                if [ -z "$worktree_name" ]; then
                    worktree_name="$1"
                    shift
                else
                    log_error "Unknown argument: $1"
                    return 1
                fi
                ;;
        esac
    done

    if [ -z "$worktree_name" ]; then
        log_error "Worktree name is required"
        show_usage
        return 1
    fi

    local worktree_path=$(get_worktree_path "$worktree_name")

    if [ ! -d "$worktree_path" ]; then
        log_error "Worktree not found at: $worktree_path"
        return 1
    fi

    # Check for uncommitted changes
    if [ "$force" = false ]; then
        cd "$worktree_path"
        if ! git diff-index --quiet HEAD --; then
            log_error "Worktree has uncommitted changes. Use --force to remove anyway."
            return 1
        fi
    fi

    log_warn "Removing worktree at: $worktree_path"
    cd "$PROJECT_ROOT"

    if [ "$force" = true ]; then
        git worktree remove --force "$worktree_path"
    else
        git worktree remove "$worktree_path"
    fi

    log_success "Worktree removed"
    log_info "Note: The branch '$worktree_name' still exists. To delete it:"
    echo "    git branch -d $worktree_name"
}

# Sync environment files to worktree
cmd_sync_env() {
    local worktree_name="$1"

    if [ -z "$worktree_name" ]; then
        log_error "Worktree name is required"
        show_usage
        return 1
    fi

    local worktree_path=$(get_worktree_path "$worktree_name")

    if [ ! -d "$worktree_path" ]; then
        log_error "Worktree not found at: $worktree_path"
        return 1
    fi

    sync_gitignored_files "$worktree_path"
    log_success "Environment files synced to worktree"
}

# Main command dispatcher
main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi

    local command="$1"
    shift

    case "$command" in
        create)
            cmd_create "$@"
            ;;
        finish|merge)
            cmd_finish "$@"
            ;;
        list)
            cmd_list "$@"
            ;;
        remove)
            cmd_remove "$@"
            ;;
        sync-env)
            cmd_sync_env "$@"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
