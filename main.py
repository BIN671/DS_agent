import httpx
import json
import base64
import traceback


import POW
import support



# Ваши данные из браузера


class DeepSeek_API:
    def __init__(self, user_token: str, session_cookie: str) -> None:

        self.memory = {}
        self.ans = None
        self.executors_table = support.executors_table



        self.solver = POW.DeepSeekPoWSolver()
        self.model = "default"
        self.session_id = None
        self.pre_message_id = None
        self.user_token = user_token
        self.session_cookie = session_cookie
        self.base_url = "https://chat.deepseek.com"
        self.headers = {
            "Authorization": f"Bearer {self.user_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0",
            "Cookie": f"ds_session_id={self.session_cookie}",
            "Origin": "https://chat.deepseek.com",
            "Referer": "https://chat.deepseek.com/",
            "Accept": "*/*",
            # Заголовки клиента
            "x-client-version": "2.5.0",
            "x-client-platform": "web",
            "x-client-bundle-id": "com.deepseek.chat",
            "x-client-locale": "ru",
            # Заголовки безопасности
            "sec-ch-ua": '"Microsoft Edge";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin"
        }


        self.client = httpx.Client(http2=True, headers=self.headers)

    def creat_session(self):
        respon = self.client.post(
            f"{self.base_url}/api/v0/chat_session/create",
            json={}
        )

        if respon.status_code == 200:
            print(respon.status_code)
            data = respon.json()
            self.session_id = data.get("data", {}).get("biz_data", {}).get("chat_session", {}).get("id")

    def get_pow_challenge(self):
        target_path: str = "/api/v0/chat/completion"
        respon = self.client.post(
            f"{self.base_url}/api/v0/chat/create_pow_challenge",
            json={"target_path": target_path}
        )

        if respon.status_code == 200:
            data = respon.json()
            challenge_data = data.get("data", {}).get("biz_data", {}).get("challenge")

            answer = self.solver.solve(challenge_data)
            payload = {
                "algorithm": challenge_data["algorithm"],
                "challenge": challenge_data["challenge"],
                "salt": challenge_data["salt"],
                "answer": answer,
                "signature": challenge_data["signature"],
                "target_path": challenge_data["target_path"]
            }

            raw_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            return base64.b64encode(raw_json).decode('utf-8')

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
            "model_type": self.model
        }
        self.model = None
        full_response = ""

        with self.client.stream(
                "POST",
                f"{self.base_url}/api/v0/chat/completion",
                headers=extra_header,
                json=payload
        ) as response:
            if response.status_code != 200:
                print(f"❌ Ошибка HTTP: {response.status_code}")
                print(response.read().decode('utf-8'))
                return ""

            self.ans, self.pre_message_id = support.parse_sse_response(response)

            return self.ans


    def execute(self):
        answer_data = support.extract(self.ans)
        text = answer_data.get("text")
        tools = answer_data.get("tools")
        status = answer_data.get("status")
        return_data = ""
        indx = None
        try:
            for indx, tool in enumerate(tools):
                name = tool.get("name")
                func = self.executors_table.get(name)
                args_data = tool.get("args")
                mem = func(**args_data)
                self.memory[tool.get("save_as")] = mem


        except Exception:
            return_data = f'ошибка в команде {indx}: {traceback.format_exc()}'
            status = "continue"

            return status, return_data


        try:
            return_keys = answer_data.get("return")
            for key in return_keys:
                return_data += self.memory[key]
        except Exception:
            return_data = f'ошибка в памяти по ключу {key}: {traceback.format_exc()}'
            status = "continue"

        return status, return_data




# if __name__ == "__main__":
#     challenge = DeepSeek_API()
#     challenge.creat_session()
#     print(challenge.send_message("топ LLM"))
#     print(challenge.send_message("опиши критерии оценки"))



"""


"""