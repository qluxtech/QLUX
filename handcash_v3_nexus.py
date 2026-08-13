# handcash_v3_nexus.py
import os
import subprocess
import time
import ast
import asyncio
import concurrent.futures
import json
import psutil
import websockets
import requests
import openai

# 環境変数または直接設定から取得（公式ドキュメント通り小文字ヘッダーを使用）
HANDCASH_APP_ID = os.environ.get("HANDCASH_APP_ID", "6a7987969b239d1da6e89505")
HANDCASH_APP_SECRET = os.environ.get("HANDCASH_APP_SECRET", "db01ad39e1f40529f286f11dd4fcd554d097b5d25f55d195fcc086f120eab84f")
HANDCASH_V3_API = "https://cloud.handcash.io/v3/paymentRequests"

TARGET_FILE = "target_script.py"
VAULT_DIR = "handcash_v3_vault"
WS_PORT = 8765

CPU_CORES = os.cpu_count() or 4
WORKER_SCALE = CPU_CORES * 4

INITIAL_TARGET_CODE = """# target_script.py
import time

def compute_workload():
    total = 0
    for i in range(100000):
        total += i
    return f"Workload Complete. Total: {total}"

if __name__ == "__main__":
    start = time.time()
    result = compute_workload()
    elapsed = time.time() - start
    print(f"{result} (Time: {elapsed:.5f}s)")
"""

CONNECTED_CLIENTS = set()

def setup_environment():
    if not os.path.exists(VAULT_DIR):
        os.makedirs(VAULT_DIR)
    if not os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            f.write(INITIAL_TARGET_CODE)

class HandCashV3PaymentConnector:
    def __init__(self):
        # 公式ドキュメントの注意点に従い、ヘッダーのキーはすべて小文字
        self.headers = {
            "app-id": HANDCASH_APP_ID,
            "app-secret": HANDCASH_APP_SECRET,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def create_payment_request(self, worker_id, reward_usd):
        """公式v3仕様に基づくPayment Requestの作成"""
        payload = {
            "product": {
                "name": f"Swarm Evolution Reward (Worker #{worker_id})",
                "description": "Autonomous AST optimization milestone achievement.",
                "imageUrl": "https://example.com/product.jpg"
            },
            "instrumentCurrencyCode": "BSV", # 公式の修正: "USD" は不可、"BSV" または "MNEE"
            "currency": "USD",
            "receivers": [
                {
                    "destination": "yourhandle", # ご自身のHandCashハンドルに変更してください
                    "sendAmount": reward_usd
                }
            ],
            "expirationType": "never"
        }
        try:
            response = requests.post(HANDCASH_V3_API, headers=self.headers, json=payload, timeout=10)
            if response.status_code == 200 or response.status_code == 201:
                return True, response.json()
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)

class HandCashV3SwarmOrchestrator:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.connector = HandCashV3PaymentConnector()

    def validate_ast(self, code_text):
        try:
            ast.parse(code_text)
            return True
        except SyntaxError:
            return False

    def benchmark_sandbox(self, filepath):
        start_time = time.time()
        try:
            result = subprocess.run(
                ["python", filepath],
                capture_output=True,
                text=True,
                timeout=5
            )
            duration = time.time() - start_time
            cpu_load = psutil.cpu_percent(interval=None)
            mem_load = psutil.virtual_memory().percent
            
            if result.returncode == 0:
                penalty = (cpu_load * 0.02) + (mem_load * 0.01)
                score = max(100.0 - (duration * 25) - penalty, 5.0)
                return True, score
            else:
                return False, 0.0
        except Exception:
            return False, 0.0

    def worker_node_mutation(self, base_code, worker_id, directive):
        prompt = f"""
あなたはHandCash v3経済圏に統合されたプログラミング・ワーカー（ID: #{worker_id}）です。
以下の指令に基づき、ベースコードのAST構造を最適化してください。
出力はMarkdownの修飾や説明を含めず、実行可能なPythonコードの生テキストのみを返してください。

【指令】
{directive}

【ベースコード】
{base_code}
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.95
            )
            code = response.choices[0].message.content.strip()
            if code.startswith("```python"):
                code = code[9:]
            if code.endswith("```"):
                code = code[:-3]
            return worker_id, code.strip()
        except Exception:
            return worker_id, base_code

    async def broadcast(self, event, data):
        if CONNECTED_CLIENTS:
            msg = json.dumps({"event": event, "timestamp": time.time(), "data": data})
            await asyncio.gather(*[c.send(msg) for c in CONNECTED_CLIENTS])

    async def run_cycle(self, gen):
        print(f"\n==================================================")
        print(f"=== [HandCash v3経済圏スウォーム 世代 {gen} 稼働] ===")
        print(f"==================================================")

        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            base_code = f.read()

        _, base_score = self.benchmark_sandbox(TARGET_FILE)
        print(f"[*] 現行コード基準スコア: {base_score:.2f}")

        directive = "ループ処理を完全にインライン展開し、CPUおよびメモリ効率の物理的限界を突破せよ。"
        
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_SCALE) as executor:
            futures = [
                loop.run_in_executor(executor, self.worker_node_mutation, base_code, i+1, directive)
                for i in range(WORKER_SCALE)
            ]
            results = await asyncio.gather(*futures)

        candidates = []
        for worker_id, variant in results:
            if self.validate_ast(variant):
                candidates.append((worker_id, variant))

        if not candidates:
            print("[!] 有効な変異体が生成されませんでした。")
            return

        best_code = base_code
        best_score = base_score
        winner_id = -1

        for worker_id, candidate in candidates:
            test_file = f"temp_v3_test_{worker_id}.py"
            with open(test_file, "w", encoding="utf-8") as tf:
                tf.write(candidate)

            success, score = self.benchmark_sandbox(test_file)
            if os.path.exists(test_file):
                os.remove(test_file)

            if success and score > base_score:
                best_score = score
                best_code = candidate
                winner_id = worker_id

        if winner_id != -1:
            score_delta = best_score - base_score
            reward_usd = round(max(score_delta * 0.01, 0.01), 2)
            print(f"[✔ 世代交代勝者] ワーカー #{winner_id} が勝利！ 報酬リンク（${reward_usd} USD分）の作成をAPIに要求します...")
            
            # HandCash v3 APIを叩いてPayment Requestを発行
            success, res_data = self.connector.create_payment_request(winner_id, reward_usd)
            if success:
                print(f"[✔ API連携成功] 支払請求が作成されました:\n{json.dumps(res_data, indent=2)}")
            else:
                print(f"[!] APIエラー: {res_data}")

            with open(TARGET_FILE, "w", encoding="utf-8") as f:
                f.write(best_code)

            with open(os.path.join(VAULT_DIR, f"v3_gen_{gen}.py"), "w", encoding="utf-8") as vf:
                vf.write(best_code)

            await self.broadcast("v3_payment_created", {"generation": gen, "winner": winner_id, "response": res_data})
        else:
            print("[= 停滞] 成果向上が見られなかったため、リクエスト発行は見送られました。")

async def ws_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        CONNECTED_CLIENTS.remove(websocket)

async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("[!] エラー: 環境変数 'OPENAI_API_KEY' が設定されていません。")
        return

    setup_environment()
    print(f"=== [HANDCASH V3 SWARM SERVER ACTIVE ON PORT {WS_PORT}] ===")
    orchestrator = HandCashV3SwarmOrchestrator()
    
    for gen in range(1, 2):
        await orchestrator.run_cycle(gen)
        await asyncio.sleep(1)

    print("\n=== [HandCash v3経済圏スウォーム・セッション完了] ===")

if __name__ == "__main__":
    asyncio.run(main())

