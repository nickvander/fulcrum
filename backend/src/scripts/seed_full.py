import logging
from datetime import datetime, timedelta

from src.database import SessionLocal
from src.core.security import get_password_hash
from src.models.user import User
from src.models.supplier import Supplier
from src.models.product import Product
from src.models.purchase_order import PurchaseOrder, PurchaseOrderStatus, PaymentStatus
from src.models.expense import Expense
from src.models.marketing import (
    Campaign, CampaignStatus, CampaignEvent, MarketingConnector,
    MarketingChannelType, ConnectorType
)
from src.scripts.seed_products_images import seed_products_with_images

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_full():
    db = SessionLocal()
    try:
        logger.info("Starting comprehensive seeding...")

        # 1. Seed Products (using existing logic)
        # Note: seed_products_with_images handles its own logging
        logger.info("--- Seeding Products ---")
        seed_products_with_images()
        
        # 2. Seed Users
        logger.info("--- Seeding Users ---")
        admin_email = "admin@example.com"
        admin_password = "SecurePass123!"
        
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            logger.info(f"Creating superuser: {admin_email}")
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                first_name="Admin",
                last_name="User",
                user_type="admin",
                is_active=True,
                is_superuser=True,
                role="admin",
                employee_id="ADM000001"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        else:
            logger.info(f"Superuser {admin_email} already exists.")
            admin_user = existing_admin

        # 2b. Seed Extra Users
        extra_users = [
            {"email": "manager@example.com", "role": "manager", "first_name": "Store", "last_name": "Manager", "emp_id": "EMP000002"},
            {"email": "staff@example.com", "role": "staff", "first_name": "Support", "last_name": "Staff", "emp_id": "EMP000003"},
        ]
        
        for u_data in extra_users:
            existing_u = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing_u:
                new_u = User(
                    email=u_data["email"],
                    hashed_password=get_password_hash("SecurePass123!"),
                    first_name=u_data["first_name"],
                    last_name=u_data["last_name"],
                    user_type=u_data["role"],
                    is_active=True,
                    is_superuser=False,
                    role=u_data["role"],
                    employee_id=u_data["emp_id"]
                )
                db.add(new_u)
                logger.info(f"Created user: {u_data['email']}")
            else:
                logger.info(f"User {u_data['email']} already exists.")
        db.commit()

        # 3. Seed Suppliers
        logger.info("--- Seeding Suppliers ---")
        suppliers_data = [
            {
                "name": "Global Electronics Ltd",
                "contact_person": "John Smith",
                "email": "contact@globalelectronics.com",
                "phone": "+1-555-0101",
                "currency": "USD",
                "payment_terms": "Net 30"
            },
            {
                "name": "Fashion Forward Inc",
                "contact_person": "Sarah Johnson",
                "email": "sales@fashionforward.com",
                "phone": "+1-555-0102",
                "currency": "USD",
                "payment_terms": "Net 60"
            },
            {
                "name": "Home Essentials Co",
                "contact_person": "Mike Brown",
                "email": "support@homeessentials.com",
                "phone": "+1-555-0103",
                "currency": "USD",
                "payment_terms": "Due on Receipt"
            }
        ]
        
        created_suppliers = []
        for s_data in suppliers_data:
            supplier = db.query(Supplier).filter(Supplier.email == s_data["email"]).first()
            if not supplier:
                supplier = Supplier(**s_data)
                db.add(supplier)
                db.flush()
                logger.info(f"Created Supplier: {supplier.name}")
            else:
                logger.info(f"Supplier {supplier.name} already exists.")
            created_suppliers.append(supplier)
        db.commit()

        # 4. Seed Purchase Orders
        logger.info("--- Seeding Purchase Orders ---")
        if created_suppliers:
            # Create a completed PO
            po1 = PurchaseOrder(
                supplier_id=created_suppliers[0].id,
                status=PurchaseOrderStatus.COMPLETED.value,
                total_amount=5000.00,
                currency="USD",
                payment_status=PaymentStatus.PAID.value,
                ordered_at=datetime.utcnow() - timedelta(days=10),
                received_at=datetime.utcnow() - timedelta(days=2),
                paid_by_user_id=admin_user.id
            )
            db.add(po1)
            
            # Create a draft PO
            po2 = PurchaseOrder(
                supplier_id=created_suppliers[1].id,
                status=PurchaseOrderStatus.DRAFT.value,
                total_amount=1200.50,
                currency="USD",
                payment_status=PaymentStatus.UNPAID.value
            )
            db.add(po2)
            
            db.commit()
            logger.info("Created sample Purchase Orders.")

        # 5. Seed Expenses
        logger.info("--- Seeding Expenses ---")
        expenses_data = [
            {
                "description": "Office Supplies",
                "amount": 150.25,
                "category": "Office",
                "date": datetime.utcnow().date(),
                "paid_by_user_id": admin_user.id,
                "expense_type": "one_time"
            },
            {
                "description": "Monthly Software Subscription",
                "amount": 49.99,
                "category": "Software",
                "date": datetime.utcnow().date(),
                "paid_by_user_id": admin_user.id,
                "expense_type": "recurring",
                "recurrence_interval": "monthly"
            }
        ]
        
        for e_data in expenses_data:
            expense = Expense(**e_data)
            db.add(expense)
        
        db.commit()
        logger.info("Created sample Expenses.")

        # 6. Seed Marketing Data
        logger.info("--- Seeding Marketing Data ---")
        
        # Connectors
        connectors_data = [
            {
                "name": "Official Instagram",
                "connector_type": ConnectorType.INSTAGRAM.value,
                "channel_type": MarketingChannelType.SOCIAL.value,
                "user_id": admin_user.id,
                "is_active": True
            },
            {
                "name": "Newsletter Service",
                "connector_type": ConnectorType.SENDGRID.value,
                "channel_type": MarketingChannelType.EMAIL.value,
                "user_id": admin_user.id,
                "is_active": True
            }
        ]
        
        created_connectors = []
        for c_data in connectors_data:
            connector = db.query(MarketingConnector).filter(MarketingConnector.name == c_data["name"]).first()
            if not connector:
                connector = MarketingConnector(**c_data)
                db.add(connector)
                db.flush() # get ID
                logger.info(f"Created Connector: {connector.name}")
            created_connectors.append(connector)
            
        # Campaign
        demo_campaign = db.query(Campaign).filter(Campaign.name == "Summer Sale 2025").first()
        if not demo_campaign:
            demo_campaign = Campaign(
                name="Summer Sale 2025",
                description="Huge discounts on electronics and outdoor gear.",
                status=CampaignStatus.SCHEDULED.value,
                start_date=datetime.utcnow().date() + timedelta(days=5),
                end_date=datetime.utcnow().date() + timedelta(days=20),
                budget=5000.0,
                user_id=admin_user.id,
                is_smart_boost=True,
                boost_reason="Seasonal trend analysis indicates high demand."
            )
            db.add(demo_campaign)
            db.flush()
            logger.info(f"Created Campaign: {demo_campaign.name}")
            
            # Events
            if len(created_connectors) >= 2:
                events = [
                    CampaignEvent(
                        campaign_id=demo_campaign.id,
                        connector_id=created_connectors[0].id, # Insta
                        name="Teaser Post",
                        channel_type=MarketingChannelType.SOCIAL.value,
                        content_body="Get ready! Something big is coming... ☀️ #SummerSale",
                        scheduled_at=datetime.utcnow() + timedelta(days=1),
                        status="scheduled"
                    ),
                    CampaignEvent(
                        campaign_id=demo_campaign.id,
                        connector_id=created_connectors[1].id, # Email
                        name="Launch Blast",
                        channel_type=MarketingChannelType.EMAIL.value,
                        content_subject="Summer Sale Starts Now!",
                        content_body="Don't miss out on up to 50% off.",
                        scheduled_at=datetime.utcnow() + timedelta(days=5),
                        status="scheduled"
                    )
                ]
                db.add_all(events)
                logger.info("Created sample Campaign Events.")
        else:
            logger.info("Campaign 'Summer Sale 2025' already exists.")

        # Quick Posts (Independent Events)
        logger.info("--- Seeding Quick Posts ---")
        quick_post_check = db.query(CampaignEvent).filter(CampaignEvent.campaign_id.is_(None)).first()
        if not quick_post_check and created_connectors:
            quick_posts = [
                CampaignEvent(
                    campaign_id=None, # Independent
                    connector_id=created_connectors[0].id, # Insta
                    name="Flash Sale Alert",
                    channel_type=MarketingChannelType.SOCIAL.value,
                    content_body="Flash Sale happening now! ⚡ Link in bio.",
                    status="published",
                    published_at=datetime.utcnow(),
                    external_url="https://instagram.com/p/123456789"
                ),
                CampaignEvent(
                    campaign_id=None,
                    connector_id=created_connectors[0].id, 
                    name="New Arrival Teaser",
                    channel_type=MarketingChannelType.SOCIAL.value,
                    content_body="Guess what just arrived? 👀",
                    status="draft",
                    scheduled_at=datetime.utcnow() + timedelta(hours=2)
                )
            ]
            
            # Link a product to the first quick post if available
            products = db.query(Product).limit(1).all()
            if products:
                quick_posts[0].products.append(products[0])
                
            db.add_all(quick_posts)
            logger.info("Created sample Quick Posts.")
        else:
            logger.info("Quick posts already exist or no connectors available.")

        db.commit()

        logger.info("Comprehensive seeding completed successfully.")

    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_full()
