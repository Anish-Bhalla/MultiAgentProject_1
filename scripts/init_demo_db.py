from app.sql.demo_database import init_business_db
from app.database import init_state_db
from app.config import get_settings

if __name__ == "__main__":
    init_state_db()
    init_business_db()
    print(f"Initialized demo business DB at {get_settings().business_db}")
    print("Note: the demo sales data is synthetic, not real company data.")
