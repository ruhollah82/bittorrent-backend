# BitTorrent User Guide: Creating, Seeding, and Downloading Torrents

## Overview

This guide explains how to create torrent files, share them with other users (seeding/peering), and download files from the BitTorrent network using this platform.

---

## Table of Contents

1. [Creating Torrent Files](#creating-torrent-files)
2. [Uploading Torrents to the Platform](#uploading-torrents-to-the-platform)
3. [Seeding (Sharing) Files](#seeding-sharing-files)
4. [Downloading Files](#downloading-files)
5. [BitTorrent Protocol Basics](#bittorrent-protocol-basics)
6. [Tools and Software](#tools-and-software)
7. [Troubleshooting](#troubleshooting)

---

## 1. Creating Torrent Files

### What is a Torrent File?

A `.torrent` file is a small metadata file that contains:

- **File information**: Names, sizes, and folder structure
- **Tracker URLs**: Where peers announce their presence
- **Piece information**: How files are divided for downloading
- **Info hash**: Unique identifier for the torrent

### Methods to Create Torrent Files

#### Method 1: Using qBittorrent (Recommended)

1. **Download and Install qBittorrent**

   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install qbittorrent

   # Or download from: https://www.qbittorrent.org/download
   ```

2. **Create a New Torrent**

   - Open qBittorrent
   - Go to `Tools` → `Torrent Creator`
   - Select the file or folder you want to share
   - Set the tracker URL: `http://127.0.0.1:8000/announce`
   - Add comments and other metadata
   - Click "Create Torrent"

3. **Save the .torrent file**
   - Choose a location to save the `.torrent` file
   - This file is small (usually <100KB) regardless of the content size

#### Method 2: Using Command Line Tools

**Using mktorrent:**

```bash
# Install mktorrent
sudo apt install mktorrent

# Create torrent for a single file
mktorrent -a http://127.0.0.1:8000/announce -c "Description of the file" file.mp4

# Create torrent for a directory
mktorrent -a http://127.0.0.1:8000/announce -c "Movie collection" -n "Movies" /path/to/movies/
```

**Using transmission-create:**

```bash
# Install transmission-cli
sudo apt install transmission-cli

# Create torrent
transmission-create -o output.torrent -c "Comment" -t http://127.0.0.1:8000/announce input_file.mp4
```

#### Method 3: Online Torrent Creators

**Warning:** Use trusted services only, as they may access your files

- [torrenteditor.com](https://torrenteditor.com)
- [torrents.me](https://torrents.me)

#### Method 4: Programmatic Creation

Using Python with `libtorrent`:

```python
import libtorrent as lt
import time

# Create torrent
fs = lt.file_storage()
lt.add_files(fs, "/path/to/files")
t = lt.create_torrent(fs)

# Add tracker
t.add_tracker("http://127.0.0.1:8000/announce")

# Set creator and comment
t.set_creator("Your BitTorrent Client")
t.set_comment("Description of the torrent")

# Generate torrent file
torrent_data = t.generate()
with open("output.torrent", "wb") as f:
    f.write(lt.bencode(torrent_data))
```

---

## 2. Uploading Torrents to the Platform

### Prerequisites

- **User Account**: Must be registered and logged in
- **User Class**: Must be `member`, `trusted`, or `elite` (not `newbie`)
- **Credits**: Must have at least 1.00 credit for upload
- **Valid Torrent**: Properly created `.torrent` file

### Upload Process

#### Via Web Interface

1. **Login to the platform**
2. **Navigate to Upload Section**
3. **Select Torrent File**
   - Click "Choose File" or drag & drop
   - Select your `.torrent` file
4. **Add Metadata**
   - Category (Movies, Software, Games, etc.)
   - Description (optional but recommended)
   - Tags (optional)
5. **Upload**
   - Click "Upload Torrent"
   - Wait for processing

#### Via API

```bash
# Upload torrent via API
curl -X POST \
  http://127.0.0.1:8000/api/torrents/upload/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "torrent_file=@/path/to/your/file.torrent" \
  -F "category=software" \
  -F "description=Useful software package"
```

**Success Response:**

```json
{
  "success": true,
  "message": "Torrent uploaded successfully",
  "torrent": {
    "id": 123,
    "name": "Ubuntu 20.04 ISO",
    "info_hash": "aabbccddeeff...",
    "size": "2147483648",
    "category": "software",
    "created_at": "2025-01-03T10:30:00Z"
  }
}
```

### Upload Restrictions

- **File Size**: No specific limit, but large files may take time to process
- **File Type**: Must be `.torrent` extension
- **Duplicates**: Cannot upload the same torrent twice (but can reactivate deleted ones)
- **Private Torrents**: Can be marked private (only invited users can access)

### What Happens During Upload

1. **File Validation**: Checks if it's a valid torrent file
2. **Metadata Extraction**: Parses torrent information
3. **Duplicate Check**: Verifies torrent doesn't already exist
4. **Database Storage**: Saves torrent metadata
5. **Credit Deduction**: 1.00 credit charged
6. **Statistics Creation**: Initializes seeding/downloading stats

---

## 3. Seeding (Sharing) Files

### What is Seeding?

**Seeding** means sharing a complete file with other users. When you seed:

- You upload pieces of the file to other downloaders
- You help keep the torrent alive
- You earn upload credits for sharing

### How to Start Seeding

#### Method 1: Using qBittorrent

1. **Open qBittorrent**
2. **Add Torrent**

   - File → Add Torrent File
   - Select the `.torrent` file you created/uploaded
   - **Important**: Point to the actual files you want to share

3. **Select Files to Seed**

   - Choose which files to share (usually all)
   - Set save location

4. **Start Seeding**
   - The torrent will show as "Seeding" status
   - Upload speed will show data being sent

#### Method 2: Using Transmission

```bash
# Add torrent and start seeding
transmission-remote -a /path/to/torrent.torrent

# Or specify files to seed
transmission-create -o output.torrent -t http://127.0.0.1:8000/announce /path/to/files/
transmission-remote -a output.torrent
```

#### Method 3: Using uTorrent/BitTorrent Client

1. **Open Client**
2. **File → Add Torrent**
3. **Select .torrent file**
4. **Choose files to share**
5. **Start torrent**

### Seeding Best Practices

#### Keep Your Client Running

```bash
# Run client in background
qbittorrent &
# Or use screen/tmux
screen -S seeding qbittorrent
```

#### Monitor Your Seeds

- Check upload speeds
- Monitor peer connections
- Ensure files remain accessible

#### Ratio Maintenance

- Good ratio (>1.0) helps maintain account privileges
- Platform rewards good seeders

### Seeding Statistics

The platform tracks:

- **Upload amount**: Data you've shared
- **Peers connected**: How many users you're helping
- **Seed time**: How long you've been seeding
- **Ratio**: Upload/download ratio

### Stopping Seeds

**Don't stop seeding immediately!**

- Seed until ratio reaches at least 1.0
- Help keep torrent healthy for others
- Platform may have minimum seeding requirements

---

## 4. Downloading Files

### Prerequisites

- **BitTorrent Client**: qBittorrent, uTorrent, Transmission, etc.
- **Torrent File or Magnet Link**: From uploaded torrents
- **Account**: Must be logged in to access private torrents

### Download Process

#### Method 1: Using qBittorrent

1. **Get Torrent File**

   - Download `.torrent` file from platform
   - Or copy magnet link

2. **Open in Client**

   - File → Add Torrent File
   - Or File → Add Torrent Link (for magnets)

3. **Select Download Location**

   - Choose where to save files
   - Select which files to download (if multi-file torrent)

4. **Start Download**
   - Click "OK" or "Download"
   - Monitor progress in client

#### Method 2: Using Command Line

```bash
# Using transmission-cli
transmission-cli /path/to/torrent.torrent

# Using aria2
aria2c --bt-enable-lpd --bt-tracker=http://127.0.0.1:8000/announce file.torrent

# Using rtorrent
rtorrent file.torrent
```

#### Method 3: Magnet Links

```bash
# Add magnet link directly
qbittorrent "magnet:?xt=urn:btih:...&dn=filename&tr=http://127.0.0.1:8000/announce"
```

### Download Optimization

#### Speed Optimization

```bash
# Increase connection limits
qbittorrent settings:
- Maximum connections per torrent: 200
- Maximum upload slots: 10
- Global maximum upload: 100 KB/s (leave headroom)
```

#### Port Forwarding

```bash
# Check if port is open (important for downloading)
# Use tools like canyouseeme.org or port forwarding guides
qbittorrent port: Usually 6881-6889
```

#### VPN Considerations

- Use VPN for privacy
- Ensure VPN allows BitTorrent traffic
- Check port forwarding through VPN

### Download Progress

**Stages of Download:**

1. **Connecting**: Finding peers and tracker
2. **Downloading**: Receiving file pieces
3. **Verifying**: Checking piece integrity
4. **Seeding**: Sharing with others (optional)

### File Verification

BitTorrent automatically verifies downloads using:

- **Piece hashing**: Each piece has a unique hash
- **File integrity**: Ensures complete, uncorrupted files
- **Redundancy**: Can recover from corrupted pieces

---

## 5. BitTorrent Protocol Basics

### How BitTorrent Works

#### File Division

- Large files split into small **pieces** (typically 256KB-1MB)
- Each piece has a **hash** for verification
- Pieces downloaded from multiple **peers** simultaneously

#### Peer Types

- **Seeders**: Have complete file, upload to others
- **Leechers**: Downloading, may also upload pieces they have
- **Peers**: General term for connected users

#### Tracker Communication

- **Announce**: Tell tracker you're downloading/seeding
- **Scrape**: Get torrent statistics
- **Peer Exchange**: Find other peers directly

### Network Architecture

```
[Torrent File] → [Tracker] → [Peer List] → [Direct Peer Connections]
                    ↓
            [DHT Network] (Distributed Hash Table)
                    ↓
            [Peer Discovery] (Magnet links)
```

### Key Concepts

#### Info Hash

- Unique identifier for each torrent
- Calculated from torrent metadata
- Used to find peers across the network

#### Peer ID

- Unique identifier for your client
- Helps trackers distinguish users
- Format: `-ClientNameVersion-Padding`

#### Choking/Unchoking

- **Choking**: Temporarily stop uploading to a peer
- **Unchoking**: Resume uploading
- Optimizes download speeds

#### Rare Piece First

- Downloads rare pieces first
- Ensures availability of all pieces
- Prevents bottlenecks

---

## 6. Tools and Software

### Desktop Clients

#### qBittorrent (Recommended)

```bash
sudo apt install qbittorrent
```

- Free and open source
- Cross-platform
- Built-in torrent creation
- Web UI available

#### Transmission

```bash
sudo apt install transmission
```

- Lightweight
- Command-line and GUI versions
- Good for headless servers

#### Deluge

```bash
sudo apt install deluge
```

- Plugin system
- Web interface
- Highly customizable

### Command Line Tools

#### aria2

```bash
sudo apt install aria2
aria2c --bt-enable-lpd file.torrent
```

- Multi-protocol downloader
- BitTorrent support
- High performance

#### rtorrent

```bash
sudo apt install rtorrent
```

- Text-based interface
- Very lightweight
- Good for servers

### Web Interfaces

- **qBittorrent Web UI**: Access client remotely
- **Transmission Web**: Built-in web interface
- **ruTorrent**: Web UI for rTorrent

### Mobile Clients

- **BitTorrent** (Official app)
- **uTorrent** (Mobile version)
- **Flud** (Android)
- **iTransmission** (iOS)

### Development Libraries

#### Python

```python
import libtorrent as lt

# Create session
session = lt.session()

# Add torrent
info = lt.torrent_info('file.torrent')
handle = session.add_torrent({'ti': info, 'save_path': './downloads'})

# Monitor progress
while not handle.status().is_seeding:
    print(f"Progress: {handle.status().progress * 100:.1f}%")
```

#### JavaScript (Node.js)

```javascript
const WebTorrent = require("webtorrent");

const client = new WebTorrent();

client.add("magnet:?xt=urn:btih:...", (torrent) => {
  console.log("Torrent added:", torrent.name);
});
```

---

## 7. Troubleshooting

### Common Issues

#### "No Peers Found"

**Symptoms:** Torrent stuck at 0%, no connections
**Solutions:**

- Check tracker URL is correct
- Wait a few minutes (trackers update periodically)
- Try different client
- Check firewall/antivirus blocking connections

#### Slow Download Speeds

**Symptoms:** Very slow download (<10 KB/s)
**Solutions:**

- Check internet connection
- Limit upload speed (leave bandwidth for downloading)
- Increase connection limits in client
- Try different ports (6881-6889)
- Check ISP throttling

#### "Tracker Error" or "Connection Failed"

**Symptoms:** Can't connect to tracker
**Solutions:**

- Verify tracker URL
- Check internet connectivity
- Try different DNS servers
- Check firewall settings

#### "Hash Check Failed"

**Symptoms:** Pieces failing verification
**Solutions:**

- File corruption - delete and re-download
- Bad torrent file - get from trusted source
- Client issues - try different client

#### Port Forwarding Issues

**Symptoms:** Can't connect to peers
**Solutions:**

```bash
# Check if port is open
nmap -p 6881 your-external-ip

# Or use online tools
# Visit: http://canyouseeme.org/
# Enter port: 6881
```

#### High CPU Usage

**Symptoms:** Client using too much CPU
**Solutions:**

- Reduce connection limits
- Disable DHT if not needed
- Update client to latest version
- Check for malware

### Advanced Troubleshooting

#### Network Diagnostics

```bash
# Check network connectivity
ping 127.0.0.1

# Test tracker response
curl "http://127.0.0.1:8000/announce?info_hash=..."

# Check listening ports
netstat -tlnp | grep :6881
```

#### Client-Specific Issues

**qBittorrent:**

- Check logs: `~/.config/qBittorrent/logs/`
- Reset settings to default
- Reinstall if corrupted

**Transmission:**

- Check config: `~/.config/transmission-daemon/settings.json`
- Stop service: `sudo service transmission-daemon stop`
- Edit config and restart

#### Platform-Specific Issues

**Windows:**

- Disable Windows Firewall temporarily
- Add client to antivirus exclusions
- Check Windows Defender settings

**Linux:**

- Check iptables rules
- Verify user permissions
- Check disk space

**macOS:**

- Check Little Snitch/Firewall settings
- Reset client preferences
- Check System Integrity Protection

### Getting Help

1. **Check Client Documentation**
2. **Search Error Messages**
3. **Community Forums**
4. **GitHub Issues** (for open source clients)
5. **Platform Support** (if using managed service)

---

## API Reference

### Torrent Upload

```http
POST /api/torrents/upload/
Authorization: Bearer <token>
Content-Type: multipart/form-data

Parameters:
- torrent_file: .torrent file
- category: torrent category
- description: optional description
```

### Torrent List

```http
GET /api/torrents/
Authorization: Bearer <token>

Query Parameters:
- category: filter by category
- search: search torrents
- ordering: sort by (name, size, created_at)
```

### Torrent Download

```http
GET /api/torrents/{info_hash}/download/
Authorization: Bearer <token>
```

### User Statistics

```http
GET /api/user/stats/
Authorization: Bearer <token>

Response:
{
  "upload_speed": "...",
  "download_speed": "...",
  "total_uploaded": 1234567890,
  "total_downloaded": 987654321,
  "ratio": 1.25
}
```

---

## Security Best Practices

### Safe Torrenting

- **Scan files** before opening
- **Use antivirus** software
- **Avoid suspicious torrents**
- **Check comments/ratings** before downloading
- **Verify file integrity**

### Privacy Considerations

- **Use VPN** for anonymity
- **Enable encryption** in client
- **Don't share personal information**
- **Use different clients** for different content types
- **Regularly clear client data**

### Account Security

- **Use strong passwords**
- **Enable 2FA** if available
- **Don't share account credentials**
- **Monitor account activity**
- **Log out from public computers**

---

## Conclusion

This guide covers the complete lifecycle of torrent creation, sharing, and downloading. Remember:

- **Create torrents** using reliable tools like qBittorrent
- **Upload to platform** for community sharing
- **Seed responsibly** to maintain good ratios
- **Download safely** using trusted clients
- **Troubleshoot** using systematic approaches

**Happy torrenting!** 🎬🎵📁

---

_Last updated: January 2025_
_For platform-specific questions, check the API documentation or contact support._
