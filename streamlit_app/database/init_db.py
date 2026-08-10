from database.database import Base, engine
from utils.logger import logger

from database.models import (
    User,
    AudioFile,
    Annotation,
    AnnotationVersion,
    ReviewComment,
    ReviewerApproval,
    AuditLog,
)

def initialize_database():
    Base.metadata.create_all(bind=engine)
    logger.info("Database created successfully!")


if __name__ == "__main__":
    initialize_database()