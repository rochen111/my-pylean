#!/bin/bash

set -euo pipefail

confirm_clean() {
    if [[ "${LEAN_REBASE_CLEAN_CONFIRM:-}" == "yes" ]]; then
        return 0
    fi

    echo "This script runs: git clean -xqdf"
    echo "It will DELETE all untracked/ignored files in this repo."
    read -r -p "Continue? Type YES to proceed: " answer
    if [[ "$answer" != "YES" ]]; then
        echo "Aborted. No cleanup was performed."
        exit 1
    fi
}

echo "Start Rebasing Organization Branches"
git config user.name "$(git log -n 1 --pretty=format:%an)"
git config user.email "$(git log -n 1 --pretty=format:%ae)"

confirm_clean

git remote set-branches origin '*'
git checkout -- .
git clean -xqdf

for branch in $(git for-each-ref refs/remotes/origin/* | cut -d"$(printf '\t')" -f2 | cut -b21- | grep ^org-)
do
    echo "Rebasing branch $branch"
    git checkout $branch
    git rebase master
    retVal=$?
    if [ $retVal -eq 0 ]; then
        echo "Pushing branch $branch"
        git push --force-with-lease --set-upstream origin $branch
    else
        echo "Rebase failed branch $branch"
        git rebase --abort
    fi
    git checkout master
    git clean -xqdf
done
