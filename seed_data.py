"""
Populate the database with realistic mock data for the shared store used by the
two sister businesses (OKEMZ HUB + TechNext360).
Run: python seed_data.py
Safe to re-run — skips if products already exist.
"""
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models import (  # ensures all tables are created
    Business,
    User, UserRole,
    Product,
    InventoryItem, ItemStatus,
    InventoryRequest, RequestStatus,
    Sale,
    Expense, ExpenseStatus,
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.execute(select(Product)).scalars().first():
    print("Seed data already exists. Delete okemzhub.db and re-run to reset.")
    db.close()
    sys.exit(0)

def ago(days=0, hours=0):
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)

# ─── Businesses (shared DB, separate books) ──────────────────────────────────
biz_defs = [
    {"slug": "okemzhub",    "name": "OKEMZ HUB",   "tagline": "Premium Laptops, Accessible Prices"},
    {"slug": "technext360", "name": "TechNext360", "tagline": "Smart Choices, Smarter Experience"},
]
for data in biz_defs:
    if not db.execute(select(Business).where(Business.slug == data["slug"])).scalar_one_or_none():
        db.add(Business(**data))
db.commit()

okemz = db.execute(select(Business).where(Business.slug == "okemzhub")).scalar_one()
technext = db.execute(select(Business).where(Business.slug == "technext360")).scalar_one()

# ─── Owners (one per business) + their staff ─────────────────────────────────
owner_okemz = User(name="Amina Okem",  username="okem_owner", hashed_password=get_password_hash("okem1234"), role=UserRole.admin, business_id=okemz.id)
owner_tech  = User(name="Zainab Okem", username="tech_owner", hashed_password=get_password_hash("tech1234"), role=UserRole.admin, business_id=technext.id)
staff1 = User(name="Chidi Okafor",  username="chidi", hashed_password=get_password_hash("chidi123"), role=UserRole.staff, monthly_sales_target=3_500_000, business_id=okemz.id)
staff2 = User(name="Amaka Johnson", username="amaka", hashed_password=get_password_hash("amaka123"), role=UserRole.staff, monthly_sales_target=3_000_000, business_id=technext.id)
db.add_all([owner_okemz, owner_tech, staff1, staff2])
db.commit()

# ─── Products (SHARED across both businesses) ────────────────────────────────
products = [
    Product(brand="Apple",   model_name="MacBook Air M2 13-inch",     base_price=1_400_000, specifications="8GB RAM, 256GB SSD, Apple M2 chip, 13.6-inch Liquid Retina display, Midnight colour, 18-hour battery"),
    Product(brand="Apple",   model_name="MacBook Pro M3 14-inch",      base_price=2_100_000, specifications="8GB RAM, 512GB SSD, Apple M3 chip, 14-inch Liquid Retina XDR display, Space Grey, ProRes video"),
    Product(brand="Apple",   model_name="MacBook Pro M3 Pro 16-inch",  base_price=3_200_000, specifications="18GB RAM, 512GB SSD, Apple M3 Pro chip, 16-inch Liquid Retina XDR display, Space Black"),
    Product(brand="Dell",    model_name="XPS 15 9530",                 base_price=1_250_000, specifications="16GB RAM, 512GB NVMe SSD, Intel Core i7-13700H, 15.6-inch OLED 3.5K touch display, Platinum Silver"),
    Product(brand="Lenovo",  model_name="ThinkPad X1 Carbon Gen 11",   base_price=1_050_000, specifications="16GB RAM, 512GB SSD, Intel Core i7-1365U, 14-inch IPS anti-glare display, Carbon Black, 15-hour battery"),
    Product(brand="HP",      model_name="Spectre x360 14",             base_price=900_000,   specifications="16GB RAM, 512GB SSD, Intel Core i7-1355U, 14-inch 2.8K OLED touch 360° display, Nightfall Black"),
]
db.add_all(products)
db.commit()

p_air, p_pro14, p_pro16, p_dell, p_lenovo, p_hp = products

# ─── Inventory Items (SHARED pool) ───────────────────────────────────────────
def unit(product, serial, status=ItemStatus.available, fault=None, added_days_ago=0):
    return InventoryItem(
        product_id=product.id, serial_number=serial, status=status,
        fault_description=fault,
        date_added=ago(added_days_ago),
    )

items = [
    # MacBook Air M2 — 3 available, 2 sold
    unit(p_air,    "MBA2-NG-001", added_days_ago=45),
    unit(p_air,    "MBA2-NG-002", added_days_ago=40),
    unit(p_air,    "MBA2-NG-003", ItemStatus.sold, added_days_ago=35),
    unit(p_air,    "MBA2-NG-004", ItemStatus.sold, added_days_ago=30),
    unit(p_air,    "MBA2-NG-005", added_days_ago=20),
    # MacBook Pro M3 14 — 2 available, 1 sold, 1 faulty
    unit(p_pro14,  "MBP14-NG-001", added_days_ago=50),
    unit(p_pro14,  "MBP14-NG-002", ItemStatus.sold, added_days_ago=38),
    unit(p_pro14,  "MBP14-NG-003", ItemStatus.faulty, fault="Screen flicker on startup, needs display replacement", added_days_ago=28),
    unit(p_pro14,  "MBP14-NG-004", added_days_ago=10),
    # MacBook Pro M3 Pro 16 — 2 available, 1 sold
    unit(p_pro16,  "MBP16-NG-001", added_days_ago=60),
    unit(p_pro16,  "MBP16-NG-002", ItemStatus.sold, added_days_ago=25),
    unit(p_pro16,  "MBP16-NG-003", added_days_ago=8),
    # Dell XPS 15 — 2 available
    unit(p_dell,   "DXPS15-NG-001", added_days_ago=55),
    unit(p_dell,   "DXPS15-NG-002", ItemStatus.sold, added_days_ago=18),
    # Lenovo ThinkPad — 1 available, 1 faulty
    unit(p_lenovo, "TPXC-NG-001", added_days_ago=42),
    unit(p_lenovo, "TPXC-NG-002", ItemStatus.faulty, fault="Battery not charging, swollen battery detected", added_days_ago=30),
    # HP Spectre — 2 available
    unit(p_hp,     "HPX360-NG-001", added_days_ago=35),
    unit(p_hp,     "HPX360-NG-002", added_days_ago=12),
]
db.add_all(items)
db.commit()

# helper: find item by serial
def item(serial):
    return next(i for i in items if i.serial_number == serial)

# ─── Sales (scoped to each seller's business) ────────────────────────────────
# Sold items must have matching Sale records. Business is derived from the seller.
sold_pairs = [
    (item("MBA2-NG-003"),   staff1,  1_600_000, ago(days=32)),   # Okemzhub
    (item("MBA2-NG-004"),   staff2,  1_580_000, ago(days=28)),   # TechNext360
    (item("MBP14-NG-002"),  staff1,  2_350_000, ago(days=22)),   # Okemzhub
    (item("MBP16-NG-002"),  staff2,  3_500_000, ago(days=20)),   # TechNext360
    (item("DXPS15-NG-002"), staff1,  1_400_000, ago(days=12)),   # Okemzhub
]
sales = [
    Sale(inventory_item_id=inv.id, sold_by_user_id=seller.id,
         business_id=seller.business_id, selling_price=price, date_sold=date)
    for inv, seller, price, date in sold_pairs
]
db.add_all(sales)
db.commit()

# ─── Expenses (scoped to each submitter's business) ──────────────────────────
expenses = [
    Expense(submitted_by_user_id=owner_okemz.id, business_id=okemz.id,    amount=85_000,  description="Shop rent — August 2026",             status=ExpenseStatus.approved, date=ago(days=30)),
    Expense(submitted_by_user_id=owner_okemz.id, business_id=okemz.id,    amount=22_500,  description="Electricity bill and generator fuel", status=ExpenseStatus.approved, date=ago(days=28)),
    Expense(submitted_by_user_id=staff1.id,      business_id=okemz.id,    amount=15_000,  description="Customer delivery (Lagos Island)",    status=ExpenseStatus.approved, date=ago(days=20)),
    Expense(submitted_by_user_id=staff1.id,      business_id=okemz.id,    amount=12_000,  description="Screen cleaning kit and accessories", status=ExpenseStatus.pending,  date=ago(days=5)),
    Expense(submitted_by_user_id=owner_tech.id,  business_id=technext.id, amount=30_000,  description="TechNext360 shop signage",            status=ExpenseStatus.approved, date=ago(days=26)),
    Expense(submitted_by_user_id=staff2.id,      business_id=technext.id, amount=8_500,   description="Packaging materials restock",         status=ExpenseStatus.approved, date=ago(days=14)),
    Expense(submitted_by_user_id=staff2.id,      business_id=technext.id, amount=30_000,  description="Local transport for stock collection",status=ExpenseStatus.pending,  date=ago(days=2)),
]
db.add_all(expenses)
db.commit()

# ─── Sample Inventory Requests (SHARED stock pipeline) ───────────────────────
requests = [
    InventoryRequest(product_id=p_air.id,   serial_number="MBA2-NG-006", requested_by_user_id=staff1.id, status=RequestStatus.pending,  date_requested=ago(days=1, hours=3)),
    InventoryRequest(product_id=p_pro14.id, serial_number="MBP14-NG-005", requested_by_user_id=staff2.id, status=RequestStatus.pending, date_requested=ago(hours=5)),
    InventoryRequest(product_id=p_dell.id,  serial_number="DXPS15-NG-003", requested_by_user_id=staff1.id, status=RequestStatus.approved, date_requested=ago(days=10)),
    InventoryRequest(product_id=p_hp.id,    serial_number="HPX360-BAD-001", requested_by_user_id=staff2.id, status=RequestStatus.rejected, rejection_reason="Serial number format is incorrect, please verify with supplier", date_requested=ago(days=8)),
]
db.add_all(requests)
db.commit()
available_count = sum(1 for i in items if i.status == ItemStatus.available)
sold_count      = sum(1 for i in items if i.status == ItemStatus.sold)
faulty_count    = sum(1 for i in items if i.status == ItemStatus.faulty)
db.close()

print("\u2714  Mock data loaded successfully!")
print(f"   Businesses : OKEMZ HUB + TechNext360 (shared products & inventory)")
print(f"   Products   : {len(products)}")
print(f"   Units      : {len(items)}  ({available_count} available, {sold_count} sold, {faulty_count} faulty)")
print(f"   Sales      : {len(sold_pairs)}   Expenses: {len(expenses)}   Requests: {len(requests)}")
print("\n   Logins:")
print("     OKEMZ HUB    owner:  okem_owner / okem1234    staff: chidi / chidi123")
print("     TechNext360  owner:  tech_owner / tech1234    staff: amaka / amaka123")
