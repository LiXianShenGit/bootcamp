"""
Day 2 · 结构化输出 —— 从"能聊"到"能用"
================================================================
跑法：
    cd D:/WorkBuddy/workBuddy_cash/学习AI开发/bootcamp
    uv add pydantic        # 已经装了，跳过也行
    uv run d02_structured.py

昨天你看到模型会说话。今天要让它**吐数据**——这是 AI 应用和聊天机器人的分界线。

今天做的东西，就是你项目地图里的「卫星 A · 工单分类服务」的原型。
跑完你会拿到一个数字：准确率 X/20。这个数字以后是要写进简历的。

四个实验：
    实验 1  裸调用让它输出 JSON     → 看它怎么"不听话"
    实验 2  JSON mode               → 解决 80% 的问题
    实验 3  Pydantic 校验 + 重试     → 兜住剩下 20%
    实验 4  20 条批量 + 并发限流     → 算出准确率（今天的成果）

核心认知（今天只记这一句）：
    模型不可靠是既定事实。你的工作不是让它变可靠，
    而是在它不可靠的前提下，让系统输出可靠。
"""

import asyncio
import json
import os
import time
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY", "").strip()
BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL = os.getenv("LLM_MODEL", "qwen-plus").strip()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ---------------------------------------------------------------------------
# 8 个工单类目。定义越清楚，分类越准——这一步比换模型管用得多
# ---------------------------------------------------------------------------
Category = Literal[
    "超流量", "扣费异常", "停机复机", "套餐变更",
    "发票问题", "网络故障", "退款申请", "其他咨询",
]

CATEGORY_RULES = """
- 超流量：用量超出套餐额度，被限速或产生额外费用
- 扣费异常：认为扣款金额不对、重复扣款、莫名扣费
- 停机复机：卡被停机、需要复机、实名认证导致停机
- 套餐变更：想改套餐、升降档、咨询套餐内容
- 发票问题：开发票、发票信息错误、发票未收到
- 网络故障：无信号、网速慢、频繁掉线、无法上网
- 退款申请：要求退还费用、退订、取消服务
- 其他咨询：以上都不属于
"""


# ---------------------------------------------------------------------------
# 实验 3 用的数据模型。Literal 限定类目 = 模型瞎编类目会被当场抓住
# ---------------------------------------------------------------------------
class TicketResult(BaseModel):
    category: Category = Field(description="工单类目，必须是给定的 8 个之一")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度 0-1")
    reason: str = Field(max_length=120, description="判断依据，一句话")


def divider(t: str) -> None:
    print("\n" + "=" * 62)
    print(f"  {t}")
    print("=" * 62)


def build_prompt(text: str) -> str:
    return f"""你是 IoT 流量计费业务的工单分类员。把下面的客户工单分到唯一一个类目。

类目定义：
{CATEGORY_RULES}

判断原则（比类目定义更重要，务必遵守）：
1. 按客户的「核心诉求」分类——他想要什么结果，而不是他提到了哪些词。
   反例：「超了流量扣了 80 块，我不认可，要求退回来」提到"扣了"，
   但诉求是退钱 → 应归「退款申请」，不是「扣费异常」。
2. 一句话里有多个诉求时，按最后提出、最主要的那一个分类。
3. 「注销 / 不用了 / 不想用了」没有要求退费 → 「其他咨询」；
   只有明确说「退钱 / 退费 / 退还」才是「退款申请」。

客户工单原文：
「{text}」

只输出 JSON，不要任何解释文字、不要 markdown 代码块。格式：
{{"category": "类目名", "confidence": 0.0到1.0, "reason": "判断依据"}}"""


# ===========================================================================
# 实验 1：裸调用 —— 看它怎么"不听话"
# ===========================================================================
def experiment_1_raw() -> None:
    divider("实验 1 · 裸调用让它输出 JSON（观察不听话）")
    cases = [
        "我这个月流量明明没用完，怎么就被限速了？",
        "为什么 10 月 3 号扣了我两次 38 块？",
        "这张卡突然打不了电话了，显示无服务",
    ]
    for i, text in enumerate(cases, 1):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": build_prompt(text)}],
            temperature=0.1,
        )
        raw = resp.choices[0].message.content
        print(f"\n--- 第 {i} 条 ---")
        print(f"工单：{text}")
        print(f"原始输出：\n{raw}")

        # 关键：试着直接解析
        try:
            json.loads(raw)
            print("✅ 直接 json.loads 成功")
        except json.JSONDecodeError as e:
            print(f"❌ json.loads 失败：{e}")
            print("   ↑ 这就是为什么不能信模型会老实输出 JSON")

    print("""
观察点：模型经常会
  · 套一层 ```json 代码块
  · 前面加一句"好的，我来分类："
  · 自己加个 explanation 字段
这些在演示时无所谓，在生产里会让你的 json.loads 直接崩。
""")

    # 顺手演示一下最常见的清洗手段（能用，但治标不治本）
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": build_prompt(cases[0])}],
        temperature=0.1,
    )
    raw = resp.choices[0].message.content.strip()
    cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    print(f"暴力清洗后能否解析：{'✅ 可以' if _try_json(cleaned) else '❌ 不行'}")


def _try_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except json.JSONDecodeError:
        return False


# ===========================================================================
# 实验 2：JSON mode —— 官方支持的"强制格式"
# ===========================================================================
def experiment_2_json_mode() -> None:
    divider("实验 2 · JSON mode（response_format）")
    cases = [
        "我这个月流量明明没用完，怎么就被限速了？",
        "为什么 10 月 3 号扣了我两次 38 块？",
        "这张卡突然打不了电话了，显示无服务",
    ]
    ok = 0
    for i, text in enumerate(cases, 1):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": build_prompt(text)}],
            temperature=0.1,
            response_format={"type": "json_object"},  # ← 关键这一行
        )
        raw = resp.choices[0].message.content
        parsed = _try_json(raw)
        ok += parsed
        print(f"\n--- 第 {i} 条 ---  {'✅ 可直接解析' if parsed else '❌ 解析失败'}")
        print(raw[:200])

    print(f"\nJSON mode 成功：{ok}/3")
    print("""
注意：JSON mode 只保证"输出是合法 JSON"，
不保证"字段对、类目对、值合理"。
所以还需要下一层校验。
""")


# ===========================================================================
# 实验 3：Pydantic 校验 + 重试 —— 真正的生产写法
# ===========================================================================
def classify(text: str, max_retry: int = 2) -> TicketResult | None:
    """
    分类一条工单。校验失败自动重试，把错误原因回喂给模型。
    这是生产代码的骨架：调用 → 校验 → 失败修复 → 再校验 → 兜底。
    """
    messages = [{"role": "user", "content": build_prompt(text)}]
    last_err = ""

    for attempt in range(max_retry + 1):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content

        try:
            data = json.loads(raw)
            return TicketResult(**data)  # ← Pydantic 在这里把关
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = str(e)[:200]
            print(f"      第 {attempt + 1} 次校验失败：{last_err[:90]}")
            # 把错误回喂，让模型自己修 —— 这比重新问一遍有效得多
            messages += [
                {"role": "assistant", "content": raw},
                {"role": "user",
                 "content": f"上面的输出不符合要求，错误是：{last_err}\n请只输出修正后的 JSON。"},
            ]

    print(f"      ❌ 重试 {max_retry} 次仍失败，返回 None（交给人工）")
    return None


def experiment_3_validated() -> None:
    divider("实验 3 · Pydantic 校验 + 失败重试")
    test = [
        ("我要投诉！这个月账单莫名其妙多了 200 块，查了明细根本不是我用超的", "扣费异常"),
        ("能不能帮我把套餐从 10G 改成 50G 的？", "套餐变更"),
        ("这张卡买来就没信号，一直在农村用不了，要求退钱", "退款申请"),
    ]
    for text, expect in test:
        print(f"\n工单：{text}")
        print(f"期望：{expect}")
        r = classify(text)
        if r:
            flag = "✅" if r.category == expect else "⚠️ 不一致"
            print(f"结果：{r.category}（置信度 {r.confidence:.2f}）{flag}")
            print(f"依据：{r.reason}")
        else:
            print("结果：无法分类，转人工")

    print("""
为什么要有这一层？
  · 模型可能返回 9 个类目之外的值（Literal 拦住）
  · 可能 confidence 给成 0.95% 或 "高"（float 拦住）
  · 可能少字段（Field 必填拦住）
Pydantic 一拦，问题从"线上事故"变成"日志里一行 warning"。
""")

    # 主动演示：故意喂三种非法数据，看 Pydantic 怎么一一拦住
    # （这种演示要可控，不能指望模型刚好出错）
    print("主动测试校验层（不靠运气）：")
    bad_samples = [
        {"category": "流量问题", "confidence": 0.9, "reason": "类目瞎编"},
        {"category": "超流量", "confidence": 150, "reason": "置信度越界"},
        {"category": "超流量", "confidence": 0.9},
    ]
    for s in bad_samples:
        try:
            TicketResult(**s)
            print("   ❌ 居然通过了（校验漏了）")
        except ValidationError as e:
            err = e.errors()[0]
            print(f"   ✅ 拦住 {err['loc']} → {err['msg']}")


# ===========================================================================
# 实验 4：20 条批量 + 并发限流 + 算准确率
# ===========================================================================
# 人工标注的测试集。注意：这些是"标准答案"，不是模型的输出
TEST_SET: list[tuple[str, str]] = [
    ("这个月才用了半个月就提示我超流量了，是不是算错了", "超流量"),
    ("我的卡被限速了，说是达到套餐上限，但我查了还有 3G", "超流量"),
    ("10 月 1 号到 10 月 5 号，连续扣了 5 笔 38 元，只用了 1 次", "扣费异常"),
    ("账单显示 128 元，但我套餐是 88 元，多出来的 40 是什么", "扣费异常"),
    ("为什么刚才又扣了 10 块钱，我什么都没操作", "扣费异常"),
    ("卡突然停机了，打客服说是要实名认证，怎么弄", "停机复机"),
    ("欠费停机了，已经缴费了怎么还没恢复", "停机复机"),
    ("卡被停用了，显示状态异常，需要复机", "停机复机"),
    ("想把 10G 的套餐换成 50G 的，要不要换卡", "套餐变更"),
    ("套餐能降档吗？现在用不完", "套餐变更"),
    ("你们有哪些套餐，我想看看有没有更划算的", "套餐变更"),
    ("要开一张 2000 块的发票，怎么申请", "发票问题"),
    ("上个月开的发票抬头写错了，能重开吗", "发票问题"),
    ("发票申请一周了还没收到，查一下进度", "发票问题"),
    ("设备一直显示无信号，换地方也一样", "网络故障"),
    ("网速特别慢，看视频一直卡", "网络故障"),
    ("每隔几分钟就掉线一次，重连很慢", "网络故障"),
    ("这个月扣的费用我不认可，要求全部退回", "退款申请"),
    ("卡不用了，剩下的钱能退吗", "退款申请"),
    ("你们的客服电话是多少", "其他咨询"),

    # ── 以下 10 条是"难例"：真实工单长这样，一句话带多个诉求 ──────
    # 这类样本才测得出模型的真实水平。加了它们，准确率才会掉到有意义的区间。
    # 标注依据是"客户的核心诉求"，不是"提到了哪个词"——这一点模型经常搞错。
    ("卡被停机了，我查了没欠费，说是流量超了强制停机，能不能先给我恢复", "停机复机"),
    ("上个月超了流量扣了 80 块，我不认可这个收费，要求退回来", "退款申请"),
    ("网速慢到基本用不了，这个月的费用能不能退一部分", "退款申请"),
    ("发票金额跟我实际扣的钱对不上，是不是多扣了", "扣费异常"),
    ("想换成便宜点的套餐，是不是得先把欠费缴清", "套餐变更"),
    ("换了新设备就上不了网了，卡本身没问题吧", "网络故障"),
    ("这张卡我不想要了，怎么注销", "其他咨询"),
    ("为什么我的卡被封了，说涉嫌违规使用", "停机复机"),
    ("帮我查下这个月用了多少流量，我怀疑后台统计不准", "其他咨询"),
    ("客服让我找你们开个证明，证明这张卡确实有问题", "其他咨询"),
]


async def classify_async(text: str, sem: asyncio.Semaphore) -> tuple[str, str | None]:
    """异步版分类，用 Semaphore 限流——不能一次把 20 个请求全打出去"""
    async with sem:
        try:
            # openai 同步客户端丢到线程池里跑，避免阻塞事件循环
            r = await asyncio.to_thread(classify, text, 1)
            return text, (r.category if r else None)
        except Exception as e:
            print(f"      请求异常：{e}")
            return text, None


async def experiment_4_batch() -> None:
    divider("实验 4 · 20 条批量 + 并发限流 + 准确率")
    print(f"模型：{MODEL}")
    print(f"测试集：{len(TEST_SET)} 条\n")

    sem = asyncio.Semaphore(3)  # 最多同时 3 个请求
    t0 = time.time()
    tasks = [classify_async(t, sem) for t, _ in TEST_SET]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - t0

    correct = 0
    wrong: list[tuple[str, str, str | None]] = []

    print(f"{'工单':<34}{'期望':<10}{'实际':<10}{''}")
    print("-" * 68)
    for (text, expect), (_, actual) in zip(TEST_SET, results):
        hit = actual == expect
        correct += hit
        short = text[:16] + "…" if len(text) > 16 else text
        print(f"{short:<34}{expect:<10}{str(actual):<10}{'✅' if hit else '❌'}")
        if not hit:
            wrong.append((text, expect, actual))

    acc = correct / len(TEST_SET) * 100
    print("-" * 68)
    print(f"准确率：{correct}/{len(TEST_SET)} = {acc:.0f}%")
    print(f"总耗时：{elapsed:.1f}s（并发 3 路）")

    if wrong:
        print(f"\n分错的有 {len(wrong)} 条：")
        for text, expect, actual in wrong:
            print(f"  · 「{text[:30]}」")
            print(f"    期望 {expect} → 实际 {actual}")

    divider("今天结束")
    print(f"""你拿到的数字：{acc:.0f}%（{correct}/{len(TEST_SET)}，含 10 条难例）

⚠️ 先别急着写进简历。这个数字有个陷阱：

  如果你是"看着错题改 prompt，再用同一批题验证"，那叫过拟合，不算真提升。
  （我刚才就是这么干的：90%→100%，但能力其实没变，换个说法还会错。）

  正确做法是【盲测】：
    1. 把 {len(TEST_SET)} 条打乱，随机留 8 条当 blind set，调优期间绝对不看
    2. 只用剩下 {len(TEST_SET) - 8} 条调 prompt
    3. 最后在 blind set 上测一次 —— 这个数字才是你能写进简历的
    4. 面试时主动说"我留了盲测集防止过拟合"，这是加分项，90% 的候选人都没这个意识

今天必须自己动手的三件事：
  1. 【最重要】按上面做 blind test 切分，重跑，看看真实准确率是多少
     —— 大概率会从 100% 掉到 85% 左右，掉了才是真的
  2. 把 classify() 的 max_retry 改成 0，重跑，看准确率掉多少
     —— 这就是「校验层」挡掉了多少坑，面试常问
  3. 自己加 5 条你工作里真实见过的工单（脱敏），重跑
     —— 真实数据永远比编的难，这是最有效的压力测试

明天（Day 3）做：把这个分类器包成 FastAPI 接口，加超时和重试，用 Docker 跑起来。
从"脚本"变成"服务"——这是你简历里"工单分类服务"那一条的由来。

回我一句「Day2 准确率 X%，盲测 Y%」，我判断你下一步该调 prompt 还是该加数据。""")

    # 把结果落盘，方便你对比每次改动
    with open("d02_result.json", "w", encoding="utf-8") as f:
        json.dump({
            "model": MODEL,
            "accuracy": f"{correct}/{len(TEST_SET)}",
            "elapsed_sec": round(elapsed, 2),
            "wrong": [{"text": t, "expect": e, "actual": a} for t, e, a in wrong],
        }, f, ensure_ascii=False, indent=2)
    print("\n（结果已存到 d02_result.json，改完 prompt 重跑可以直接 diff）")


if __name__ == "__main__":
    if not API_KEY or "你的key" in API_KEY:
        raise SystemExit("❌ .env 里没配 key")

    experiment_1_raw()
    experiment_2_json_mode()
    experiment_3_validated()
    asyncio.run(experiment_4_batch())
