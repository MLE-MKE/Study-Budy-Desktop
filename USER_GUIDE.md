# Study Budy Desktop user guide

Study Budy Desktop is a Windows app for Twitch streamers who run study, coworking, productivity, or body-doubling streams.

## Install Study Budy

Use the installer file:

```text
Study-Budy-Desktop-v0.1.0-Windows-Setup.exe
```

Double-click it and follow the setup screens. The installer adds Study Budy Desktop to your Start Menu. You can also choose to create a Desktop shortcut.

If you received the portable ZIP instead, extract it first, then open:

```text
Study Budy.exe
```

## First launch

When Study Budy opens:

1. Go to **Connections**.
2. Enter your Twitch Client ID.
3. Connect your streamer account.
4. Optionally connect a bot account if you want chat replies to come from a separate Twitch account.
5. Go to **Dashboard**.
6. Click **Start** to start the local overlay service.
7. Copy the overlay URLs into OBS or Streamlabs Desktop Browser Sources.

Study Budy does not ask for your Twitch password. Do not paste a Client Secret, access token, refresh token, or password into the Client ID field.

## Twitch setup

If you need your own Twitch Client ID:

1. Open the Twitch Developer Console.
2. Register a new application.
3. Use a public/native app style registration. Do not use a Client Secret in Study Budy.
4. Select a category appropriate for chat bot or productivity tools.
5. Copy only the Client ID into Study Budy.

The same Client ID can be used to connect both your streamer account and optional bot account.

## OBS and Streamlabs Desktop

Start the overlay service, then add Browser Sources using these local URLs:

- Task overlay: `http://127.0.0.1:5155/overlay`
- Timer overlay: `http://127.0.0.1:5155/timer`
- Check-In overlay: `http://127.0.0.1:5155/checkin`

Use 1920 × 1080 at 30 FPS as a starting point. The overlays are local to your computer and should not require administrator permission.

## Saved files and logs

Study Budy stores your settings, database, uploads, backups, and logs here:

```text
%LOCALAPPDATA%\Study Budy
```

Logs are here:

```text
%LOCALAPPDATA%\Study Budy\logs
```

Twitch OAuth credentials are stored securely in Windows Credential Manager through the app's credential system.

## Updating Study Budy

Install the new version over the old version. Normal updates should preserve your saved tasks, settings, and credentials because user data is stored outside the installation folder.

## Uninstalling Study Budy

Use Windows **Apps & features** or **Installed apps** to uninstall Study Budy Desktop. The normal uninstall removes the app files but preserves your saved data in `%LOCALAPPDATA%\Study Budy`.

## Troubleshooting

- If the app does not open, check `%LOCALAPPDATA%\Study Budy\logs\startup-error.log`.
- If overlays do not load in OBS, open the same URL in a browser and make sure the Dashboard says the overlay service is Live.
- If Twitch chat stays disconnected, reconnect the streamer account in **Connections**.
- If you changed the Twitch Client ID, reconnect your Twitch accounts so the new app ID can authorize them.
- If SmartScreen warns you, this test build is unsigned. Only continue if you trust the source of the installer.
