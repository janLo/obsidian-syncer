#!/usr/bin/env python3
import gpsoauth
import getpass
import uuid

def generate_android_id():
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
        for ele in range(0,8*6,8)][::-1])
    return mac.replace(':', '')

def main():
    print("Google Keep Master Token Generator")
    print("----------------------------------")
    print("This script will generate a Master Token for use with obsidian-syncer.")
    print("\nSelect Authentication Flow:")
    print("1. App Password Flow (Recommended if it works)")
    print("   - Requires 2FA and an App Password from https://myaccount.google.com/apppasswords")
    print("2. OAuth Cookie Flow (Alternative)")
    print("   - Requires logging into Google in your browser and extracting the `oauth_token` cookie")
    print("   - See docs for more details.")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice not in ['1', '2']:
        print("Invalid choice. Exiting.")
        return

    email = input("Email: ")
    
    if choice == '1':
        password = getpass.getpass("App Password: ")
        android_id = generate_android_id()
        print("\nAuthenticating...")
        res = gpsoauth.perform_master_login(email, password, android_id)
        
    elif choice == '2':
        print("\nTo get your oauth_token:")
        print("1. Open an incognito/private browser window.")
        print("2. Log into your Google account.")
        print("3. Navigate to https://accounts.google.com/EmbeddedSetup")
        print("4. Open Developer Tools (F12) -> Application/Storage tab -> Cookies.")
        print("5. Find the cookie named `oauth_token` (starts with `oauth2_4/`) and copy its value.")
        oauth_cookie_token = input("Paste your oauth_token cookie here: ")
        
        # Use a random android_id as required for the alternative flow
        # It needs to be exactly 16 lowercase hex characters
        android_id = uuid.uuid4().hex[:16]
        print("\nExchanging token...")
        res = gpsoauth.exchange_token(email, oauth_cookie_token, android_id)

    if 'Token' in res:
        print("\n✅ Success! Your Master Token is:")
        print("-" * 50)
        print(res['Token'])
        print("-" * 50)
        print("\nPlease update your KEEP_PASSWORD environment variable or config.yaml")
        print("with this Master Token. Keep it secret!")
    else:
        print(f"\n❌ Authentication failed:")
        for key, value in res.items():
            print(f"  {key}: {value}")
        if choice == '1':
            print("\nPlease ensure you are using an App Password and not your standard account password.")
            print("If you get BadAuthentication, Google may have blocked the request. Try the OAuth Cookie flow (Choice 2).")
        elif choice == '2':
            print("\nPlease ensure your oauth_token cookie is correct and has not expired.")

if __name__ == '__main__':
    main()
