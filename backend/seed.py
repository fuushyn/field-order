"""Seed the database with demo data."""
from database import engine, Base, SessionLocal
from models import SalesRep, Retailer, Product
from auth import hash_password


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing data
    db.query(Product).delete()
    db.query(Retailer).delete()
    db.query(SalesRep).delete()
    db.commit()

    # Sales rep
    rep = SalesRep(
        username="rep1",
        password_hash=hash_password("password"),
        name="Alex Johnson",
        email="alex@fieldorder.com",
    )
    db.add(rep)
    db.flush()

    # Retailers
    retailers = [
        Retailer(
            name="QuickMart Downtown",
            address="123 Main St, Springfield, IL 62701",
            contact_phone="(217) 555-0101",
            contact_email="manager@quickmart.com",
            rep_id=rep.id,
        ),
        Retailer(
            name="FreshStop Groceries",
            address="456 Oak Ave, Springfield, IL 62702",
            contact_phone="(217) 555-0202",
            contact_email="orders@freshstop.com",
            rep_id=rep.id,
        ),
        Retailer(
            name="Corner Convenience",
            address="789 Elm Blvd, Springfield, IL 62703",
            contact_phone="(217) 555-0303",
            contact_email="info@cornershop.com",
            rep_id=rep.id,
        ),
    ]
    db.add_all(retailers)

    # Products
    products = [
        # Beverages
        Product(sku="BEV-001", name="Cola Classic 24-pack", category="Beverages", unit_price=18.99, unit="case"),
        Product(sku="BEV-002", name="Orange Juice 12-pack", category="Beverages", unit_price=24.50, unit="case"),
        Product(sku="BEV-003", name="Sparkling Water 24-pack", category="Beverages", unit_price=14.99, unit="case"),
        Product(sku="BEV-004", name="Energy Drink 12-pack", category="Beverages", unit_price=29.99, unit="case"),
        # Snacks
        Product(sku="SNK-001", name="Potato Chips Variety Box", category="Snacks", unit_price=22.00, unit="box"),
        Product(sku="SNK-002", name="Granola Bars 48-ct", category="Snacks", unit_price=19.50, unit="box"),
        Product(sku="SNK-003", name="Mixed Nuts 12-pack", category="Snacks", unit_price=35.00, unit="box"),
        Product(sku="SNK-004", name="Pretzels 24-pack", category="Snacks", unit_price=16.75, unit="box"),
        # Dairy
        Product(sku="DAI-001", name="Whole Milk 1 Gallon", category="Dairy", unit_price=4.29, unit="piece"),
        Product(sku="DAI-002", name="Cheddar Cheese Block", category="Dairy", unit_price=6.99, unit="piece"),
        Product(sku="DAI-003", name="Greek Yogurt 12-pack", category="Dairy", unit_price=15.00, unit="case"),
        # Bakery
        Product(sku="BAK-001", name="White Bread Loaf", category="Bakery", unit_price=3.49, unit="piece"),
        Product(sku="BAK-002", name="Hamburger Buns 8-pack", category="Bakery", unit_price=4.99, unit="piece"),
        Product(sku="BAK-003", name="Croissants 12-ct", category="Bakery", unit_price=12.00, unit="box"),
        # Cleaning
        Product(sku="CLN-001", name="All-Purpose Cleaner 6-pack", category="Cleaning", unit_price=21.00, unit="case"),
        Product(sku="CLN-002", name="Paper Towels 12-roll", category="Cleaning", unit_price=18.50, unit="case", in_stock=False),
    ]
    db.add_all(products)

    db.commit()
    db.close()
    print("Seeded: 1 rep, 3 retailers, 16 products")


if __name__ == "__main__":
    seed()
