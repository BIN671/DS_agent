import wasmtime
import numpy as np


class DeepSeekPoWSolver:
    def __init__(self, wasm_path: str = "sha3_wasm_bg.7b9ca65ddd.wasm"):
        self.engine = wasmtime.Engine()
        with open(wasm_path, "rb") as f:
            wasm_bytes = f.read()

        module = wasmtime.Module(self.engine, wasm_bytes)
        self.store = wasmtime.Store(self.engine)
        linker = wasmtime.Linker(self.engine)
        linker.define_wasi()

        self.instance = linker.instantiate(self.store, module)
        self.memory = self.instance.exports(self.store)["memory"]

        self.exports = self.instance.exports(self.store)
        self.alloc = self.exports["__wbindgen_export_0"]
        self.add_to_stack = self.exports["__wbindgen_add_to_stack_pointer"]
        self.solve_func = self.exports["wasm_solve"]

    def _write_string(self, text: str) -> tuple[int, int]:
        encoded = text.encode('utf-8')
        length = len(encoded)
        ptr = self.alloc(self.store, length, 1)

        memory_view = self.memory.data_ptr(self.store)
        for i, byte in enumerate(encoded):
            memory_view[ptr + i] = byte
        return ptr, length

    def solve(self, challenge_data: dict) -> int:
        prefix = f"{challenge_data['salt']}_{challenge_data['expire_at']}_"

        challenge_ptr, challenge_len = self._write_string(challenge_data['challenge'])
        prefix_ptr, prefix_len = self._write_string(prefix)

        retptr = self.add_to_stack(self.store, -16)

        try:
            self.solve_func(
                self.store,
                retptr,
                challenge_ptr,
                challenge_len,
                prefix_ptr,
                prefix_len,
                float(challenge_data['difficulty'])
            )

            memory_view = self.memory.data_ptr(self.store)

            status = int.from_bytes(bytes(memory_view[retptr:retptr + 4]), byteorder='little', signed=True)

            # ИСПРАВЛЕНИЕ ЗДЕСЬ:
            # 0 означает, что решение НЕ найдено
            if status == 0:
                raise RuntimeError("WASM не смог найти решение")

            answer_bytes = bytes(memory_view[retptr + 8:retptr + 16])
            answer = int(np.frombuffer(answer_bytes, dtype=np.float64)[0])

            return answer

        finally:
            self.add_to_stack(self.store, 16)