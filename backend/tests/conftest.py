"""
Shared pytest fixtures for the OCR cart generation test suite.
"""
import sys
import os

# Ensure the backend directory is on the path so all modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Product, SalesRep, Retailer
from auth import hash_password

# ---------------------------------------------------------------------------
# In-memory SQLite test database
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    _seed_test_db(session)
    yield session
    session.close()


def _seed_test_db(session):
    """Seed the test database with the same 16 products used in production."""
    rep = SalesRep(
        username="testrep",
        password_hash=hash_password("testpass"),
        name="Test Rep",
        email="testrep@test.com",
    )
    session.add(rep)
    session.flush()

    retailer = Retailer(
        name="Test Store",
        address="1 Test St",
        rep_id=rep.id,
    )
    session.add(retailer)

    products = [
        # Beverages
        Product(id=1,  sku="BEV-001", name="Cola Classic 24-pack",     category="Beverages", unit_price=18.99, unit="case"),
        Product(id=2,  sku="BEV-002", name="Orange Juice 12-pack",      category="Beverages", unit_price=24.50, unit="case"),
        Product(id=3,  sku="BEV-003", name="Sparkling Water 24-pack",   category="Beverages", unit_price=14.99, unit="case"),
        Product(id=4,  sku="BEV-004", name="Energy Drink 12-pack",      category="Beverages", unit_price=29.99, unit="case"),
        # Snacks
        Product(id=5,  sku="SNK-001", name="Potato Chips Variety Box",  category="Snacks",    unit_price=22.00, unit="box"),
        Product(id=6,  sku="SNK-002", name="Granola Bars 48-ct",        category="Snacks",    unit_price=19.50, unit="box"),
        Product(id=7,  sku="SNK-003", name="Mixed Nuts 12-pack",        category="Snacks",    unit_price=35.00, unit="box"),
        Product(id=8,  sku="SNK-004", name="Pretzels 24-pack",          category="Snacks",    unit_price=16.75, unit="box"),
        # Dairy
        Product(id=9,  sku="DAI-001", name="Whole Milk 1 Gallon",       category="Dairy",     unit_price=4.29,  unit="piece"),
        Product(id=10, sku="DAI-002", name="Cheddar Cheese Block",      category="Dairy",     unit_price=6.99,  unit="piece"),
        Product(id=11, sku="DAI-003", name="Greek Yogurt 12-pack",      category="Dairy",     unit_price=15.00, unit="case"),
        # Bakery
        Product(id=12, sku="BAK-001", name="White Bread Loaf",          category="Bakery",    unit_price=3.49,  unit="piece"),
        Product(id=13, sku="BAK-002", name="Hamburger Buns 8-pack",     category="Bakery",    unit_price=4.99,  unit="piece"),
        Product(id=14, sku="BAK-003", name="Croissants 12-ct",          category="Bakery",    unit_price=12.00, unit="box"),
        # Cleaning
        Product(id=15, sku="CLN-001", name="All-Purpose Cleaner 6-pack",category="Cleaning",  unit_price=21.00, unit="case"),
        Product(id=16, sku="CLN-002", name="Paper Towels 12-roll",      category="Cleaning",  unit_price=18.50, unit="case"),
    ]
    session.add_all(products)
    session.commit()


@pytest.fixture(scope="session")
def product_dicts(db_session):
    """Return all products as plain dicts for use in cart_parser tests."""
    products = db_session.query(Product).all()
    return [
        {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "unit_price": p.unit_price,
            "unit": p.unit,
            "in_stock": p.in_stock,
        }
        for p in products
    ]
