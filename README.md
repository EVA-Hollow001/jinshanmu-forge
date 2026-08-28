# 金山木攻坚（Jinshanmu Forge）· 人机对抗攻坚管线

> An adversarial multi-model research pipeline for hard open problems, battle-tested on the Collatz conjecture.
> 人机对抗攻坚管线：互盲铺路 → 专职拆台 → 独立核验 → 幸存者收窄。首战目标：Collatz（3n+1）。

**状态**：Collatz 阶段第 3 轮已收口（山穷水尽报告），**不包含任何未经攻击消化的证明声称**。诚实原则：继承/新推/待验证三色标注，AI 参与如实披露。当前目标已转向 Lonely Runner 猜想。

## 四条结构铁律

1. **断外援**：全树无联网工具，推理只用已知定理与自身知识；不确定的来源标「待验证」，严禁编文献。
2. **宽搜索**：每轮 ≥3 条互盲并行路线，起步角度显式不同，轮内互不可见，严禁第一轮收敛。
3. **内部互审**：每条候选证明必须过专职拆台手（造反例、找边界失效）；攻击手的目标是杀证明，不是帮证明。
4. **不许提前交卷**：完整证明须 ≥2 轮对抗、每个反例被消化或证伪、独立专家逐行复核。卡住就换角度再来一轮，不许交白卷。

## 首战：Collatz 猜想（已收山）

### 战果（第 1–3 轮，独立于文献的数值排除）

**真排除（新推）**：
- 非平凡循环 ⟹ m ≥ 5（m=2,3,4,7：纯连分数 + B–S）。
- **最小元扫描**：不存在最小元 ≤7.216×10⁹ 且恰周期 ≤10⁵ 的非平凡环（自算，不冒充世界纪录）。
- **B 界证书**：m=5..10⁵ 共 99,996 个 m 全部通过（S1）。
- **小 D 清层**：D≤10⁹ 全层 162 对 / 8.28×10⁸ 向量 0 非平凡（R3）。

**已死路线（14 条，每条带精确卡点）**：
- A 唯一化：方向用反（用 N 下界去上界 D），反例 (6,10)（d=0.490>0.263）与 (15,24)/(15,25)。
- 窗内夹逼：窗内 1870 对 I=∅ 为 0，零排除力。
- Baker 单独：无排除力；组合筛：ΣC(A−1,m−1)≈10⁴⁹¹⁶³ 天文爆炸。
- 2-adic/3-adic/素因子覆盖：无独立同余、零筛选。完整死路地图见 D 文章。

**方法论产物**：
- 7 个带真实反例的 AI 数学推理失败模式（articles/B）。
- **预测-验证-对账管线**（tools/collatz_pipeline/）：LLM 直觉 vs 数值现实，两轮校准误差 5.6%→0.9%，可复现。

### 诚实声明

- 全部现代下界（m≥10^10 量级，Simons–de Weger 等）属已知结果，本仓库不冒充新发现。
- 「证明 Collatz」的成功率评估：**0.5–2%**。本仓库的现实价值 = 方法论 + 失败模式目录 + 框架可复用性，不是数学宣告。
- 所有数值经本机 Python 大整数验证；所有裁决带反例。

## 对外文章

- **D · AI 数学方法论复盘**（[GitHub 内文](articles/D-AI数学方法论复盘.md) / [知乎](https://zhuanlan.zhihu.com/p/2076572679369385685) / 掘金同题）：用 LLM + 验证器 + 死路地图打一场数学攻坚的完整记录，含 14 条死路、99,996 证书、预测-验证-对账管线。

## 仓库结构

```
jinshanmu-framework/
├── README.md                  ← 本文件
├── articles/                  ← 对外文章（中文首发）
│   ├── A-负侧鉴别器.md
│   ├── B-七个死法.md
│   ├── C-席位灾备实录.md
│   └── D-AI数学方法论复盘.md  ← v3（45/50 人味版，含 GitHub 链接）
├── preset/                    ← DSH agent 预设（可直接安装）
│   ├── preset.yml
│   └── agent.cordis.yml
├── docs/
│   ├── round1-report.md       ← 第 1 轮完整收口报告
│   ├── round2-report.md       ← 第 2 轮收口（R2a 死亡 + R1 存活）
│   ├── round3-report.md       ← 第 3 轮收口（S2 零杀伤 + 扫描墙）
│   ├── exhausted.md           ← 山穷水尽报告（14 条死路 + 0.5–2% 自评）
│   ├── routeA/B-round1.md     ← 各路线铺路报告
│   ├── publish-copy-ai-math.md← 掘金/知乎发布文案
│   └── basic-verification.md  ← 公共事实核验报告
├── tools/
│   ├── call_deepseek_e.mjs    ← 官方 API 直连脚本（凭据从 .credentials.yaml 读）
│   ├── collatz_verify_r1.py   ← 主持人复核脚本（7 项断言）
│   ├── collatz_r1_sieve.py    ← CF 筛+B–S 整除双筛（第 2 轮主力）
│   ├── collatz_r3_dsmall.py   ← |D| 小值穷尽
│   └── collatz_pipeline/      ← 预测-验证-对账管线（truths + 两轮预测 + 校准图）
└── LICENSE
```

## 安装（DSH）

```bash
# 把 preset/ 拷到 ~/.dsh/.agent-presets/jinshanmu/
# 预设内 subagent 席位已按「plan 无余额」灾备方案重绑：
#   subagent/subagent_flash → deepseek-official（需 DEEPSEEK_API_KEY）
#   minimax → minimax-cn；glm/doubao → volcengine-coding-plan
# settings.yaml 建议加：
#   llm-deepseek: {thinking: enabled, reasoningEffort: max}
```

## 路线图

- ~~第 2 轮：CF 筛机械化推到 m≈10⁶；Baker 主项依赖链；|D| 小值穷尽 → grok 拆台 → 收口。~~
- ~~第 3 轮：m-循环约化 φ(m) 通道判定 → 结论：不可闭（缺可核验常数）→ 出山穷水尽报告。~~
- **下一目标：Lonely Runner 猜想**（同上管线，先铺路后拆台）。

## 作者与披露

人机团队产物。**AI 参与范围**：初稿生成、结构组织、文案润色（含去除 AI 写作腔调的编辑）；**人类主理范围**：研究方向裁定、数据与结论的最终核验、收山决定、发布。**AI 不豁免验证**：本仓库的每一条数学断言都经过攻击手和机器复核，不因来源而免检。

本仓库对 AI 参与不做粉饰，也不刻意强调：AI 写的、人改的、真实算的，三者边界即上文所列。数据真实性不依赖作者身份，依赖产物清单（docs/、tools/ 下全部可复现）。
