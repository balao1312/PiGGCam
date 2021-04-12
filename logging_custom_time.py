from datetime import datetime
import logging

class TimestampFilter(logging.Filter):
    """
    This is a logging filter which will check for a `timestamp` attribute on a
    given LogRecord, and if present it will override the LogRecord creation time
    to be that of the timestamp (specified as a time.time()-style value).
    This allows one to override the date/time output for log entries by specifying
    `timestamp` in the `extra` option to the logging call.
    """

    def filter(self, record):
        if hasattr(record, 'timestamp'):
            record.created = record.timestamp
        return True
    
def logger():
    format = '[%(asctime)s] %(levelname)s: %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(level=logging.INFO, format=format, datefmt=datefmt,
        # filename=f'./logs/{datetime.now().strftime("%Y-%m-%d")}.log', filemode='a')
        handlers=[logging.FileHandler(f'./logs/{datetime.now().strftime("%Y-%m-%d")}.log'), logging.StreamHandler()])
        
    logger = logging.getLogger(__name__)
    filter = TimestampFilter()
    logger.addFilter(filter)
    return logger                                                                           