"""
Run once to create an owner (admin) account for one of the two businesses.
Usage: python create_admin.py
"""
import sys
import getpass
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models import Business, User, UserRole  # registers all models

# Keep in sync with DEFAULT_BUSINESSES in app/main.py
DEFAULT_BUSINESSES = [
    {"slug": "okemzhub",    "name": "OKEMZ HUB",    "tagline": "Premium Laptops, Accessible Prices"},
    {"slug": "technext360", "name": "TechNext360",  "tagline": "Smart Choices, Smarter Experience"},
]

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Ensure the businesses exist before assigning an owner to one of them.
for data in DEFAULT_BUSINESSES:
    if not db.execute(select(Business).where(Business.slug == data["slug"])).scalar_one_or_none():
        db.add(Business(**data))
db.commit()

businesses = db.execute(select(Business)).scalars().all()

print("─" * 44)
print("  Create Owner (Admin) Account")
print("─" * 44)
print("  Select the business this owner manages:")
for idx, b in enumerate(businesses, start=1):
    print(f"    {idx}. {b.name}  ({b.slug})")

choice = input(f"Business [1-{len(businesses)}] : ").strip()
try:
    business = businesses[int(choice) - 1]
except (ValueError, IndexError):
    print("✗  Invalid business selection.")
    db.close()
    sys.exit(1)

name     = input("Full name   : ").strip()
username = input("Username    : ").strip()
password = getpass.getpass("Password    : ")
confirm  = getpass.getpass("Confirm pwd : ")

if password != confirm:
    print("✗  Passwords do not match.")
    sys.exit(1)

if len(password) < 8:
    print("✗  Password must be at least 8 characters.")
    sys.exit(1)

if db.execute(select(User).where(User.username == username)).scalar_one_or_none():
    print(f"✗  Username '{username}' is already taken.")
    db.close()
    sys.exit(1)

admin = User(
    name=name,
    username=username,
    hashed_password=get_password_hash(password),
    role=UserRole.admin,
    business_id=business.id,
)
db.add(admin)
db.commit()
print(f"\n✓  Owner account '{username}' created for {business.name}. You can now start the server.")
db.close()
