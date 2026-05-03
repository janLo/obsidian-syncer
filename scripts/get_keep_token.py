#!/usr/bin/env python3
import gpsoauth
import getpass
import uuid

def main():
    print("Google Keep Master Token Generator")
    print("----------------------------------")
    print("This script will generate a Master Token for use with obsidian-syncer.")
    print("You must provide your Google Account email and an App Password.")
    print("If you have 2FA enabled, go to https://myaccount.google.com/apppasswords")
    print("to generate an App Password.")
    print()

    email = input("Email: ")
    password = getpass.getpass("App Password: ")

    # Generate a MAC address based device ID similar to gkeepapi's default
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
        for ele in range(0,8*6,8)][::-1])
    android_id = mac.replace(':', '')

    print("\nAuthenticating...")
    res = gpsoauth.perform_master_login(email, password, android_id)
    
    if 'Token' in res:
        print("\nSuccess! Your Master Token is:")
        print("-" * 50)
        print(res['Token'])
        print("-" * 50)
        print("\nPlease update your KEEP_PASSWORD environment variable or config.yaml")
        print("with this Master Token. Keep it secret!")
    else:
        print(f"\nAuthentication failed:")
        for key, value in res.items():
            print(f"  {key}: {value}")
        print("\nPlease ensure you are using an App Password and not your standard account password.")
        print("If you still get BadAuthentication, Google may have temporarily blocked the request.")

if __name__ == '__main__':
    main()
