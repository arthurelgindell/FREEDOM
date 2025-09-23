# 🚀 BETA SETUP INSTRUCTIONS FOR CCKS SYNCTHING REPLICATION

## ✅ File Already Sent
The setup script has been sent to Beta via Tailscale file transfer.

## 📋 Steps to Run on Beta Machine

### 1. Open Terminal on Beta

### 2. Get the Setup Script
```bash
# Check for received files
tailscale file get

# This will show something like:
# setup_syncthing_beta.sh from alpha.dell@
# Accept? (y/n)
# Type 'y' and press Enter
```

### 3. Make Script Executable and Run
```bash
chmod +x setup_syncthing_beta.sh
./setup_syncthing_beta.sh
```

### 4. Copy Beta's Device ID
When the script completes, it will display:
```
Beta Device ID: [LONG-STRING-OF-CHARACTERS]
```
**COPY THIS ENTIRE ID** - you'll need it for the next step

### 5. Return to Alpha and Configure
On Alpha (this machine), run:
```bash
/Volumes/DATA/FREEDOM/configure_syncthing_alpha.sh
```
When prompted, paste Beta's Device ID.

## 🔍 What the Script Does on Beta

1. **Installs Syncthing** (if not already installed)
2. **Creates RAM Disk** at `/Volumes/CCKS_RAM` (100GB)
3. **Verifies Folders**:
   - `~/.claude` (CCKS database location)
   - `/Volumes/DATA/FREEDOM` (should exist)
   - `/Volumes/CCKS_RAM/ccks_cache` (cache folder)
4. **Starts Syncthing** with web UI on port 8384
5. **Configures for Alpha** connection
6. **Displays Beta Device ID** for pairing

## ✨ Verification Steps

After both machines are configured:

### On Beta:
```bash
# Check if CCKS is working
~/.claude/ccks stats

# Once synced, you should see the same entry count as Alpha
```

### On Alpha:
```bash
# Add a test entry
~/.claude/ccks add "SYNC TEST FROM ALPHA $(date)"
```

### On Beta (after 10 seconds):
```bash
# Query for the test entry
~/.claude/ccks query "SYNC TEST FROM ALPHA"
# Should return the entry!
```

## 🎯 Success Indicators

- ✅ Both machines show as "Connected" in Syncthing web UI
- ✅ Folder status shows "Up to Date"
- ✅ CCKS entries sync within 10 seconds
- ✅ Both machines have same CCKS entry count

## 🔧 Troubleshooting

If sync doesn't work:
1. Check firewall allows port 22000 (TCP/UDP)
2. Verify both Syncthing processes are running
3. Check web UI at http://[machine-ip]:8384
4. Ensure devices are properly paired
5. Wait up to 60 seconds for initial discovery

## 📊 Monitor Progress

On Alpha, run:
```bash
/Volumes/DATA/FREEDOM/monitor_syncthing_connection.sh
```

This will show real-time connection status and sync progress.

---

**Alpha Device ID** (for reference):
`J64ABTL-XGEG4FK-IWADAUE-4GYS4NQ-UNTQE22-BZSUUU2-ZFNCRTY-WCGCYAO`