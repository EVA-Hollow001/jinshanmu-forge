# Agent Plan 归零：DSH 多模型席位灾备实录

> 一场长程多智能体攻坚跑到一半，主 provider 额度耗尽，7 个 subagent 席位死了 5 个。本文记录完整的灾备过程：从「子代理连环阵亡」到「不停机全量重绑」的每一步，包括踩过的三个坑。

## 事故时间线

1. 攻坚第 1 轮，5 条铺路线的 subagent 陆续「failed before it finished」或交付空消息。
2. 换 GLM/豆包席位重试，同样阵亡。只有 grok（xAI key）和 minimax（key 席位）正常。
3. 排查确认：**所有走火山 Agent Plan 的席位全部没有余额了**，key 席位完好。
4. 灾备改造：主路改走 DeepSeek 官方 API，全部席位重绑，零停机。

## 席位重绑矩阵

| 席位 | 原绑定（死） | 新绑定 | 凭据 |
|---|---|---|---|
| subagent | Agent Plan · deepseek-v4-pro | deepseek-official · deepseek-v4-pro | DEEPSEEK_API_KEY |
| subagent_flash | Agent Plan · deepseek-v4-flash | deepseek-official · deepseek-v4-flash | DEEPSEEK_API_KEY |
| subagent_minimax | Agent Plan · minimax-m3 | minimax-cn · MiniMax-M3 | MINIMAX_CN_API_KEY |
| subagent_glm | Agent Plan · glm-5.3 | volcengine-coding-plan · glm-5-3-260925 | ARK_API_KEY（Coding Plan 独立额度） |
| subagent_doubao | Agent Plan · doubao-evolving | volcengine-coding-plan · doubao-2.1-turbo | 同上 |
| subagent_grok / qwen3 | xAI / 百炼 | 不变 | 本来就活 |

修改点：`~/.dsh/.agent-presets/<preset>/agent.cordis.yml` 里每个 tool 行的 `agentOptions.provider/model`。注意**生效时机**：agent 预设的工具绑定在会话启动时加载，改完要重启/新开会话才生效（重启后 sessions 持久化，跑了一半的攻坚可以续）。

## 踩坑 1：settings.yaml 里加 provider 段 ≠ 直接可用

官方 provider（deepseek-official）不是 settings.yaml 里的用户配置，而是 `dsh-llm-deepseek` 插件注册的路由，配置段名是 `llm-deepseek`，不进 `providers` 列表。关键配置：

```yaml
llm-deepseek:
  thinking: enabled
  reasoningEffort: max
```

加了这段后**下一个请求立即生效，无需重启**（插件按请求解析配置）——这是文档里写的 seam，实测有效。但注意：spawn 子代理的 `agentOptions` schema 只收 {provider, model, maxTokens}，**不收 reasoningEffort**，所以子代理的推理档只能靠这个插件段统一控制。

## 踩坑 2：max 推理档会吃光 max_tokens

直连 API 时把 `max_tokens` 设成 16000 跑 max 推理档，结果 16000 个 token 全被 reasoning 吃掉，**回答 0 字节**。官方 V4 Pro 支持大输出（DSH 配置里 maxTokens 393216），直连要留够：默认 64000 起步。

## 踩坑 3：staging 工具沙箱没有 require

想用 super-injector 的 staging 通道挂一个「DeepSeek 官方直连」工具，沙箱里 `require` 不存在。解法：

- `await import('node:fs')` 可用（ESM 上下文）；
- parameters 要用「属性名→值 schema」映射，不要 JSON-Schema 的 `type:"object"` 包装（转正时会报 `parameters.type must be a value schema object`）；
- 探针工具记得 demote 掉，别留在 staging。

最终产出一个已转正的工具 `deepseek_official_chat`：凭据运行时从 `.credentials.yaml` 读（key 不进聊天、不进命令行），默认 v4-pro + max 推理。

## 可复用的灾备清单

1. **永远留一条 key 席位做哨兵**：额度死了 key 席位能立刻定位是「provider 死」还是「网络死」。
2. **主路要有双 provider**：plan（免费额度）打头、官方 key 兜底，路由写在预设矩阵里，改一行就能切。
3. **直连工具兜底**：subagent 全死时，一个「读凭据文件→官方 API→写盘」的 50 行 node 脚本就能让攻坚不断粮。
4. **恢复验证**：重绑后第一条路就当冒烟测试（我们拿 3-adic 路线验证了新绑定）。

## 附件

- 直连脚本与工具源码见配套仓库 `tools/`；
- 预设重绑 diff 见 `docs/seat-failover.md`。

*本文记录的是真实事故处理，所有 provider/模型名与配置路径均可在 DSH 配置目录核对。*
