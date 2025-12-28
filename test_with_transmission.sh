#!/bin/bash
# Test seeding and leeching with transmission-cli

TORRENT_FILE="/tmp/Windows 11 original.torrent"
TRACKER_URL="http://localhost:8000/announce"
INFO_HASH="f950c7e7e17527274392c7c83339c7c743a08189"
AUTH_TOKEN="Xl6h4RL7Db9OMLM0M6Zpo8aJEy_Rlu6y09D3jO2La-s"
SOURCE_DIR="/hd-external/Operating System"
DOWNLOAD_DIR="/tmp/bt-downloads"

echo "=========================================="
echo "Testing BitTorrent Seeding/Leeching"
echo "=========================================="
echo ""
echo "Torrent: Windows 11 original"
echo "Info Hash: $INFO_HASH"
echo "Tracker: $TRACKER_URL"
echo ""

# Check if transmission-cli is installed
if ! command -v transmission-cli &> /dev/null; then
    echo "❌ transmission-cli not found"
    echo "Install it with: sudo apt-get install transmission-cli"
    exit 1
fi

# Create download directory
mkdir -p "$DOWNLOAD_DIR"

echo "=========================================="
echo "Option 1: Test Seeding (if you have the file)"
echo "=========================================="
echo ""
echo "To seed the torrent, run:"
echo ""
echo "transmission-cli \\"
echo "  --download-dir \"$SOURCE_DIR\" \\"
echo "  \"$TORRENT_FILE\""
echo ""
echo "Note: transmission-cli doesn't support custom tracker URLs directly."
echo "You need to modify the .torrent file or use a different client."
echo ""

echo "=========================================="
echo "Option 2: Use Python Tracker Simulator"
echo "=========================================="
echo ""
echo "Run inside Docker container:"
echo ""
echo "docker exec bittorrent_web python3 test_tracker_simulator.py \\"
echo "  http://localhost:8000 \\"
echo "  $INFO_HASH \\"
echo "  $AUTH_TOKEN"
echo ""

echo "=========================================="
echo "Option 3: Test with qBittorrent or Deluge"
echo "=========================================="
echo ""
echo "1. Open qBittorrent or Deluge"
echo "2. Add torrent: $TORRENT_FILE"
echo "3. In torrent properties, add tracker: $TRACKER_URL"
echo "4. Start download/seeding"
echo ""

echo "=========================================="
echo "Monitor Tracker Activity"
echo "=========================================="
echo ""
echo "View logs:"
echo "  docker-compose logs -f web | grep announce"
echo ""
echo "Check stats:"
echo "  docker exec bittorrent_web python3 manage.py shell -c \\"
echo "    \"from torrents.models import Torrent; \\"
echo "     t = Torrent.objects.get(info_hash='$INFO_HASH'); \\"
echo "     print(f'Seeders: {t.stats.seeders}, Leechers: {t.stats.leechers}')\""
echo ""

