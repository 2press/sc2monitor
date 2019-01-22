"""Log to database via SQLAlchemy."""
import logging
import traceback

from sc2monitor.model import Log


class SQLAlchemyHandler(logging.Handler):
    """Handler for logging via SQLAlchemy to the database."""

    def __init__(self, db_session):
        """Init logger and set database session."""
        super().__init__()
        self.db_session = db_session
        self.errors = 0
        self.warnings = 0

    def emit(self, record):
        """Write a record to the database."""
        trace = None
        exc = record.__dict__['exc_info']
        level = record.__dict__['levelname']

        if level in ['ERROR', 'CRITICAL']:
            self.errors += 1
        elif level == 'WARNING':
            self.warnings += 1

        if exc:
            trace = traceback.format_exc()
        log = Log(
            logger=record.__dict__['name'],
            level=level,
            trace=trace,
            msg=record.__dict__['msg'],)
        self.db_session.add(log)
        self.db_session.commit()
