import asyncio
import json

from aiohttp import ClientSession

from .login import AuthSession


class APIError(Exception):
    def __init__(self, error):
        self.error = error
        self.code = error.get("error_code")
        self.message = error.get("error_msg")
        self.params = error.get("request_params")

    def __str__(self):
        return f"{self.code}: {self.message}"\
               f" | Request parameters: {self.params}"


class VKRequest(asyncio.Future):
    def __init__(self, method, params):
        super().__init__()
        self.method = method
        self.params = params


class API:
    def __init__(self, token='', exec=True, proxy=None, **kwargs):
        self.proxy = proxy
        self.token = token
        self.exec = exec

        self._session = ClientSession()

        self.default_params = kwargs
        self.default_params.update({"access_token": token})

        self.requests_queue = asyncio.Queue()
        if self.exec:
            asyncio.create_task(self._execute_loop())

    async def request(self, method, timeout=None, params=None, **kwargs):
        params = {}
        params.update(self.default_params)
        params.update(kwargs)
        params.pop("access_token")
        if self.exec:
            request = VKRequest(method, params)
            await self.requests_queue.put(request)
            await asyncio.wait_for(request, timeout=timeout)
            return request.result()
        else:
            result = await self.raw_request(method, params)
            return result["response"]

    async def raw_request(self, method, params={}, **kwargs):
        params.update(self.default_params)
        params.update(kwargs)
        # VKAndroidApp/5.52-4543 (Android 5.1.1; SDK 22; x86_64; unknown Android SDK built for x86_64; en; 320x240)
        async with self._session.post(
             f'https://api.vk.com/method/{method}',
             data=params, headers={
                "user-agent": "KateMobileAndroid/56 lite-460 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)",
                "X-VK-Android-Clent": "new",
                "X-Get-Processing-Time": "1"
             }) as response:
            response = await response.json()
        if response.get("error"):
            raise APIError(response.get("error"))
        return response

    async def close(self):
        await self._session.close()

    async def _execute_loop(self):
        while True:
            await asyncio.sleep(1/2)

            code = ''
            reqs = list()
            requests = list()

            for _ in range(25):
                r = await self.requests_queue.get()
                params = json.dumps(r.params, ensure_ascii=False)
                line = f"API.{r.method}({params})"
                reqs.append(line)
                new_code = f"return [{','.join(reqs)}];"
                if len(new_code) > 9995:
                    break
                requests.append(r)
                code = new_code
                if self.requests_queue.empty():
                    break

            if not code:
                continue

            asyncio.create_task(
                self._execute(code, requests),
            )

    async def _execute(self, code, requests):
        response = await self.raw_request("execute", code=code)
        result = response.get("response") or []
        errors = response.get("execute_errors") or []
        if len(result) != len(requests):
            result = [*result, *[False] * (len(requests) - len(result))]

        if len(errors) != len(requests):
            errors = [*errors, *[None] * (len(requests) - len(errors))]

        for res, req, err in zip(result, requests, errors):
            if req.done():
                continue

            if res is False or res is None:
                req.set_exception(APIError(
                    err
                ))
            else:
                req.set_result(res)
