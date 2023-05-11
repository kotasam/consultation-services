import httpx
import structlog
from structlog import get_logger
import logging
import asyncio
from worke_consultation_service.config import config as cfg

log = get_logger("Structured Logger")


NEW_RELIC_API_KEY = cfg.get("new_relic", "NEW_RELIC_API_KEY")
NEW_RELIC_URL = cfg.get("new_relic", "NEW_RELIC_URL")


async def postLog(URL, API_KEY, data):
    async with httpx.AsyncClient() as client:
        r = await client.post(URL=URL, API_KEY=API_KEY, json=data)


class NewRelicMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        structlog.configure(
            processors=[sendToNewRelic, structlog.processors.JSONRenderer()],
        )
        response = self.get_response(request)
        log.info(
            "[Request]: Path:"
            + str(request.path)
            + "Body: "
            + (str(request.body) if request.body else "")
            + "[Response]: \n Body: "
            + str(response.content)
        )
        return response


async def postLog(URL, API_KEY, data):
    async with httpx.AsyncClient() as client:
        r = await client.post(URL, json=data, headers={"Api-Key": NEW_RELIC_API_KEY})


def sendToNewRelic(logger, log_method, event_dict):
    try:
        payload = {
            "message": f"{log_method} - {event_dict['event']}",
            # "attributes": event_dict,
        }
        asyncio.run(postLog(URL=NEW_RELIC_URL, API_KEY=NEW_RELIC_API_KEY, data=payload))

        return event_dict
    except Exception as err:
        print(err)
        logging.error(f"sendToNewRelic: {err}", exc_info=True)
        pass


structlog.configure(
    processors=[sendToNewRelic, structlog.processors.JSONRenderer()],
)
