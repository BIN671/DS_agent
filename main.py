import httpx
import json
import base64
import traceback

import os
import time
import mimetypes
import uuid

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
    def get_pow_challenge(self, target_path: str = "/api/v0/chat/completion"):
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

    def upload_image(self, image_path: str) -> str:
        """Загружает картинку и возвращает file_id, готовый для прикрепления к сообщению."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл не найден: {image_path}")

        # 1. Получаем PoW
        pow_header = self.get_pow_challenge("/api/v0/file/upload_file")

        # 2. Читаем файл
        with open(image_path, "rb") as f:
            file_content = f.read()
        file_size = len(file_content)
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Делаем имя файла безопасным (убираем кириллицу, если она ломает парсер)
        import urllib.parse
        filename = urllib.parse.quote(os.path.basename(image_path))

        import uuid
        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex

        # 3. Вручную формируем тело запроса
        body = b""
        # СНАЧАЛА ФАЙЛ
        body += f"--{boundary}\r\n".encode("utf-8")
        body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8")
        body += f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8")
        body += file_content
        body += b"\r\n"

        # ПОТОМ PURPOSE
        body += f"--{boundary}\r\n".encode("utf-8")
        body += b'Content-Disposition: form-data; name="purpose"\r\n\r\n'
        body += b"user_data\r\n"

        # КОНЕЦ
        body += f"--{boundary}--\r\n".encode("utf-8")

        # 4. Заголовки
        upload_headers = {
            "Authorization": f"Bearer {self.user_token}",
            "Cookie": f"ds_session_id={self.session_cookie}",
            "User-Agent": self.headers["User-Agent"],
            "x-ds-pow-response": pow_header,
            "x-file-size": str(file_size),
            "x-model-type": "vision",
            "x-thinking-enabled": "false",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }

        # 5. Отправляем через ЧИСТЫЙ клиент, чтобы self.headers не мешали
        with httpx.Client(http2=True) as clean_client:
            upload_resp = clean_client.post(
                f"{self.base_url}/api/v0/file/upload_file",
                content=body,
                headers=upload_headers
            )

        print(f"DEBUG [upload_file] Status: {upload_resp.status_code}")
        print(f"DEBUG [upload_file] Response: {upload_resp.text}")

        upload_data = upload_resp.json()
        data_dict = upload_data.get("data")
        if data_dict is None:
            raise Exception(f"Сервер вернул null в 'data'. Ответ: {upload_data}")

        file_id = data_dict.get("biz_data", {}).get("id")
        if not file_id:
            raise Exception(f"Не удалось найти file_id. Ответ: {upload_data}")

        # --- ФОРК ФАЙЛА (С ИСПРАВЛЕНИЕМ) ---
        vision_file_id = file_id  # По умолчанию используем оригинальный ID

        fork_resp = self.client.post(
            f"{self.base_url}/api/v0/file/fork_file_task",
            json={"file_id": file_id, "to_model_type": "vision"}
        )

        print(f"DEBUG [fork_file_task] Status: {fork_resp.status_code}")
        print(f"DEBUG [fork_file_task] Response: {fork_resp.text}")

        if fork_resp.status_code == 200:
            fork_data = fork_resp.json()
            fork_biz_data = fork_data.get("data", {}).get("biz_data")

            # Если форк прошел успешно и вернул новый ID, берем его
            if fork_biz_data and fork_biz_data.get("id"):
                vision_file_id = fork_biz_data.get("id")
            else:
                # Если biz_msg == "model kind satisfied", оставляем оригинальный file_id
                print("DEBUG: Форк не требуется, используем оригинальный file_id.")

        # --- ОЖИДАНИЕ ПАРСИНГА (POLLING) ---
        max_attempts = 15
        for attempt in range(max_attempts):
            fetch_resp = self.client.get(
                f"{self.base_url}/api/v0/file/fetch_files",
                params={"file_ids": str(vision_file_id)}  # Убедимся, что это строка
            )

            if fetch_resp.status_code == 200:
                fetch_data = fetch_resp.json()
                # Достаем список файлов (он может быть в разных местах в зависимости от версии API)
                biz_data = fetch_data.get("data", {}).get("biz_data", {})
                files_list = biz_data.get("files", [])

                # Если вдруг сервер вернул не список, а один объект
                if not files_list and biz_data.get("id") == vision_file_id:
                    files_list = [biz_data]

                for f_info in files_list:
                    if f_info.get("id") == vision_file_id:
                        status = f_info.get("status")
                        print(f"DEBUG: Статус файла {vision_file_id}: {status}")

                        if status == "SUCCESS":
                            return vision_file_id
                        elif status in ["FAILED", "CONTENT_EMPTY"]:
                            raise Exception(f"Ошибка парсинга картинки: {status}")

            time.sleep(1)

        raise TimeoutError("Сервер слишком долго обрабатывает картинку.")

    # ---- отправка сообщения ----
    def send_message(self, prompt, file_ids: list[str] = None, master=True, _retries=3):
        print(self.pre_message_id)

        if file_ids:
            current_model = "vision"
        else:
            current_model = self.model or "default"

        pow_header = self.get_pow_challenge("/api/v0/chat/completion")
        extra_header = {"x-ds-pow-response": pow_header}

        payload = {
            "chat_session_id": self.session_id,
            "parent_message_id": self.pre_message_id,
            "prompt": prompt,
            "ref_file_ids": file_ids if file_ids else [],
            "thinking_enabled": False,
            "search_enabled": True,
            "action": None,
            "preempt": False,
            "model_type": self.model,
            "shumei_device_id": "BXtqxQpYwbwmQJ4XNTSkZ1zdx6VKEjfM3oYUI0ZuReztNUfZHQEtelinyc05c+lkbCRSiuuZnihhE6swCriHP1Q=",
        }

        with self.client.stream(
                "POST",
                f"{self.base_url}/api/v0/chat/completion",
                headers=extra_header,
                json=payload,
        ) as response:
            if response.status_code != 200:
                body = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {response.status_code}: {body[:500]}")

            print("=" * 60)
            print(f"STATUS: {response.status_code}")
            print(f"URL: {response.url}")
            print("HEADERS:")
            for k, v in response.headers.items():
                print(f"  {k}: {v}")
            print("=" * 60)

            # Парсим ОДИН раз
            ans, new_id = support.parse_sse_response(response)

            print(f"PARSED ANSWER: {ans!r}")
            print(f"NEW pre_message_id: {new_id}")
            print("=" * 60)

        if new_id is not None and ans:
            # Успех: обновляем состояние и возвращаем
            self.ans = ans
            self.pre_message_id = new_id
            return self.ans

        # Пустой поток — известный сбой DeepSeek
        if master and _retries > 0:
            import time
            time.sleep(10)
            return self.send_message(prompt, master=True, _retries=_retries - 1)

        return None  # или raise RuntimeError("EMPTY_STREAM")


    # ---- исполнение инструментов ----
    def execute(self):
        if self.ans is None:
            print("ответ не получен")
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
