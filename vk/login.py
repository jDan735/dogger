import aiohttp
import json
import re

from json import JSONDecodeError

from urllib.parse import urlparse, parse_qs, urlencode

action_regex = re.compile(r"<form(?= ).* action=\"(.+)\"")


def get_qs_field(url, field="access_token"):
    parsed_url = urlparse(url)
    query_string = parsed_url.query

    if not query_string:
        query_string = parsed_url.fragment

    query = parse_qs(query_string)
    if not query.get(field):
        return

    return query.get(field)[0]


class AuthSession(aiohttp.ClientSession):
    LOGIN_URL = "https://m.vk.com"
    OAUTH_URL = "https://oauth.vk.com/authorize"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def login(self, login, password):
        params = {
            'email': login,
            'pass': password}

        async with self.get(self.LOGIN_URL) as r:
            html = await r.text()
        action = action_regex.findall(html)

        if not action:
            raise RuntimeError("Action wasn't found")

        action = action[0]

        async with self.post(action,
                             params=urlencode(params)) as r:
            with open("huy.html", "w") as f:
                f.write(await r.text())
            return "service_msg service_msg_warning" not in await r.text()

    async def oauth(self, client_id, scope):
        data = {
            "client_id": client_id,
            "scope": scope,
            "display": "page",
            "response_type": "token",
            "revoke": 0,
            "client_secret": "VeWdmVclDCtn6ihuP1nt",
            "redirect_uri": "http://api.vk.com/blank.html"
        }

        async with self.post(self.OAUTH_URL, params=data) as r:
            response = await r.text()
            url = r.history[2].real_url

        access_token = get_qs_field(url.human_repr())
        if access_token:
            return access_token

        action = action_regex.findall(response)
        if not action:
            try:
                error = json.loads(response)
            except JSONDecodeError:
                ...
            else:
                description = error.get("error_description")
                raise RuntimeError("VK Error: " + description)

            raise RuntimeError("Action wasn't found")
        else:
            action = action[0]

            async with self.get(action) as r:
                url = r.real_url

        access_token = get_qs_field(url.human_repr())
        return access_token

    @classmethod
    async def get_access_token(cls, login, password, client_id, scope):
        client = cls()
        ok = await client.login(login, password)
        if not ok:
            await client.close()
            print("не смог залогиниться..")
            return

        token = await client.oauth(client_id, scope)
        await client.close()
        return token
