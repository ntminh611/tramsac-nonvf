#!/usr/bin/env bash
# One-shot deploy: point the app at your hosted data and push everything to GitHub.
#
# First create an EMPTY public repo on github.com (no README), then run:
#     ./deploy.sh <github-user>/<repo>
#
# After this, data is "online": re-running the scraper (or GitHub Actions, or
# editing data/stations.json right on github.com) updates every installed app —
# no app rebuild needed. (macOS sed syntax; you're on darwin.)
set -euo pipefail

REPO="${1:-}"
if [ -z "$REPO" ]; then
  echo "Usage: ./deploy.sh <github-user>/<repo>   (create the empty repo first)"
  exit 1
fi

RAW="https://raw.githubusercontent.com/${REPO}/main/data/stations.json"

# 1) wire the app to the hosted JSON
sed -i '' "s|^const String kRemoteUrl = .*|const String kRemoteUrl = '${RAW}';|" \
  app/lib/data_source.dart
echo "kRemoteUrl -> ${RAW}"

# 2) commit + push
git add -A
git commit -m "deploy: serve live station data from ${REPO}" --no-verify || true
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${REPO}.git"
git push -u origin main

echo
echo "✅ Pushed. The app now fetches live data from:"
echo "   ${RAW}"
echo "Next: on github.com open the repo → Actions tab → enable workflows"
echo "      (daily auto-refresh). To add OCM status: Settings → Secrets →"
echo "      Actions → new secret OCM_API_KEY."
