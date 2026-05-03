# Authentication Guidelines

### Google Keep

To securely authenticate with Google Keep via `gkeepapi`, standard passwords and App Passwords are no longer supported for continuous syncing. Google's automated security blocks frequent login requests, so you **MUST** use a **Master Token**.

#### Generating a Master Token

Run the included helper script to generate a Master Token:

```bash
uv run scripts/get_keep_token.py
```

The script supports two authentication flows. You can choose the one that works best for you.

**Method 1: App Password Flow (Recommended)**
1. Ensure you have 2-Step Verification enabled on your [Google Account](https://myaccount.google.com/).
2. Navigate to **Security** and search for "**App passwords**".
3. Create a new App Password (e.g., for "Obsidian Syncer") and copy the 16-character string.
4. Run the script, select choice `1`, and provide your email and the App Password.

**Method 2: OAuth Cookie Flow (Alternative)**
If the App Password flow fails with a `BadAuthentication` error (often because Google temporarily blocks the request), use this alternative flow.
1. Open an incognito/private browser window.
2. Log into your Google account.
3. Navigate to `https://accounts.google.com/EmbeddedSetup`.
4. Open Developer Tools (F12) -> Application/Storage tab -> Cookies.
5. Find the cookie named `oauth_token` (starts with `oauth2_4/`) and copy its value.
6. Run the script, select choice `2`, and provide your email and the copied cookie.

**Final Step:**
The script will output a Master Token (starts with `aas_et/`). Use this Master Token as your `KEEP_PASSWORD` environment variable. Keep it secret!

!!! tip "Nextcloud Credentials"
    Pass your Nextcloud credentials via environment variables (`NC_USER` and `NC_PASSWORD`). The configuration file will dynamically expand these variables to prevent hardcoding secrets.

### Obsidian Headless

The `obsidian-headless` tool requires an active Obsidian Sync subscription. To authenticate, you should run the container interactively once:

1. Open a terminal in the container: `docker exec -it obsidian-syncer bash`
2. Run `ob login` and follow the prompts.
3. Link the vault with `ob sync-setup --vault "YourRemoteVaultName" --path /vaults/my_vault`.
4. Restart the container so the Python daemon picks up the new sync process.
