#!/bin/bash
# git_remote_guard.sh — item 20: refuse to push when any git remote URL carries a credential
# (https://TOKEN@github.com/..., https://user:pass@...). Prints the remote names only, never the URL.
# Installed as .git/hooks/pre-push by:  tools/git_remote_guard.sh --install
# Use an SSH deploy key (git@github-one2lvos:one2lv-com/One2lvos.git, as this machine does) or a credential helper.
cd "$(git rev-parse --show-toplevel 2>/dev/null || dirname "$0"/..)" || exit 2
if [ "${1:-}" = "--install" ]; then
  hook=.git/hooks/pre-push
  [ -e "$hook" ] && [ ! -e "$hook.before_guard" ] && cp -p "$hook" "$hook.before_guard"
  printf '#!/bin/bash\nexec "$(git rev-parse --show-toplevel)/tools/git_remote_guard.sh"\n' > "$hook"
  chmod +x "$hook"; echo "installed pre-push guard"; exit 0
fi
bad=0
while read -r name url; do
  if echo "$url" | grep -qE '^[a-z+]+://[^/@]+@'; then
    echo "REFUSED: remote '$name' has a credential in its URL. Switch it to SSH or a credential helper:"
    echo "  git remote set-url $name git@github.com:<owner>/<repo>.git"
    bad=1
  fi
done < <(git config --get-regexp '^remote\..*\.(url|pushurl)$' | sed -E 's/^remote\.([^.]+)\.(push)?url /\1 /')
[ $bad -eq 0 ] && echo "OK: no credentials in git remote URLs"
exit $bad
