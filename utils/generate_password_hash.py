"""
Helper script to generate password hashes for owner/admin accounts in secrets.toml

⚠️ NOTE: This is ONLY needed for:
- Creating the initial owner account password hash for secrets.toml
- Changing owner password later
- Adding backup owner/admin accounts to secrets.toml

Regular users should use the signup form in the app - they don't need this script!

Usage:
    python utils/generate_password_hash.py
"""
import hashlib
import getpass

def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

if __name__ == "__main__":
    print("=" * 60)
    print("Password Hash Generator for secrets.toml")
    print("=" * 60)
    print("\n⚠️  Use this ONLY for owner/admin accounts in secrets.toml")
    print("   Regular users should use the signup form in the app!\n")
    
    password = getpass.getpass("Enter password to hash: ")
    
    hashed = hash_password(password)
    print(f"\n✅ Password hash generated:")
    print(f"\n{hashed}")
    print("\n📝 Copy this hash to your .streamlit/secrets.toml file")
    print("=" * 60)

