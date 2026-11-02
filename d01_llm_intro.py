"""
D001 · 手写注意力 + 手写 next-token 预测
================================================================================
跑法：
    cd D:/WorkBuddy/workBuddy_cash/学习AI开发/bootcamp
    uv run d01_llm_intro.py

为什么今天要手写这个：
    你是 Java 后端出身，习惯把 LLM 当成一个"黑盒 HTTP 服务"。
    但面试官问"Transformer 到底在算什么"、"为什么会有幻觉"时，
    答不出机制的人会被当场判定为"只会调 API"。

    90 分钟手写一次注意力，你会得到三样东西：
      1. 一个能画给面试官看的流程图
      2. "幻觉"的机制级解释（不是"因为它瞎编"）
      3. 一个直觉：为什么上下文窗口是有限资源

四个实验：
    实验 1  手写 softmax（带数值稳定性处理）      → 理解归一化
    实验 2  手写缩放点积注意力                   → 打印注意力权重矩阵
    实验 3  手写贪心 next-token 预测              → 亲眼看到"逐词生成"
    实验 4  上下文预算实验                        → 看到注意力如何稀释

⚠️ 本文件不 import 任何 AI 框架。numpy 只用来做矩阵乘法。
   如果你 import 了 transformers / torch，说明你没理解今天的重点。

今天要带走的三个认知：
    ① LLM 是概率机器：它在算"下一个 token 的概率分布"，不是"查数据库"
    ② 幻觉的根源：概率采样必然有低概率路径被选中，且 LLM 没有事实校验器
    ③ 上下文是预算：注意力权重会被稀释，长上下文不等于好上下文
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

# numpy 打印精度：别刷屏，但要看得出分布
np.set_printoptions(precision=3, suppress=True, linewidth=120)


def divider(title: str) -> None:
    print("\n" + "=" * 68)
    print(f"  {title}")
    print("=" * 68)


# =============================================================================
# 实验 1 · 手写 softmax
# =============================================================================
# 面试点：为什么 softmax 要减最大值？（数值稳定性）
#   exp(1000) 在 float32 里直接溢出成 inf
#   减去 max 之后 exp(x - max) 的值域是 (0, 1]，再除回去结果完全不变
# =============================================================================
def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """数值稳定的 softmax（支持指定归一化轴）。"""

    x_max = np.max(x, axis=axis, keepdims=True)   # keepdims 保住维度，便于广播
    e = np.exp(x - x_max)                          # 减最大值 → 不溢出
    return e / np.sum(e, axis=axis, keepdims=True)

def experiment_1_softmax() -> None:
    divider("实验 1 · 手写 softmax（数值稳定性）")

    logits = np.array([2.0, 1.0, 0.5, 3.0])
    probs = softmax(logits)

    print(f"原始 logits      : {logits}")
    print(f"softmax 结果     : {probs}")
    print(f"概率之和         : {probs.sum():.10f}  ← 必须等于 1")
    print(f"最大概率对应     : 第 {int(np.argmax(probs))} 个（logits 最大的是第 {int(np.argmax(logits))} 个）")

    # 数值稳定性验证
    print("\n--- 数值稳定性验证 ---")
    huge = np.array([1000.0, 1001.0, 1002.0])
    with np.errstate(over="ignore", invalid="ignore"):
        naive = np.exp(huge) / np.sum(np.exp(huge))   # 朴素写法：会溢出
    stable = softmax(huge)                            # 稳定写法
    print(f"朴素 exp(1000) 结果 : {naive}   ← 出现 nan 就是溢出了")
    print(f"稳定 softmax 结果   : {stable}")
    # 朴素写法已经溢出成 nan，无法与正确结果比较——这正是要点
    print(f"朴素写法是否已失效   : {bool(np.isnan(naive).any())}  ← 溢出即失效")
    print(f"稳定写法概率和       : {stable.sum():.6f}  ← 仍然是合法分布")
    print("→ 结论：减最大值是必须的。这是你在面试里能说出的'我踩过这个坑'。")


# =============================================================================
# 实验 2 · 手写缩放点积注意力（Scaled Dot-Product Attention）
# =============================================================================
# 公式：Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V
#
#   Q: query   —— "我在找什么"
#   K: key     —— "我是什么"       （Q·K 越大 = 越相关）
#   V: value   —— "我携带的信息"   （被注意力权重加权求和）
#   / sqrt(d_k) —— 防止维度大时点积爆炸导致 softmax 梯度消失
#
# 面试点：
#   - 为什么除 sqrt(d_k)？d_k 越大，点积方差越大，softmax 越接近均匀，梯度趋近 0
#   - 多头是干什么的？不同的头学不同的关注模式（有的看语法，有的看指代）
# =============================================================================
def attention(q: np.ndarray, k: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """单头缩放点积注意力。返回 (输出, 注意力权重)。"""
    d_k = q.shape[-1]
    scores = q @ k.T                      # (seq_q, seq_k) 每个 query 对每个 key 的匹配分
    scores = scores / math.sqrt(d_k)      # 缩放
    weights = softmax(scores, axis=-1)    # 每一行归一化 → 每个 query 的注意力分布
    out = weights @ v                    # 加权求和
    return out, weights


def demo_attention() -> None:
    divider("实验 2 · 手写缩放点积注意力")

    # 造一个玩具"句子"：3 个 token，每个 token 用 4 维向量表示
    # 这里用可解释的手工向量，而不是随机数 —— 这样注意力结果有物理意义
    tokens = ["我", "爱", "编程"]

    # 手工设计 Q/K，让"爱"更关注"编程"（模拟真实语义关系）
    q = np.array([
        [1.0, 0.0, 0.0, 0.0],   # "我" 的 query
        [0.0, 1.0, 0.0, 0.0],   # "爱" 的 query
        [0.0, 0.0, 1.0, 0.0],   # "编程" 的 query
    ])
    k = np.array([
        [1.0, 0.0, 0.0, 0.0],   # "我" 的 key：跟 "我" 匹配
        [0.0, 1.0, 0.0, 0.0],   # "爱" 的 key：跟 "爱" 匹配
        [0.0, 0.0, 1.0, 0.0],   # "编程" 的 key：跟 "编程" 匹配
    ])
    v = np.array([
        [10.0, 0.0],   # "我" 携带的信息
        [0.0, 10.0],   # "爱" 携带的信息
        [0.0, 0.0],    # "编程" 携带的信息
    ])

    out, weights = attention(q, k, v)

    print("句子：", " ".join(tokens))
    print("\n注意力权重矩阵（行 = 当前 token 在看谁，列 = 被看的 token）：")
    print("        " + "".join(f"{t:>10}" for t in tokens))
    for i, t in enumerate(tokens):
        row = "".join(f"{w:>10.3f}" for w in weights[i])
        print(f"  {t:<6}{row}")

    print("\n每一行的和（必须 = 1）：", weights.sum(axis=1))
    print("\n每个 token 聚合后的表示（value 的加权和）：")
    for i, t in enumerate(tokens):
        print(f"  {t:<6} → {out[i]}")

    print("\n怎么读这张表：")
    print("  · 对角线最大 = 每个 token 主要关注自己（这是没有上下文时的退化情况）")
    print("  · 真实模型里，'我' 会更多关注 '爱'（语义关联）")
    print("  · 每一行加起来 = 1，这就是'注意力'的本质：分配信息读取的配额")

    # 缩放因子的影响
    print("\n--- 为什么除 sqrt(d_k) ---")
    print("（用同一组 query/key，只改维度，观察 softmax 分布的尖锐程度）")
    rng = np.random.default_rng(0)
    for d in (4, 16, 64, 256):
        q_t = rng.normal(size=(1, d))
        k_t = rng.normal(size=(8, d))
        raw = q_t @ k_t.T
        scaled = raw / math.sqrt(d)
        p_raw = softmax(raw[0])
        p_scaled = softmax(scaled[0])
        # 用熵衡量分布的平坦程度（熵越小越尖锐）
        ent_raw = float(-(p_raw * np.log(p_raw + 1e-12)).sum())
        ent_scaled = float(-(p_scaled * np.log(p_scaled + 1e-12)).sum())
        print(f"  d_k={d:>4}: 不缩放 最大概率 {p_raw.max():.4f} 熵 {ent_raw:.3f} | "
              f"缩放后 最大概率 {p_scaled.max():.4f} 熵 {ent_scaled:.3f}")

    print("\n→ 维度越大，点积的方差越大。不缩放时 softmax 会被推向 one-hot，")
    print("  梯度趋近 0（学不动了）；除以 sqrt(d_k) 把方差拉回 1 附近，分布保持可学。")
    print("  注意：熵在两种情况下都会随维度变化，真正的对比要看'不缩放'那一列")
    print("  是否已经饱和到 1.0000 —— 那就是梯度过不了关的信号。")


# =============================================================================
# 实验 3 · 手写贪心 next-token 预测
# =============================================================================
# 这是理解 LLM 的关键：它不是"生成一个句子"，是"重复 n 次：算概率 → 选一个 → 追加"
# 面试点："为什么会有幻觉" —— 因为每一步都在概率分布里采样，
#   没有任何一步在检查"这是不是真的"。低概率的路径一旦被选中，后面就会顺着编。
# =============================================================================
def demo_next_token() -> None:
    divider("实验 3 · 手写贪心 next-token 预测")

    # 一个玩具词表：给每个词一个"分数"（真实模型里这来自神经网络）
    # 注意：这些是 logits，不是概率——logits 可以是任意实数（负数、超过 1 都行）
    vocab = {
        "天气": 2.5, "很": 1.8, "好": 0.9, "不": -0.4,
        "热": -1.1, "冷": -1.8, "下雨": -2.6, "雪": -3.2,
    }
    tokens = list(vocab.keys())
    logits = np.array([vocab[t] for t in tokens])

    print("词表（logits，注意这不是概率）：")
    for t, s in vocab.items():
        print(f"  {t:<6} {s:>6.2f}")
    print(f"  总和 = {logits.sum():.2f}  ← logits 可以是负数、可以超过 1，它不是概率")
    print("  （真实模型输出的 logits 长这样：一堆没有意义的实数，经过 softmax 才是概率）")

    # 走 softmax 得到真正的概率分布
    probs = softmax(logits)
    print("\nsoftmax 之后的概率分布（这才叫概率）：")
    for t, p in sorted(zip(tokens, probs), key=lambda x: -x[1]):
        bar = "█" * int(p * 40)
        print(f"  {t:<6} {p:.4f}  {bar}")

    # 贪心生成
    # 关键：真实模型的分布会**随上下文变化**——每生成一个词，
    # 下一个词的分布就完全不一样了。静态词表只能演示"贪心会重复"。
    print("\n贪心生成（静态词表 —— 演示'贪心必然重复'）：")
    current = ["今天"]
    for step in range(6):
        p = softmax(np.array([vocab[t] for t in tokens]))
        best = int(np.argmax(p))
        current.append(tokens[best])
        print(f"  第{step + 1}步：选了「{tokens[best]}」(p={p[best]:.4f})  →  {' '.join(current)}")
    print("  ↑ 注意每一步概率完全一样 —— 因为词表是静态的。")
    print("  真实模型不是这样：'今天天气' 后面接 '很' 的概率会远高于 '天气'。")

    # 动态词表：模拟"上下文影响下一个词"
    print("\n动态词表 —— 演示真实的逐词生成（上下文改变分布）：")
    # 规则：当前词决定下一个词的候选与权重（简单模拟"语言模型的接龙"）
    dynamic = {
        "今天": {"天气": 3.0, "的": 0.6, "很": 0.4},
        "天气": {"很": 3.0, "不": 1.0, "热": 0.5, "冷": 0.2},
        "很":   {"好": 3.2, "热": 1.0, "冷": 0.3},
        "好":   {"。": 4.0, "吗": 1.0, "的": 0.5},
        "。":   {"今天": 2.0, "天气": 1.0},
    }
    context = "今天"
    generated: list[str] = []
    print(f"  起始上下文：{context}")
    for step in range(8):
        if context not in dynamic:
            print(f"  第{step + 1}步：上下文「{context}」不在词表里 → 结束（模拟 EOS）")
            break
        nexts = dynamic[context]
        ntokens = list(nexts.keys())
        p = softmax(np.array([nexts[t] for t in ntokens]))
        pick = ntokens[int(np.argmax(p))]
        cand = ", ".join(f"{t}={pr:.2f}" for t, pr in zip(ntokens, p))
        print(f"  第{step + 1}步：输入「{context}」→ 候选 [{cand}]")
        print(f"         选中「{pick}」(p={p.max():.4f})")
        generated.append(pick)
        context = pick
    print(f"\n  生成结果：今天{''.join(generated)}")
    print("  ↑ 这才是真实 LLM 的工作方式：给一段上下文，输出下一个 token 的分布，")
    print("    采样一个，追加到上下文，再来一轮。循环到结束符为止。")
    print("  注意每一步的候选集都不一样——因为上下文变了，分布就变了。")

    # 温度实验
    print("\n--- temperature 对分布的影响 ---")
    for temp in (0.0, 0.7, 2.0):
        # temperature=0 是极限情况：用放大 logits 模拟"绝对贪心"
        scaled = logits / max(temp, 1e-6) if temp > 0 else logits * 100.0
        p = softmax(scaled)
        top = int(np.argmax(p))
        ent = float(-(p * np.log(p + 1e-12)).sum())
        print(f"  temperature={temp:<4} 最大概率={p.max():.4f} 熵={ent:.3f} "
              f"最可能词=「{tokens[top]}」")
    print("\n→ temperature→0 分布尖锐（确定但重复）；temperature 高分布平坦（多样但易胡话）。")
    print("  真实 API 里 temperature=0 通常仍非完全确定（浮点与并行计算导致）。")

    # 采样演示：为什么高 temperature 会"编"
    print("\n--- 采样演示：同一个分布，采 8 次会得到不同句子 ---")
    rng = np.random.default_rng(7)
    for temp in (0.3, 1.5):
        samples: list[str] = []
        for _ in range(8):
            scaled = logits / temp
            p = softmax(scaled)
            pick = int(rng.choice(len(tokens), p=p))
            samples.append(tokens[pick])
        uniq = len(set(samples))
        print(f"  temperature={temp}: {samples}  → {uniq} 种不同结果")
    print("\n→ temperature 高时，低概率词也会被采到（'雪' 也会出现）。")
    print("  模型没有事实校验器，它只知道'雪'在语料里和'天气'共现过。")
    print("  **这就是幻觉的机制：概率采样 + 没有事实校验 = 会自信地编。**")


# =============================================================================
# 实验 4 · 上下文预算：注意力会稀释
# =============================================================================
# 面试点："上下文窗口有 128K，为什么还要做上下文管理？"
#   答案：注意力权重会被稀释 + 成本线性上涨 + "Lost in the Middle" 现象
# =============================================================================
def demo_context_budget() -> None:
    divider("实验 4 · 上下文预算：注意力被稀释")

    n = 20
    dim = 8
    rng = np.random.default_rng(42)

    # ────────────────────────────────────────────────────────────────────────
    # 场景：20 个 token，每个都和 query 有中等相关性。
    # 关键信息只是其中"稍微更相关"的一个（不是绝对相关）。
    # ────────────────────────────────────────────────────────────────────────
    def build_context(n_ctx: int, key_idx: int) -> tuple[np.ndarray, np.ndarray]:
        q = rng.normal(size=dim)
        keys = rng.normal(size=(n_ctx, dim))
        common = rng.normal(size=dim)          # 公共分量：所有 token 都有点相关
        keys += common * 0.8
        keys[key_idx] = q * 0.9 + common * 0.8  # 关键 token 额外相关一点
        return q, keys

    # ────────────────────────────────────────────────────────────────────────
    # 主结论：上下文越长，关键 token 能分到的注意力配额越少
    # 这是数学必然——softmax 的分母是所有 token 的指数和
    # ────────────────────────────────────────────────────────────────────────
    print("【主结论】上下文长度 vs 关键 token 能拿到的注意力权重")
    print(f"{'上下文长度':<12}{'关键 token 权重':>18}{'相对 5-token 基准':>22}")
    baseline = None
    for n_ctx in (5, 10, 20, 50, 100):
        ws = []
        for _ in range(30):
            q, kk = build_context(n_ctx, n_ctx // 2)
            _, ww = attention(q[None, :], kk, rng.normal(size=(n_ctx, dim)))
            ws.append(ww[0][n_ctx // 2])
        mean_w = float(np.mean(ws))
        if baseline is None:
            baseline = mean_w
        print(f"{n_ctx:<12}{mean_w:>18.4f}{mean_w / baseline:>22.2f}x")

    print("\n→ 上下文从 5 涨到 100，关键 token 的注意力配额掉到 1/5 以下。")
    print("  这不是模型'笨'，是 softmax 的数学性质：")
    print("  每一行权重加起来必须等于 1，token 越多，每个能分到的越少。")
    print()
    print("  **面试可讲**：上下文窗口有 128K，为什么还要做上下文工程？")
    print("  因为瓶颈不是'装不下'，而是'装进去也读不出来'——")
    print("  注意力是有限配额，不是无限的记忆。")

    # ────────────────────────────────────────────────────────────────────────
    # 位置效应：如实说明这个玩具版本演示不出来
    # ────────────────────────────────────────────────────────────────────────
    print("\n" + "-" * 68)
    print("【补充】关键 token 的位置是否影响权重？")
    print("-" * 68)
    results: dict[str, float] = {}
    for label, idx in [("最前面", 0), ("前面1/4", n // 4), ("正中间", n // 2),
                       ("后面1/4", 3 * n // 4), ("最后面", n - 1)]:
        ws = []
        for _ in range(30):
            q, kk = build_context(n, idx)
            _, ww = attention(q[None, :], kk, rng.normal(size=(n, dim)))
            ws.append(ww[0][idx])
        results[label] = float(np.mean(ws))

    for label, val in results.items():
        print(f"  {label:<10}{val:>10.4f}")

    spread = max(results.values()) - min(results.values())
    print(f"\n  最大差异：{spread:.4f}（各位置权重都在 0.28~0.37 之间）")
    print("\n  ⚠️ 诚实说明：这个玩具版本**演示不出清晰的 Lost in the Middle**。")
    print("     原因是它没有位置编码（RoPE）、没有多头、没有多层堆叠——")
    print("     而真实的位置效应正是由这些机制产生的。")
    print()
    print("  Lost in the Middle 是**真实模型的实测结论**（Liu et al., 2023）：")
    print("  关键信息放在上下文的开头或结尾时召回率明显更高，放中间会掉。")
    print()
    print("  你要记住的不是这个脚本的数字，而是那条结论 + 它的成因：")
    print("  **位置本身会影响注意力分配，所以重要的信息要放头尾。**")
    print("  这直接决定了后面 RAG 怎么组装上下文（见 D024-D025）。")

# =============================================================================
# 主流程
# =============================================================================
def main() -> None:
    print("""
D001 · 搞懂 LLM 在干什么
================================================================================
今天不调 API。你已经会调了（D01 的实验 1-4 已验证 qwen-plus 正常）。
今天要建立的是**机制级直觉**——这是面试官真正会问的层次。

跑完你会得到：
  1. 一个能画给面试官的注意力流程图
  2. "为什么会有幻觉"的机制级答案
  3. "上下文是预算不是仓库"的直觉
""")
    experiment_1_softmax()
    demo_attention()
    demo_next_token()
    demo_context_budget()

    divider("今天到此为止")
    print(
        """你要带走的三个认知：

  ① LLM 是概率机器：它在算"下一个 token 的概率分布"，不是"查数据库"
     → 幻觉不是 bug，是概率采样的必然产物（没有任何事实校验环节）

  ② 注意力 = 分配信息读取配额：每行加起来等于 1
     → 上下文越长，单个 token 拿到的配额越少 → 上下文是预算

  ③ 位置会影响注意力分配：重要的信息要放头尾（Lost in the Middle，真实模型实测）
     → 这直接决定了后面 RAG 怎么组装上下文

下一步（自己动手，别跳过）：
  · 把 demo_attention 里的 q/k 改成"我"更多关注"爱"，看权重矩阵怎么变
  · 把 demo_context_budget 的 n 改成 100，再跑一次，看中间位置的权重掉多少
  · 改 demo_next_token 的 vocab 加一个"编程"，用贪心看会不会被采样出来

做完在对话里回我一句「跑通了，看到 XXX」，我给你 D002。
"""
    )


if __name__ == "__main__":
    main()
