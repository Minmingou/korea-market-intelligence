import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (Base.metadata에 테이블을 등록하기 위해 import)
from app.config import settings
from app.database import Base, get_db
from app.main import app as fastapi_app

# 테스트는 개발자의 로컬 .env 설정(예: STEP 4 KIS 연동 확인을 위한
# USE_MOCK_DATA=false)과 무관하게 항상 Mock 데이터로 실행되어야 한다.
# 그렇지 않으면 테스트가 실제 외부 API를 호출해 느려지거나 실패할 수 있다.
settings.use_mock_data = True
settings.use_mock_dart = True
settings.use_mock_news = True
settings.use_mock_llm = True

test_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
Base.metadata.create_all(bind=test_engine)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client():
    with TestClient(fastapi_app) as test_client:
        yield test_client
