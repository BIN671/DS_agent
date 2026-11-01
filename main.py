import httpx
import json
import base64
import traceback

import executors
import POW
import support


# Значения по умолчанию; могут быть переопределены извне (settings.json)
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_MAX_STEPS = 30


class DeepSeek_API:
    def __init__(self, user_token: str, session_cookie: str) -> None:
        self.memory = {}
        self.ans = None
        self.executors_table = executors.executors_table

        self.solver = POW.DeepSeekPoWSolver()
        self.model = "default"
        self.session_id = None
        self.pre_message_id = None
        self.user_token = user_token
        self.session_cookie = session_cookie
        self.base_url = "https://chat.deepseek.com"

        self.api_timeout = DEFAULT_TIMEOUT_S
        self.max_steps = DEFAULT_MAX_STEPS
        self._step_count = 0

        self.headers = {
            "Authorization": f"Bearer {self.user_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0",
            "Cookie": f"ds_session_id={self.session_cookie}",
            "Origin": "https://chat.deepseek.com",
            "Referer": "https://chat.deepseek.com/",
            "Accept": "*/*",
            "x-client-version": "2.5.0",
            "x-client-platform": "web",
            "x-client-bundle-id": "com.deepseek.chat",
            "x-client-locale": "ru",
            "sec-ch-ua": '"Microsoft Edge";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }

        self.client = httpx.Client(
            http2=True,
            headers=self.headers,
            timeout=self.api_timeout,
        )

    # ---- настройки ----
    def apply_settings(self, settings: dict) -> None:
        """Применяет словарь настроек (api_timeout, max_steps)."""
        if not settings:
            return
        try:
            self.api_timeout = float(settings.get("api_timeout", self.api_timeout))
        except (TypeError, ValueError):
            pass
        try:
            self.max_steps = int(settings.get("max_steps", self.max_steps))
        except (TypeError, ValueError):
            pass
        self.client.timeout = httpx.Timeout(self.api_timeout)

    # ---- сессия ----
    def create_session(self):
        response = self.client.post(
            f"{self.base_url}/api/v0/chat_session/create",
            json={},
        )
        if response.status_code == 200:
            data = response.json()
            self.session_id = (
                data.get("data", {})
                .get("biz_data", {})
                .get("chat_session", {})
                .get("id")
            )
            return self.session_id

        raise RuntimeError(
            f"Не удалось создать сессию: HTTP {response.status_code} "
            f"{response.text[:300]}"
        )

    # обратная совместимость с прежним именем
    def creat_session(self):
        return self.create_session()

    # ---- PoW ----
    def get_pow_challenge(self):
        target_path: str = "/api/v0/chat/completion"
        response = self.client.post(
            f"{self.base_url}/api/v0/chat/create_pow_challenge",
            json={"target_path": target_path},
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"PoW challenge failed: HTTP {response.status_code} "
                f"{response.text[:300]}"
            )

        data = response.json()
        challenge_data = data.get("data", {}).get("biz_data", {}).get("challenge")
        if not challenge_data:
            raise RuntimeError("PoW challenge пуст в ответе API")

        answer = self.solver.solve(challenge_data)
        payload = {
            "algorithm": challenge_data["algorithm"],
            "challenge": challenge_data["challenge"],
            "salt": challenge_data["salt"],
            "answer": answer,
            "signature": challenge_data["signature"],
            "target_path": challenge_data["target_path"],
        }
        raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.b64encode(raw_json).decode("utf-8")

    # ---- отправка сообщения ----
    def send_message(self, prompt):
        pow_header = self.get_pow_challenge()
        extra_header = {"x-ds-pow-response": pow_header}

        payload = {
            "chat_session_id": self.session_id,
            "parent_message_id": self.pre_message_id,
            "prompt": prompt,
            "ref_file_ids": [],
            "thinking_enabled": False,
            "search_enabled": True,
            "action": None,
            "preempt": False,
            "model_type": self.model,
        }
        # после первого запроса модель фиксируется как строка, а не None
        self.model = self.model or "default"

        with self.client.stream(
            "POST",
            f"{self.base_url}/api/v0/chat/completion",
            headers=extra_header,
            json=payload,
        ) as response:
            if response.status_code != 200:
                body = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {response.status_code}: {body[:500]}")

            self.ans, self.pre_message_id = support.parse_sse_response(response)
            return self.ans

    # ---- исполнение инструментов ----
    def execute(self):
        if self.ans is None:
            return "error", "Нет ответа модели для разбора"

        try:
            answer_data = support.extract(self.ans)
        except Exception:
            return (
                "continue",
                "не удалось разобрать ответ модели как JSON: "
                + traceback.format_exc(),
            )

        if not isinstance(answer_data, dict):
            return "error", "Ответ модели не является JSON-объектом"

        status = answer_data.get("status")
        tools = answer_data.get("tools") or []
        return_keys = answer_data.get("return") or []

        self._step_count += 1
        if self.max_steps and self._step_count > self.max_steps:
            self._step_count = 0
            return "error", f"Превышен лимит шагов ({self.max_steps})"

        return_data = ""

        # --- инструменты ---
        indx = None
        try:
            for indx, tool in enumerate(tools):
                name = tool.get("name")
                func_factory = self.executors_table.get(name)
                if func_factory is None:
                    raise KeyError(f"Неизвестный инструмент: {name!r}")

                args_data = tool.get("args") or {}
                cwd = tool.get("cwd")
                result = func_factory(cwd)(**args_data)

                save_as = tool.get("save_as")
                if save_as:
                    self.memory[save_as] = result
        except Exception:
            return (
                "continue",
                f"ошибка в команде {indx}: " + traceback.format_exc(),
            )

        # --- память ---
        missing = [k for k in return_keys if k not in self.memory]
        if missing:
            return (
                "continue",
                f"ошибка в памяти: ключи не найдены {missing}",
            )
        for key in return_keys:
            return_data += self.memory[key]

        if status == "done":
            self._step_count = 0

        return status, return_data
