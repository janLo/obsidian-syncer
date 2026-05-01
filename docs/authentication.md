# Authentication Guidelines

### Google Keep

To securely authenticate with Google Keep via `gkeepapi`, standard passwords are not recommended as they may trigger Google's automated security blocks. Instead, use an **App Password** (recommended) or a **Master Token**.

#### Using an App Password (Recommended)

An App Password is a 16-digit passcode that gives an app or device permission to access your Google Account. This requires 2-Step Verification to be enabled.

1. Go to your [Google Account](https://myaccount.google.com/).
2. Navigate to **Security** on the left panel.
3. Ensure **2-Step Verification** is turned **On**.
4. Search for "**App passwords**" in the top search bar (or find it under the 2-Step Verification settings).
5. Enter a name for the app (e.g., "Obsidian Syncer") and click **Create**.
6. Copy the generated 16-character password (you can omit the spaces) and use it as your `KEEP_PASSWORD` environment variable.

#### Using a Master Token (Advanced)

If you prefer not to use an App Password, you can extract a Master Token. The Master Token is a long string that acts as a secure session token.

Use the Master Token directly as the `KEEP_PASSWORD` in your configuration. Note that Master Tokens may eventually expire or be revoked by Google if suspicious activity is detected.

!!! tip "Nextcloud Credentials"
    Pass your Nextcloud credentials via environment variables (`NC_USER` and `NC_PASSWORD`). The configuration file will dynamically expand these variables to prevent hardcoding secrets.

### Obsidian Headless

The `obsidian-headless` tool requires an active Obsidian Sync subscription. To authenticate, you should run the container interactively once:

1. Open a terminal in the container: `docker exec -it obsidian-syncer bash`
2. Run `ob login` and follow the prompts.
3. Link the vault with `ob sync-setup --vault "YourRemoteVaultName" --path /vaults/my_vault`.
4. Restart the container so the Python daemon picks up the new sync process.
