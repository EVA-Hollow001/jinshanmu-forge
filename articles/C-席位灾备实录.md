# Agent Plan 额度归零的那天：DSH 多模型席位灾备实录

一场长程多智能体攻坚跑到一半，主 provider 额度耗尽，7 个 subagent 席位死了 5 个。这篇记录怎么在不重启的情况下把整条线救回来，包括踩过的三个坑。所有配置路径都能在 DSH 配置目录里核对。

## 事故经过

攻坚第 1 轮，5 条铺路线的 subagent 陆续报「failed before it finished」，或者回一个空收尾消息。换 GLM、豆包席位重试，一样死。只有 grok（xAI key）和 minimax（key 席位）还活着。

排查结论：**走火山 Agent Plan 的席位全部没余额了**，key 席位完好。这是第一次靠「留一条 key 席位当哨兵」快速定位了是 provider 死而不是网络死。

## 重绑矩阵

| 席位 | 原绑定（死） | 新绑定 | 凭据 |
|---|---|---|---|
| subagent | Agent Plan · deepseek-v4-pro | deepseek-official · deepseek-v4-pro | DEEPSEEK_API_KEY |
| subagent_flash | Agent Plan · deepseek-v4-flash | deepseek-official · deepseek-v4-flash | DEEPSEEK_API_KEY |
| subagent_minimax | Agent Plan · minimax-m3 | minimax-cn · MiniMax-M3 | MINIMAX_CN_API_KEY |
| subagent_glm | Agent Plan · glm-5.3 | volcengine-coding-plan · glm-5-3-260925 | ARK_API_KEY（独立额度） |
| subagent_doubao | Agent Plan · doubao-evolving | volcengine-coding-plan · doubao-2.1-turbo | 同上 |
| subagent_grok / qwen3 | xAI / 百炼 | 不变 | 本来就活 |

改的是 `~/.dsh/.agent-presets/<preset>/agent.cordis.yml` 里每个 tool 行的 `agentOptions.provider/model`。注意生效时机：agent 预设的工具绑定在会话启动时加载，改完要重启或新开会话。重启后 session 文件持久化，攻坚进度没丢，直接续。

## 坑 1：官方 provider 的配置段不叫你以为的那个名字

deepseek-official 不是 settings.yaml 里 `providers` 列表的用户配置，是 `dsh-llm-deepseek` 插件注册的路由，配置段名是 `llm-deepseek`：

```yaml
llm-deepseek:
  thinking: enabled
  reasoningEffort: max
```

这段加上后下一个请求就生效，不用重启（插件按请求解析配置）。另外 spawn 子代理的 `agentOptions` schema 只收 {provider, model, maxTokens}，不收 reasoningEffort，子代理的推理档只能靠这个插件段统一控制。

## 坑 2：max 推理档会吃光 max_tokens

直连 API 时 `max_tokens` 设 16000 跑 max 推理档，16000 个 token 全被 reasoning 吃掉，回答 0 字节。官方 V4 Pro 支持大输出（DSH 里 maxTokens 393216），直连默认给 64000 起步。

## 坑 3：staging 工具沙箱里没有 require

想用 super-injector 的 staging 通道挂一个「DeepSeek 官方直连」工具，沙箱里 `require` 不存在。解法：

- `await import('node:fs')` 可用（ESM 上下文）；
- parameters 要传「属性名 → 值 schema」映射，别套 JSON-Schema 的 `type:"object"` 包装，转正时会报 `parameters.type must be a value schema object`；
- 探针工具用完记得 demote。

最终产出已转正的工具 `deepseek_official_chat`：凭据运行时从 `.credentials.yaml` 读（key 不进聊天、不进命令行），默认 v4-pro + max 推理。

## 灾备清单（下次直接抄）

1. 留一条 key 席位当哨兵，额度死了能立刻分清是 provider 死还是网络死。
2. 主路双 provider：plan 免费额度打头、官方 key 兜底，路由写在预设矩阵里，切起来改一行。
3. 直连兜底：subagent 全死时，一个「读凭据文件 → 官方 API → 写盘」的 50 行 node 脚本就能让攻坚不断粮。脚本在配套仓库 tools/call_deepseek_e.mjs。
4. 重绑后第一条路当冒烟测试。我们用 3-adic 路线验证了新绑定，一次通过。

---

*本文是真实事故记录，AI 参与全程披露。*
