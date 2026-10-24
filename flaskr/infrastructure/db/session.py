from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def crear_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
