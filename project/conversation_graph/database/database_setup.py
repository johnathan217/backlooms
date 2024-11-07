from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from project.database.database import Base


def setup_database(host="localhost", user="root", password="", database="conversation_graph"):
    try:
        engine = create_engine(
            f"mysql+mysqlconnector://{user}:{password}@{host}"
        )

        with engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {database}"))
            conn.commit()

        engine = create_engine(
            f"mysql+mysqlconnector://{user}:{password}@{host}/{database}"
        )

        Base.metadata.create_all(engine)

        print("Database and tables created successfully!")
        return True

    except SQLAlchemyError as err:
        print(f"Database setup error: {err}")
        return False