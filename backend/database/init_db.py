from backend.database.database import Base, engine
from backend.utils.logger import logger

from backend.database.models import (
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