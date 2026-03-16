import time
import logging
from fastapi import Request

logger = logging.getLogger("app.requests")

def log_requests(request: Request, call_next):
    start_time = time.time()

    response = call_next(request)

    duration = round((time.time() - start_time) * 1000, 2)

    logger.info(
        "%s %s - $s - #sms",
        request.client.host,
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )

    return response