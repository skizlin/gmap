#!/bin/bash
# Run this ONCE on the server (e.g. in /var/www/gmap) so Git never overwrites
# these data files when you run "git pull". Updated from GitHub: sports.csv,
# feed_sports.csv, and backend/data/markets/*.csv (market_score_type, market_period_type,
# market_templates — reference data shared between environments). All other data
# below is managed in backoffice and stays server-local.
# To undo: git update-index --no-skip-worktree <file>

set -e
cd "$(dirname "$0")/.."

# Protect everything EXCEPT sports.csv and feed_sports.csv (those two come from repo).
FILES=(
  backend/data/brands.csv
  backend/data/categories.csv
  backend/data/competitions.csv
  backend/data/domain_events.csv
  backend/data/entity_feed_mappings.csv
  backend/data/event_mappings.csv
  backend/data/feeder_config.csv
  backend/data/feeder_event_notes.csv
  backend/data/feeder_ignored_events.csv
  backend/data/feeds.csv
  backend/data/feed_time_statuses.csv
  backend/data/languages.csv
  backend/data/margin_template_competitions.csv
  backend/data/margin_templates.csv
  backend/data/markets.csv
  backend/data/partners.csv
  backend/data/sport_feed_mappings.csv
  backend/data/teams.csv
  backend/data/translations.csv
)

for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    git update-index --skip-worktree "$f"
    echo "Protected: $f"
  else
    echo "Skip (not found): $f"
  fi
done
echo "Done. git pull will update sports.csv, feed_sports.csv, and backend/data/markets/*.csv; these files stay local."
