import logging
import logging.handlers
import os


def setup_logging():
    """Setup optimized logging configuration for Docker"""

    # Simpler formatter for better performance
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # Changed to INFO level

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # API logger
    api_logger = logging.getLogger("api")
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = True

    # App logger (used in api/main.py)
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = True

    # Consumer logger
    consumer_logger = logging.getLogger("consumer")
    consumer_logger.setLevel(logging.WARNING)
    consumer_logger.propagate = True

    # Disable some noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("db.database").setLevel(logging.WARNING)

    # Enable INFO level for development
    if os.getenv("DEBUG", "false").lower() == "true":
        root_logger.setLevel(logging.INFO)
        console_handler.setLevel(logging.INFO)
        api_logger.setLevel(logging.INFO)

    logging.warning("Optimized logging setup completed")
