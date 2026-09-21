import os
import pytest

# MUST be set before any application modules are imported!
os.environ["DATABASE_URL"] = "sqlite:///./test_plannededucation.db"

from src.plannededucation.api import database, models
from src.plannededucation.api.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Create the test tables in SQLite
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    yield
    # Cleanup after session
    models.Base.metadata.drop_all(bind=database.engine)
    if os.path.exists("./test_plannededucation.db"):
        try:
            os.remove("./test_plannededucation.db")
        except:
            pass
