import logging


def get_logger(name: str) -> logging.Logger:
    """
    Return a named stdlib logger.

    Flotilla packages emit logs but do not configure handlers, formatters, or
    levels. Applications remain responsible for process logging configuration.
    """
    return logging.getLogger(name)
