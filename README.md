# 前沿雷达 · 技术基线 v1.1

> 快照时间：**2026-11-02** ｜ 下次强制刷新：**2026-12-27**（每月一次）
>
> 这份文件解决一个问题：AI 领域每周都在变，但**你的学习计划不能每周推倒重来**。  
> 所以分两层：**稳定的底层（不用追）** 和 **流动的上层（必须追）**。
>
> v1.1 变更摘要：**LangChain4j 版本纠偏（1.19.0 → 1.23.0）**、Spring AI 2.1.0 仍为 RC 未 GA、
> 新增「记忆/技能持久化投毒」威胁模型、MCP 工具错误二分法与幂等性要求、JDK 28 Value Class 风险提示。

---

## 一、先建立一个判断力：什么值得追，什么不用追

| 层级      | 内容                                                        | 变化速度     | 你的策略                     |
| ------- | --------------------------------------------------------- | -------- | ------------------------ |
| **不变层** | 上下文工程思想、RAG 检索原理、Agent 循环范式、评估方法论、生产可靠性（限流/幂等/降级/审计）、成本意识 | 3-5 年不变  | **死磕，这是护城河**             |
| **协议层** | MCP、A2A、Agent Skills                                      | 半年一次大版本  | **吃透当前版本 + 关注设计意图**，别背细节 |
| **框架层** | LangGraph、Spring AI、LangChain4j、AgentScope                | 3-6 个月一次 | **学一个深、其余能读**，别做框架收藏家    |
| **模型层** | GPT / Claude / Gemini / Qwen / DeepSeek / GLM             | 每 1-3 个月 | **只记能力边界和价格量级**，不记榜单     |
| **工具层** | 各种 agent 产品、IDE 插件、低代码平台                                  | 每周       | **基本不追**，需要时再看           |

> 一句话：**追不完的别追。你的竞争力在"不变层"，不在"知道最新模型叫什么"。**

---

## 二、2026-11 技术基线（当前必须知道的版本与事实）

### 2.1 协议与标准

| 项目               | 当前状态                                                              | 关键点                                                                                                                                                                                                                                                                                                                                     |
| ---------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MCP**          | **2026-07-28 版本 GA**                                              | ① **无状态化**：去掉 initialize 握手和 `Mcp-Session-Id`，协议版本/客户端能力移入每请求 metadata，list 端点可缓存<br />② **MRTR（多轮往返请求）**：工具可返回 `resultType: "input_required"`，客户端带 `inputResponses` 重试 → **协议级人工审批原语**<br />③ `tasks` 扩展（长任务）、拒绝正式弃用 **DCR**（改用 Client ID Metadata Documents）<br />④ 强制 **RFC 9207 issuer 校验**（修授权服务器混淆漏洞）<br />⑤ 新增扩展框架（服务器渲染 UI、长任务） |
| **MCP 治理**       | Linux 基金会下的 **Agentic AI Foundation（AAIF）**                       | Anthropic + OpenAI + Block 共同创立                                                                                                                                                                                                                                                                                                         |
| **Agent Skills** | **2026-10-22 捐赠给 AAIF，成为中立标准**                                    | 2026-10-23 MCP TS SDK 2.4.0 支持 `loadSkills(folder)` / `skills.attach(server)`（SEP-2640）；70+ 平台已接入（ChatGPT / Cursor / Copilot / VS Code）；已发布约 100 万个 skill、2.8 亿次安装                                                                                                                                                                      |
| **A2A**          | Agent 互联协议，Java 侧有官方实现                                            | 多 Agent 跨组织协作场景才用得到，优先级低于 MCP                                                                                                                                                                                                                                                                                                           |
| **MCP 安全现状**     | ⚠️ 某安全厂商扫描 **33,563** 个 server 构建：**49% 存在安全问题，36% 命中至少 1 条高危规则** | 主要问题：工具描述里的提示注入、网络暴露、来源不明。有 `mcpscore` 这类审计工具（72 条规则 / 0-100 分）                                                                                                                                                                                                                                                                         |

### 2.2 Java 侧工具链（你的主战场）

| 项目                    | 版本                    | 说明                                                                       |
| --------------------- | --------------------- | ------------------------------------------------------------------------ |
| **Spring AI**         | **2.0.2 GA**（最新正式版）| 2.1.0-RC1（2026-10-23）**尚未转 GA**，GA 目标 11 月；2.1.0-M1 已升 Spring Boot **4.2** |
| **LangChain4j**       | **1.23.0（2026-10-30）** | Java 8+；`AiServices` 声明式；1.21+ 引入 Decision Models / Guardrails / tool selection（`@Experimental`）；1.22 加 Anthropic 自动 prompt caching；1.23 强化 agentic patterns（MCP client 已按 2026-07-28 spec 实现） |
| **Spring AI Alibaba** | 1.1.2                 | ⚠️ 基于 Spring AI 1.1.2 + Boot 3.5.x，**尚未跟进 Spring AI 2.0 / Boot 4**（选型陷阱） |
| **AgentScope Java**   | 2.0.0 GA（2026-07）     | 多 Agent；模型容错、事件流、多租户、Workspace 隔离                                        |
| **MCP Java SDK**      | 2.0.0 GA              | Spring 团队维护                                                              |
| **Google ADK Java**   | 迭代中                   | 绑 Vertex AI + A2A                                                        |
| **Jlama**             | 迭代中                   | 纯 JVM 跑 GGUF，不需要 Python 运行时                                              |
| **Solon AI**          | 3.5.x+                | 轻量、非框架绑定、Java 8~26                                                       |

> ⚠️ **版本号使用纪律**：Maven 上 `langchain4j` 坐标已迁移到 `org.langchain4j`（旧的 `dev.langchain4j` 坐标在 Maven Central 显示的最新版本停在 1.19.x，与实际 1.23.0 不一致——**不要用旧坐标查版本，会被误导**）。
> 查权威版本用：`curl -s https://repo1.maven.org/maven2/dev/langchain4j/langchain4j-bom/maven-metadata.xml | tail -20`（BOM 的 `lastUpdated` 字段最准）。

### 2.3 Python 侧（你必须能读能写）

| 项目                       | 说明                                                                           |
| ------------------------ | ---------------------------------------------------------------------------- |
| **LangGraph**            | Agent 编排事实标准：StateGraph / checkpointer / interrupt（HITL）/ 子图                 |
| **LangChain**            | 生态大而全，但 2026 年建议"读得懂、少依赖"                                                    |
| **LlamaIndex**           | 文档/RAG 场景强                                                                   |
| **FastMCP**              | 写 MCP Server 最快的方式                                                           |
| **Ragas**                | RAG 四指标：faithfulness / answer_relevancy / context_precision / context_recall |
| **PromptFoo**            | Prompt 回归测试 + CI 集成（评估进流水线的首选）                                               |
| **LangFuse / LangSmith** | 可观测：trace 树、会话回放、成本统计                                                        |
| **vLLM / SGLang**        | 推理加速（PagedAttention、continuous batching）                                     |

### 2.4 模型层（只记量级，别背榜单）

| 模型                | 特征（2026-10 视角）                                                              |
| ----------------- | --------------------------------------------------------------------------- |
| Qwen3.8-Max       | 2.4T 参数 / 95B 激活 / 1M 上下文                                                   |
| DeepSeek-V4-Flash | 284B MoE / 13B 激活 / 1M 上下文 / **MIT 开源**（2026-07-31）；有可配置 `reasoning_effort` |
| Gemini 3.7 Flash  | 价格约为上代一半；端到端成本大幅下降                                                          |
| GLM-5.3           | 开源权重，编码能力有跃升                                                                |

**给你的实用结论**：国内开发用 **Qwen / DeepSeek 的 OpenAI 兼容端点**最省事；做成本对比实验时至少跑 3 个模型；**本地调试用 4B 小模型 + Ollama**，别用大模型烧钱调 bug。

### 2.5 今年被正式命名的工程实践（要学会的"行话"）

按对开发流程的影响排序，这些是面试里能体现你"在圈内"的词：

1. **上下文工程（Context Engineering）** —— 已取代 prompt engineering 成为主流框架。核心：**稀缺资源不是指令质量，是窗口空间**。每个工具定义、每次文件读取、每段子 Agent 记录，都会在后续每次请求中计费。真正的功夫是决定"什么不进上下文"。
2. **Agent Skills** —— 把流程性知识打包成可加载的文件夹（`SKILL.md` + 脚本 + 参考文件），**渐进式加载**，而不是把说明书贴进 prompt。
3. **MCP Server** —— 让 Agent 触达它看不到的系统。
4. **Subagent 委派** —— 把探索性阅读推进子上下文，保持主上下文干净。
5. **验证闸门（Verification Gates）** —— 让 Agent 必须"证明改动有效"才能报完成（hooks + 测试）。
6. **Spec-driven development** —— 把规格当主产物，代码当可再生产物。

### 2.6 ⚠️ 2026-11 新增威胁模型：持久化投毒（Memory / Skills Poisoning）

**这是本次基线刷新最重要的新增项，直接影响 W10 和 W16。**

Pydantic AI 2.64（2026-10-30）新增 `ArtifactScanner`，官方给出的理由值得整段引用：

> 记忆文件和 skills 是**持久化**的，因此某次运行里植入的指令**会在后续的运行中继续生效**。
> 而现有护栏只看得到 prompt、tool call 和 output —— **看不见已经落盘的 skill 或记忆**。

对应的还有 ADK Python 的一个 bug 修复（2026-10-31，尚未发正式版）：把模型**隐藏推理（thoughts）写进记忆**，导致模型把自己上一轮的"内心戏"当成事实检索回来。

**⇒ 对你的直接影响（W10 / W16 要动手做的）：**

| 风险 | 防护动作 |
|---|---|
| 恶意 skill 替换 | skill 目录入库前扫描；catalog 里保留被拒 skill 的**名字但不含内容**，防止未扫描的同名副本顶替 |
| 记忆投毒 | 写入记忆前扫描指令型内容；**禁止把模型 reasoning 当记忆存**；记忆检索时标注来源与可信度 |
| skill / 记忆被投毒后长期生效 | 落盘内容必须有**来源标记 + 版本 + 写入时间**，可审计可回滚 |

> 💡 **这条是你的加分项**。面试时能说出"我们防的不只是提示注入，还有**持久化投毒**——因为 skill 和记忆是落盘的，一次投毒会长期生效"，说明你跟上了 2026-11 的威胁模型，不是停留在 OWASP LLM Top 10 的旧清单。
> 建议写进 W16 的安全章节，README 里贴一句「记忆/skill 写入前扫描，来源可审计」。

### 2.7 MCP 生产细节补充（面试高频，实操必会）

从 2026 年 Q4 社区实践里提炼出的几条，都不是 spec 原文但**是你的 Server 能不能用的关键**：

| 细节 | 做法 | 为什么 |
|---|---|---|
| **工具错误二分法** | 协议错误（未知工具、schema 不符）→ JSON-RPC error；**工具执行错误 → `isError: true` 的正常返回** | 后者会把错误信息交回模型，模型能自我纠正；前者是硬错误，模型无法恢复 |
| **错误文案要带下一步** | 不要返回 `"404"`，返回 `"没有 id=p_99 的订单。先调 list_orders 查可用 id"` | 模型读到错误才知道怎么接着做 |
| **写操作幂等** | 接受 `idempotencyKey`，存结果，重复 key 返回原结果 | 无状态传输下流断了客户端会重发请求，没幂等就会重复写 |
| **工具按意图设计，不按 REST 端点镜像** | 一个工具干一个用户意图（`find_overdue_invoices(customer, min_days)`），而不是把 `get_customer`+`get_accounts`+`get_invoices` 三个都暴露 | 链式调用时模型错选率高、token 消耗大 |
| **读写分离 + 标注 hint** | 写工具标 `destructiveHint`，读工具标 `readOnlyHint` | 让宿主知道哪些需要额外确认 |
| **返回 `resource_link` 而非全文** | 大结果返回链接，让客户端按需取 | 避免一次性撑爆上下文 |
| **Origin 头校验** | 防 DNS rebinding | Streamable HTTP 必做 |

### 2.8 JDK 版本风险提示（Java 侧的隐藏坑）

JDK 27.0.1.0.3 已 GA（2026-10-24），JDK 28 进入 EA（Build 21）。

⚠️ **JDK 28 的 JEP 401 Value Objects 是预览特性，但影响面极大**：开启 preview 后，**30 个 JDK 核心类**（8 个包装类、Record、4 个 Optional、16 个时间类含 `LocalDate`/`Instant`）会变成值对象，行为变化包括：
- `==` 从引用比较变成字段逐一比较（两个独立创建的相同 `LocalDate`，`==` 从 false 变 true）
- 值对象失去内在 monitor，`synchronized` / `wait()` 抛 `IdentityException`
- `WeakHashMap` 拒绝值对象
- 反射改私有字段抛 `IllegalAccessException`

**⇒ 对你的影响**：本计划全程用 **JDK 21**（LTS，Spring AI 2.0 / Boot 4 基线兼容），**不要为了"用最新"升 JDK 28 preview**。但这件事本身是个很好的面试谈资——说明你关注 JVM 生态且知道"新特性不等于该立刻用"。


### 2.9 两个反直觉但极其重要的成本事实

> 面试时说出这两条，对方会立刻知道你"真跑过"。

1. **MCP 不一定比 CLI 便宜**：实测同一任务，MCP 消耗 **4-32 倍** token（MCP server 把所有工具 schema 塞进 session prefix，且每次变动都会让 **prompt cache 失效**）。→ 工具超过 40 个时，客户端甚至可能不再把工具暴露给模型。
2. **反思/多轮自检成本翻倍**：每加一层 Reflexion，token 就翻一倍。**"准确率提升 5% 花掉 3 倍成本"经常是亏的**——要学会算这笔账。 

---

## 三、更新机制（怎么做到"实时跟新"）

### 3.1 每周日 30 分钟：轻扫描（只做记录，不改计划）

按顺序扫这 4 个地方，只记"有没有影响我当前阶段的东西"：

| 来源                                                            | 看什么                   |
| ------------------------------------------------------------- | --------------------- |
| `modelcontextprotocol.io` 的 spec 变更日志                         | MCP 是否又出新版本、有没有破坏性变更  |
| LangGraph / Spring AI / LangChain4j 的 GitHub Release          | 你正在用的框架有没有大版本         |
| 1 个 AI 工程周刊（如 AI Native Engineering / Ben's Bites / 张小珺 / 宝玉） | 本周有没有"新命名的实践"         |
| 你目标岗位的 JD（每周抓 5 条新 JD）                                        | **市场要什么变了没有** ← 这条最重要 |

**输出**：在 `FRONTIER.md` 底部「动态记录」追加 1-3 行。**没东西就写"无变化"。**

### 3.2 每月最后一个周日：强制刷新（可以改计划）

- [ ] 更新本文件第二部分的版本表
- [ ] 判断是否需要调整 `CURRICULUM.md`（**只有两种情况允许改**：① 你正在学的框架出现破坏性变更 ② 目标岗位的 JD 出现了你计划里完全没覆盖的硬要求）
- [ ] 版本号 +0.1，底下写变更说明
- [ ] 抓 10 条目标岗位 JD，把高频新词记到「JD 关键词池」

### 3.3 硬约束：防止自己被新东西带跑

> **计划周期内，任何"要不要加学 XXX"的判断，先过这三问：**
>
> 1. 它是我目标 JD 里出现过的词吗？（不是 → 记下来，不学）
> 2. 不学它，我下周的交付物做不出来吗？（不是 → 不学）
> 3. 它是"不变层"还是"流动层"？（流动层 → 知道它存在就够了）
>
> 三问全过才动。**否则你会在第 6 周开始学一个第 20 周已经过时的东西。**

---

## 四、JD 关键词池（每周抓新 JD 后往里加）

出现 ≥ 3 次就必须在你的简历/项目里体现：

- Agent 核心循环（感知-思考-行动-观察）
- 工具机制设计与实现 / Function Calling
- 任务规划与拆解
- **上下文生命周期管理**
- 权限与扩展机制
- 数据持久化 / 工作隔离策略
- 多 Agent 协作架构
- **MCP / MCP Server 开发**
- **RAG / 向量检索 / 混合搜索**
- **Prompt 工程 / 上下文工程 / Skills 工程 / Harness 工程**
- LangChain / LangGraph / LlamaIndex
- Spring AI / SpringBoot / SpringCloud / 微服务
- 高并发 / 限流 / 熔断 / 缓存 / 消息队列
- vLLM / SGLang / llama.cpp / 推理加速
- 模型调用监控 / 成本控制 / **质量评估机制**
- LangFuse / LangSmith / PromptFoo
- Docker / K8s / CI-CD
- 全栈能力（React / Vue）

---

## 五、动态记录（每周日追加，append-only）

### 2026-10-29 · v1.0 建立基线

- 建立 2026-10 技术基线快照
- 关键判断：Java 侧工具链已全部 GA，转型不需要放弃 Java
- 关键判断：主项目走 NL2SQL / Data Agent，利用数据开发背景做差异化
- 已发生的重大变更：MCP 2026-07-28 spec GA（无状态 + MRTR）；Agent Skills 2026-10-22 捐赠给 AAIF

### 2026-10-29 · 周扫描（记录级，不改计划）

- Spring AI 2.1.0-RC1（10-23，GA 目标 11 月）：`@Tool(requiresConfirmation = true)` 工具级人工确认 + Session Memory（追加式事件日志 + 按轮压缩、不切断 tool_call 与结果）；ChatMemory 系自 2.1 弃用、3.0 移除；依赖升至 MCP Java SDK 2.1.0 → **W11 开工前按 2.1 写，别学 ChatMemory**
- LangGraph 1.2（10-27）：节点级 `timeout` + `error_handler` 可直接路由到恢复节点、SIGTERM 优雅停机存可续 checkpoint；`create_react_agent` 已弃用 → `langchain.agents.create_agent`（middleware）→ 影响 W7 写法与 W16 稳定性验收
- MCP：spec 无新版本（仍 2026-07-28）；reference servers 升 v2.0.0「modern era」（新老客户端双兼容），Tasks & Events 升 WG、Agents 降为兴趣组 → W9 读 spec 不变，SDK 走 2.0+
- JD 新高频：① 熟练使用 Claude Code/Codex 且懂 Skill/MCP 扩展 ② 评估系统 + 质量与成本可观测体系 ③ 多用户隔离的自主规划 Agent（①②已在 W10/W15/W16 覆盖）

### 2026-11-01 · 周扫描（记录级，不改计划）

- LangGraph **1.2.19（10-30，patch）**：1.2.17 修掉「显式 `recursion_limit` 等于默认值时被丢弃」——死循环保护曾静默跑到 9999 步；1.2.18 起 `error_handler` 全路径可恢复、被 recursion limit / `interrupt_after` 停掉的 run 会流回最后一个 checkpoint；**`DeltaChannel` 的 `snapshot_frequency` 默认 1000→100（行为变更，长线程读更快但更占存储，回退传 1000）** → 命中 **W6 轮次保护 / W7 checkpointer / W16 稳定性验收**，写代码按 1.2.19 起
- **基线纠错**：LangChain4j 已到 **1.22.0（10-08）**，不是上表的 1.19.0。1.21 引入 Decision Models / `RoutingChatModel` / RAG re-ranking / tool selection / guardrails（均 `@Experimental`），1.22 加 OpenAI Decisions API + Anthropic 自动 prompt caching → **W12 开工时版本号改 1.22，任务内容不变**
- **Agent Skills 有了首个公开大厂 skill 栈**：MiniMax 10-28 开源 **MCode Stack**（17 个 SKILL.md + 5 清单，MIT），把 harness engineering 落成可执行检查项——`context-tax-audit` 把「工具定义成本」和「工具结果成本」分开算；`tool-budget-audit`；`independent-review` 只给 reviewer diff+需求+测试结果、不给作者对话 → **W10 写 skill 时直接抄这套分类，不是必须学**
- **方向性提示（少 subagent）**：AAIF 侧明确倾向把 router/planner 折进主循环、用 skills 做特化，别铺多 agent 网 → **W7 D4 判断标准改为默认单 agent + skills，只在上下文是实测瓶颈时才上多 agent**
- MCP：spec 仍 **2026-07-28**，本周无新版本、无破坏性变更；Spring AI Alibaba 本周无发布
- JD：国内「资深 AI Agent 开发工程师」（30-60k）把「上下文工程」列为核心职责，并新增「步数 / token / 墙钟 / 调用数 **四重硬上限**」「checkpoint 须工作区文件与会话历史**原子回滚**」→ W8 / W15 / W16 已覆盖，不改计划

### 2026-11-02 · 基线强制刷新 v1.0 → v1.1（计划起点当天）

> 本次刷新方法：三处权威源交叉验证（Maven Central `maven-metadata.xml` 的 `lastUpdated` 时间戳 + 官方 GitHub Releases + 协议官方文档），不用二手博客的版本号。

**版本纠偏（重要，影响 W11/W12 写法）**

| 项目 | 旧基线 | 权威实测 | 处理 |
|---|---|---|---|
| **LangChain4j** | 1.19.0 | **1.23.0（2026-10-30）** | W12 版本号改 1.23.0；1.21+ 的 Decision Models / Guardrails 可作为"进阶了解"，**不作为必学**（`@Experimental`） |
| **Spring AI** | 2.0.0 GA | **2.0.2 GA（最新正式版）**；**2.1.0-RC1 未转 GA** | W11 用 2.0.2 起步；2.1.0 正式版出了再切（重点是别把 RC 当 GA 用） |
| **MCP spec** | 2026-07-28 | **2026-07-28（仍最新）** | 不变；`ping` / `logging/setLevel` / `notifications/roots/list_changed` 已**移除**（非弃用），Roots/Sampling/Logging 走 12 个月弃用窗口，**最早 2027-07-28 之后才可能移除** |

**新增前沿（已写入第 2.6 / 2.7 / 2.8 节）**

- ⚠️ **持久化投毒（Memory / Skills Poisoning）** —— Pydantic AI 2.64（10-30）新增 `ArtifactScanner`，官方理由：记忆与 skill 落盘，**一次投毒长期生效**，而现有护栏看不见已落盘内容；ADK Python 同期修复"把模型隐藏 reasoning 写进记忆"的 bug → **W10 写 skill 时加扫描步骤，W16 安全章节加这一条，并写进 README**
- **MCP 生产细节 7 条**（错误二分法 / 错误文案带下一步 / 写操作幂等 / 工具按意图设计 / 读写分离 hint / `resource_link` / Origin 校验）→ **W9-W10 直接照做，这是"能跑"和"能用"的分界**
- **JDK 28 Value Objects 风险** → 全程用 JDK 21 LTS；此事本身是面试谈资

**JD 侧变化（11-01 抓取）**

- 「Agent 开发工程师」（国聘，15-20K·13薪，北京）职责里明确写了：任务拆解、流程编排、工具调用、多轮对话、**结果评估**、异常处理、**人工审核节点** → 命中 W7/W8/W16，不改计划
- 「Agent 应用开发工程师」（苏州，13万/年）要求：LangChain/LangGraph、**ReAct 范式**、**Function Call**、**上下文压缩**、RAG 知识库构建与优化、**Agent 评测方案设计**；加分项含**本地大模型部署/微调降低显存** → 命中 W6/W8/W15/W13 选修
- 「AI 原生全栈工程师」（南京）要求：本体建模、Agent 智能体模块、**Skill 能力与可复用组件沉淀**、效果评测与可靠性验证 → 命中 W10/W15
- 海外岗（Applied AI Engineer）把 **"评估数据集 + 成功阈值 + 评估进 CI/CD"** 列为必备而非加分 → **这坐实了 W15 是分水岭的判断**
- 薪资现实校准：国内 Agent 开发工程师集中在 **13-20K 区间**（社招 1-5 年）；资深档 30-60K 需要 3 年+ AI 经验 → **转型首份平薪或涨 10-20% 是合理预期**（与原判断一致）

**结论：24 周结构不动。** 本次刷新只改版本号引用（W11/W12）、给 W10/W16 增补安全项、给 W9-W10 增补 MCP 生产细节。**无结构性变更。**


---

*格式：`### YYYY-MM-DD · 一句话结论` 换行 `- 具体变化 / 对我的影响`*
