# Testing Real Torrent Seeding and Leeching

This guide shows how to test seeding and leeching with a real torrent file using `mktorrent` and `transmission-cli`.

## Prerequisites

1. **mktorrent** - For creating torrent files
2. **transmission-cli** - For testing seeding/leeching (optional, can use any BitTorrent client)

## Step 1: Create Torrent File

```bash
# Create torrent from your file
mktorrent -a "http://localhost:8000/announce" \
          -c "Windows 11 Original ISO - Test Torrent" \
          -n "Windows 11 original" \
          "/hd-external/Operating System/Windows 11 original.iso"
```

This creates a `.torrent` file in the current directory.

## Step 2: Upload Torrent to Server

Run the test script to extract info hash and upload to server:

```bash
# Copy torrent to container
docker cp "/tmp/Windows 11 original.torrent" bittorrent_web:/tmp/

# Run test script
docker exec bittorrent_web python3 test_real_torrent.py /tmp/Windows\ 11\ original.torrent
```

This will:
- Extract torrent info (name, size, info hash)
- Create a test user if needed
- Create an auth token
- Upload the torrent to the database
- Display the info hash and auth token for testing

## Step 3: Test Seeding

### Option A: Using transmission-cli (if installed)

```bash
# Start seeding (you have the complete file)
transmission-cli \
  --tracker "http://localhost:8000/announce" \
  --auth "seeder_user:Xl6h4RL7Db9OMLM0M6Zpo8aJEy_Rlu6y09D3jO2La-s" \
  --download-dir "/hd-external/Operating System" \
  "/tmp/Windows 11 original.torrent"
```

### Option B: Using Python Tracker Simulator

```bash
# Use the existing tracker simulator
docker exec bittorrent_web python3 test_tracker_simulator.py \
  f950c7e7e17527274392c7c83339c7c743a08189 \
  Xl6h4RL7Db9OMLM0M6Zpo8aJEy_Rlu6y09D3jO2La-s
```

## Step 4: Test Leeching

### Option A: Using transmission-cli

```bash
# Start leeching (download to different directory)
transmission-cli \
  --tracker "http://localhost:8000/announce" \
  --auth "leecher_user:YOUR_AUTH_TOKEN" \
  --download-dir "/tmp/downloads" \
  "/tmp/Windows 11 original.torrent"
```

### Option B: Using Python Tracker Simulator

The simulator will automatically create both seeder and leecher clients.

## Step 5: Monitor Tracker

Check the tracker logs:

```bash
# View web server logs
docker-compose logs -f web | grep announce

# Check torrent stats
docker exec bittorrent_web python3 manage.py shell -c "
from torrents.models import Torrent, TorrentStats
t = Torrent.objects.get(info_hash='f950c7e7e17527274392c7c83339c7c743a08189')
print(f'Torrent: {t.name}')
print(f'Seeders: {t.stats.seeders}')
print(f'Leechers: {t.stats.leechers}')
print(f'Completed: {t.stats.completed}')
"
```

## Using Other BitTorrent Clients

You can use any BitTorrent client that supports custom trackers:

### qBittorrent
1. Add torrent file
2. Right-click → Properties → Trackers
3. Add tracker: `http://localhost:8000/announce`
4. Set authentication if required

### Deluge
1. Add torrent file
2. Right-click → Options → Trackers
3. Add tracker: `http://localhost:8000/announce`

### rTorrent
```bash
rtorrent "/tmp/Windows 11 original.torrent"
# Then in rtorrent console:
tracker.insert = "http://localhost:8000/announce"
```

## Troubleshooting

### "Invalid peer_id length"
- Make sure peer_id is exactly 20 bytes (40 hex characters)

### "Torrent not found"
- Make sure the torrent is uploaded to the database
- Check info hash matches

### "Authentication required"
- Make sure you're using a valid auth token
- Token must be associated with a user account

### "Connection refused"
- Make sure Docker containers are running: `docker-compose ps`
- Check tracker URL is correct: `http://localhost:8000/announce`

## Example Output

```
============================================================
Testing Real Torrent Seeding/Leeching
============================================================

📦 Extracting torrent information...
   Name: Windows 11 original
   Info Hash: f950c7e7e17527274392c7c83339c7c743a08189
   Size: 4.47 GB

👤 Setting up test user...
✅ Created user: seeder_user / seeder123

🔑 Creating auth token...
✅ Created auth token: Xl6h4RL7Db9OMLM0M6Zpo8aJEy_Rlu6y09D3jO2La-s

📤 Uploading torrent to server...
✅ Created torrent: Windows 11 original
   Info Hash: f950c7e7e17527274392c7c83339c7c743a08189
   Size: 4.47 GB

🌐 Testing tracker...
✅ Tracker announce successful!
```

## Notes

- The torrent file must point to `http://localhost:8000/announce` as the tracker
- Authentication is required for private trackers
- Make sure the file path is accessible when seeding
- For leeching, the client will download to the specified directory

