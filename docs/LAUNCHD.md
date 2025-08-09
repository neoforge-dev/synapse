# macOS Autostart (launchd)

Use launchd to automatically start the API on login. Memgraph runs via Docker.

## Steps

1) Ensure Docker Desktop starts on login (Preferences → General).
2) Copy the sample plist to your LaunchAgents and edit paths:

```bash
cp docs/macos.graphrag.api.plist.sample ~/Library/LaunchAgents/macos.graphrag.api.plist
# Edit the absolute paths inside the file to match your project and shell
launchctl load ~/Library/LaunchAgents/macos.graphrag.api.plist
launchctl start macos.graphrag.api
```

3) To stop/unload:
```bash
launchctl stop macos.graphrag.api
launchctl unload ~/Library/LaunchAgents/macos.graphrag.api.plist
```

Notes:
- The sample uses `make run-api` and assumes Memgraph is already running (`make run-memgraph` or Docker auto-start).
- Consider a second plist for Memgraph if you want it managed by launchd as well.
