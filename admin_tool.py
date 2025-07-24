#!/usr/bin/env python3
"""
Local admin tool for managing blacklist without going through web endpoints
"""

import os
import json
from dotenv import load_dotenv
from content_filter import ContentFilter

load_dotenv()

def main():
    # Initialize content filter
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        print("Error: GROQ_API_KEY not found in environment")
        return
    
    cf = ContentFilter(groq_api_key)
    
    while True:
        print("\n=== Mahjong AI Admin Tool ===")
        print("1. View blacklist")
        print("2. View IP stats")
        print("3. View system stats") 
        print("4. Blacklist IP")
        print("5. Remove IP from blacklist")
        print("6. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            blacklist = cf.export_blacklist()
            if blacklist:
                print(f"\nBlacklisted IPs ({len(blacklist)}):")
                for ip, data in blacklist.items():
                    print(f"  {ip}: {data['blacklist_reason']}")
            else:
                print("\nNo IPs currently blacklisted")
                
        elif choice == "2":
            ip = input("Enter IP address: ").strip()
            stats = cf.get_ip_stats(ip)
            print(f"\nStats for {ip}:")
            print(json.dumps(stats, indent=2))
            
        elif choice == "3":
            stats = cf.get_system_stats()
            print("\nSystem Stats:")
            print(json.dumps(stats, indent=2))
            
        elif choice == "4":
            ip = input("Enter IP to blacklist: ").strip()
            reason = input("Enter reason (optional): ").strip() or "Manual admin action"
            cf.manually_blacklist_ip(ip, reason)
            print(f"IP {ip} has been blacklisted")
            
        elif choice == "5":
            ip = input("Enter IP to remove from blacklist: ").strip()
            reason = input("Enter reason (optional): ").strip() or "Manual admin removal"
            cf.unblacklist_ip(ip, reason)
            print(f"IP {ip} has been removed from blacklist")
            
        elif choice == "6":
            print("Goodbye!")
            break
            
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()