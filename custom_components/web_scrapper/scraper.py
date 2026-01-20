import re

from bs4 import BeautifulSoup
from lxml import html

from homeassistant.helpers.aiohttp_client import async_get_clientsession


class WebScraperRequestError(Exception):
    pass


async def async_fetch_and_extract(
    hass,
    url,
    selector,
    selector_type,
    regex=None,
    request_method="GET",
    timeout=15,
):
    session = async_get_clientsession(hass)
    try:
        async with session.request(request_method, url, timeout=timeout) as resp:
            if resp.status != 200:
                raise WebScraperRequestError(f"HTTP {resp.status}")
            content = await resp.text()
    except Exception as err:
        raise WebScraperRequestError(str(err)) from err

    if selector_type == "css":
        soup = BeautifulSoup(content, "html.parser")
        elements = soup.select(selector)
        text = "\n".join(e.get_text(" ", strip=True) for e in elements)
    else:
        doc = html.fromstring(content)
        nodes = doc.xpath(selector)
        text = "\n".join(
            n if isinstance(n, str) else " ".join(n.itertext()) for n in nodes
        )

    if regex:
        text = re.findall(regex, text)

    return text
