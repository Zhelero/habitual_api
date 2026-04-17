import time
import logging
from fastapi import Request

logger = logging.getLogger("app.requests")


async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()

    client = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    user_agent = request.headers.get("User-Agent", "-")

    if request.url.query:
        path = f"{path}?{request.url.query}"

    message = "%s %s %s -> %s (%sms) [%s]"

    try:
        response = await call_next(request)
    except Exception:
        duration = round((time.perf_counter() - start_time) * 1000, 2)

        logger.exception(
            message,
            client,
            method,
            path,
            500,
            duration,
            user_agent,
        )
        raise

    duration = round((time.perf_counter() - start_time) * 1000, 2)
    status = response.status_code

    if status >= 500:
        logger.error(message, client, method, path, status, duration, user_agent)

    elif status >= 400:
        logger.warning(message, client, method, path, status, duration, user_agent)

    else:
        logger.info(message, client, method, path, status, duration, user_agent)

    return response
