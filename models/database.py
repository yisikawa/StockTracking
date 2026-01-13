from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from config import DB_NAME

engine = create_engine(f'sqlite:///{DB_NAME}')
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # Import all models here so that they are registered properly on the metadata
    import models.stock
    Base.metadata.create_all(bind=engine)
