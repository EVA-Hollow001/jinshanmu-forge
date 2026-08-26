# 金山木攻坚（Jinshanmu Forge）· 人机对抗攻坚管线

> An adversarial multi-model research pipeline for hard open problems, battle-tested on the Collatz conjecture.
> 人机对抗攻坚管线：互盲铺路 → 专职拆台 → 独立核验 → 幸存者收窄。首战目标：Collatz（3n+1）。

**状态**：第 2 轮已收口，第 3 轮进行中。**本仓库不含任何未经攻击消化的证明声称。** 诚实原则：继承/新推/待验证三色标注，AI 参与如实披露。

## 四条结构铁律

1. **断外援**：全树无联网工具，推理只用已知定理与自身知识；不确定的来源标「待验证」，严禁编文献。
2. **宽搜索**：每轮 ≥3 条互盲并行路线，起步角度显式不同，轮内互不可见，严禁第一轮收敛。
3. **内部互审**：每条候选证明必须过专职拆台手（造反例、找边界失效）；攻击手的目标是杀证明，不是帮证明。
4. **不许提前交卷**：完整证明须 ≥2 轮对抗、每个反例被消化或证伪、独立专家逐行复核。卡住就换角度再来一轮，不许交白卷。

## 首战：Collatz 猜想

### 战果（截至第 2 轮收口）

**真排除（新推）**：
- 非平凡循环 ⟹ m ≥ 5（m=2,3,4,7：纯连分数 + B–S）。
- **最小元扫描**：不存在最小元 ≤7.216×10⁹ 且恰周期 ≤10⁵ 的非平凡环（自算，不冒充世界纪录）。

**第 2 轮拆台后**：
- **A 唯一化已死**：用 N 下界去上界 D 方向非法。反例 (6,10)（d=0.490>0.263，仍在 3.2 窗）与 (15,24)/(15,25)（同 m 双 A）。
- Baker 单独仍无排除力（no-go 方向活，「真实 f≤0.2」死）。
- D≤10⁹ 全层 0 非平凡解（162 对 / 8.28×10⁸ 向量）。
- **负侧鉴别器**仍是方法论核心。

**方法论产物**：7 个带真实反例的 AI 数学推理失败模式（见 articles/B）。

**公共事实修正**：2^A=Π(3+1/nᵢ)>3^m（A/m 从上侧逼近 log₂3）；B–S 方程正号形式；log₂3 连分数与收敛子表（k=9 为 24727/15601）；LTE 分奇偶；n₁ 界的正侧专属性。

### 诚实声明

- 全部现代下界（m≥10^10 量级，Simons–de Weger 等）属已知结果，本仓库不冒充新发现。
- 「证明 Collatz」的成功率评估：低个位数。本仓库的现实价值 = 方法论 + 失败模式目录 + 框架可复用性，不是数学宣告。
- 所有数值经本机 Python 大整数验证；所有裁决带反例。

## 仓库结构

```
jinshanmu-framework/
├── README.md                  ← 本文件
├── articles/                  ← 对外文章（中文首发）
│   ├── A-负侧鉴别器.md
│   ├── B-七个死法.md
│   └── C-席位灾备实录.md
├── preset/                    ← DSH agent 预设（可直接安装）
│   ├── preset.yml
│   └── agent.cordis.yml
├── docs/
│   ├── round1-report.md       ← 第 1 轮完整收口报告
│   ├── round2-report.md       ← 第 2 轮收口（R2a 死亡 + R1 存活）
│   ├── routeA/B-round1.md     ← 各路线铺路报告
│   └── basic-verification.md  ← 公共事实核验报告
├── tools/
│   ├── call_deepseek_e.mjs    ← 官方 API 直连脚本（凭据从 .credentials.yaml 读）
│   ├── collatz_verify_r1.py   ← 主持人复核脚本（7 项断言）
│   ├── collatz_r1_sieve.py    ← CF 筛+B–S 整除双筛（第 2 轮主力）
│   └── collatz_r3_dsmall.py   ← |D| 小值穷尽
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

- 第 2 轮：CF 筛机械化推到 m≈10⁶；Baker 主项依赖链；|D| 小值穷尽 → grok 拆台 → 收口。
- 第 3 轮：分岔判定——m-循环约化 φ(m) 通道能否闭合；闭则收证明（≥2 轮攻击+独立终审），否则出山穷水尽报告。

## 作者与披露

人机团队产物：人类主理 + 多模型 agent 管线（DeepSeek V4 Pro/Grok 4.6/MiniMax M3 等），AI 参与全程披露。数学断言不因来源而豁免验证——本仓库的每一条结论都经过攻击手和机器复核。
