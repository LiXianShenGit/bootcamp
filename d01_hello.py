"""
Day 1 · 第一次跟大模型说话
================================================================
跑法（第一次会自动装依赖）：
    cd D:/WorkBuddy/workBuddy_cash/学习AI开发/bootcamp
    cp .env.example .env      # 然后编辑 .env 填你的 key
    uv run d01_hello.py

你会依次看到 4 个实验：
    实验 1  单次调用 + 用量统计       → 看懂 input/output token
    实验 2  算钱                      → 建立成本直觉（最重要）
    实验 3  流式输出                  → 打字机效果怎么来的
    实验 4  temperature 对比           → 亲眼看到"不确定性"

今天的目标不是学会调 API（那 10 分钟就会），
是建立 3 个直觉：token 是计费单位、成本可以算、模型输出不稳定。
这三个直觉，决定你以后写的是玩具还是生产系统。
"""

import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY", "").strip()
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").strip()
MODEL = os.getenv("LLM_MODEL", "deepseek-chat").strip()
PRICE_IN = float(os.getenv("PRICE_IN_PER_M", "2.0"))   # 元 / 百万 input token
PRICE_OUT = float(os.getenv("PRICE_OUT_PER_M", "8.0"))  # 元 / 百万 output token


def divider(title: str) -> None:
    print("\n" + "=" * 62)
    print(f"  {title}")
    print("=" * 62)


def check_env() -> None:
    if not API_KEY or "你的key" in API_KEY:
        print("❌ 还没填 key。打开 bootcamp/.env，把 LLM_API_KEY 换成你自己的。")
        sys.exit(1)


def main() -> None:
    check_env()
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    print(f"模型：{MODEL}")
    print(f"接口：{BASE_URL}")

    # ---------------------------------------------------------------
    # 实验 1：单次调用
    # 观察点：usage 里的 prompt_tokens / completion_tokens 是两个独立计费项
    # ---------------------------------------------------------------
    divider("实验 1 · 单次调用 + 用量")
    question = "用一句话解释什么是 token，不要超过 30 个字。"
    t0 = time.time()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        temperature=0.3,
    )
    cost_ms = (time.time() - t0) * 1000

    print(f"我问：{question}")
    print(f"它答：{resp.choices[0].message.content}")
    print(f"\n耗时：{cost_ms:.0f} ms")
    print(f"输入 token：{resp.usage.prompt_tokens}   ← 我发过去的话")
    print(f"输出 token：{resp.usage.completion_tokens}   ← 它生成的话")
    print(f"合计：{resp.usage.total_tokens}")

    # ---------------------------------------------------------------
    # 实验 2：算钱 —— 这一步最值钱
    # 面试官问"你怎么控成本"，能当场算的人不到 10%
    # ---------------------------------------------------------------
    divider("实验 2 · 算钱（建立成本直觉）")
    in_tok = resp.usage.prompt_tokens
    out_tok = resp.usage.completion_tokens
    one_call = in_tok / 1_000_000 * PRICE_IN + out_tok / 1_000_000 * PRICE_OUT

    print(f"这一次调用花了：{one_call:.6f} 元")
    print("\n放大到真实业务：")
    for scale, label in [(1_000, "1000 次（一个小功能上线第一天）"),
                         (100_000, "10 万次（一个部门一个月）"),
                         (1_000_000, "100 万次（一个 C 端产品一天）")]:
        print(f"  {label:<28} {one_call * scale:>10.2f} 元")

    print("\n⚠️ 注意：真正的生产系统输入远不止这一句——")
    print("   RAG 要带上 5 段检索结果（几千 token），Agent 要带上工具定义和")
    print("   历史对话。同样的问答，输入可能从 15 token 涨到 4000 token，")
    print("   成本直接翻几十倍。这就是为什么后面要学「上下文工程」。")

    # 中文 vs 英文的 token 差异（很多人不知道）
    zh = "今天天气很好，我们一起去公园散步吧。"
    en = "The weather is nice today, let's go for a walk in the park."
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        print(f"\n中文 {len(zh)} 字 → {len(enc.encode(zh))} token")
        print(f"英文 {len(en)} 字符 → {len(enc.encode(en))} token")
        print("→ 同样意思，中文往往更省 token。但不同模型的切分方式不同，")
        print("  真要精确算，得用各家自己的 tokenizer。")
    except ImportError:
        print("\n（想精确数 token：uv add tiktoken）")

    # ---------------------------------------------------------------
    # 实验 3：流式
    # 观察点：首 token 延迟（TTFT）和总耗时是两回事
    # 用户感知的"快"，靠的是 TTFT，不是总时长
    # ---------------------------------------------------------------
    divider("实验 3 · 流式输出（打字机效果）")
    print("它正在写：", end="", flush=True)
    t0 = time.time()
    first_token_at = None
    chunks = 0
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用 3 句话介绍你自己，每句换行。"}],
        temperature=0.7,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content or ""
        if delta:
            if first_token_at is None:
                first_token_at = time.time()
            chunks += 1
            print(delta, end="", flush=True)
    total = time.time() - t0
    print(f"\n\n首 token 延迟（TTFT）：{(first_token_at - t0) * 1000:.0f} ms  ← 用户感受到的'快'")
    print(f"总耗时：{total * 1000:.0f} ms  ← 全文生成完")
    print(f"收到 {chunks} 个 chunk")

    # ---------------------------------------------------------------
    # 实验 4：temperature
    # 观察点：同一个问题，同样的代码，输出不一样
    # 这不是 bug，是特性。理解它，你才知道什么时候该锁死它
    # ---------------------------------------------------------------
    divider("实验 4 · temperature 对比（看不确定性）")
    q4 = "给一个 30 岁想转行学编程的人一句建议，20 字以内。"
    for temp in (0.0, 1.3):
        print(f"\n--- temperature = {temp} ---")
        for i in range(3):
            r = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": q4}],
                temperature=temp,
                max_tokens=60,
            )
            print(f"  第{i + 1}次：{r.choices[0].message.content.strip()}")

    divider("今天到此为止")
    print(
        """你要带走的三件事：

  1. token 是计费单位，输入和输出分开算价 → 省成本先省输入
  2. 成本能算出来，就别拍脑袋 → 面试能当场算的人极少
  3. 模型输出不稳定是特性 → 要稳定就降温度 + 加校验 + 加重试

下一步（自己动手，别跳过）：
  · 把实验 4 的 temperature 改成 -0.5，看报什么错
  · 把实验 1 的 prompt 换成一段 300 字的中文，看 prompt_tokens 涨多少
  · 打开 .env 把 PRICE_IN_PER_M 改成 0.5 再跑一次实验 2，感受价格敏感度

做完在对话里回我一句「跑通了，看到 XXX」，我给你 Day 2。"""
    )


if __name__ == "__main__":
    main()
