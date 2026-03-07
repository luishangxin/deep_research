# 目标：从零复现 DeerFlow Agent Backend 架构

你是一位顶级 Python 后端与 Agent 架构师。你需要使用 Python 3.12+ 和 `uv` 包管理器搭建一个包含 "多层中间件的 LangGraph Agent" 与 "FastAPI 网关" 的双服务后端系统。请按照以下架构约束和实现步骤生成代码：

## 1. 基础配置与依赖 (pyproject.toml)
请配置以下核心依赖库：
`fastapi`, `uvicorn`, `langgraph`, `langchain`, `langchain-mcp-adapters`, `sse-starlette`, `pydantic`, `pyyaml`
项目的入口配置管理需要依赖两份文件：
- [config.yaml](cci:7://file:///Users/liushangxin/work/deep_research/config.yaml:0:0-0:0): 管理所有基建配置 (模型路径定义、支持的 Tool 列表、是否打开记忆、降级策略等)。
- `extensions_config.json`: 管理第三方插件 (如 MCP Server 清单、动态插拔的独立 Skills/Prompt清单)。

## 2. 目录结构约束 (src/)
实现代码放置在 `src/` 中，请构建以下模块：
- `src/agents/lead_agent/`: 主 Agent 逻辑所在，使用 LangGraph 状态图构建单一核心流。在进入大语言模型前，需实现责任链模式 (Middleware Chain) 处理各种周边工作状态。
- `src/gateway/`: FastAPI 的挂载点，提供纯 RESTful (提供配置读取 / 各种 CRUD) 接口并开放给前端。
- `src/sandbox/`: 设计一个抽象的沙盒类（具备 `execute_command`, `read_file`, `write_file`），实现一个底层映射本地特定工作目录的 `LocalSandboxProvider` 子类来实现线程隔离的虚拟文件路径执行。
- `src/mcp/`: 集成 `langchain-mcp-adapters/MultiServerMCPClient`，基于配置文件热更新所有的 MCP Server Tool。
- `src/subagents/`: 定义后台多线程池逻辑。创建一个 `task(description, subagent_type)` 的 Tool 允许主 Agent 调度后端并行的 Agent 协程执行子任务，执行进度采用推拉结合的方式更新给主会话。

## 3. 核心机制要求
请在生成代码时确保实现如下核心系统：
1. **ThreadState 设计**: 扩展标准的 `AgentState`，额外包含字典和列表字段以便处理局部沙盒、TODO清单(Plan Mode)、视觉缓存和文件上传表。
2. **中间件队列机制**: 必须在实际调用 LLM 的 `_call_model` 节点前依次实现以下函数或高阶方法链：
   - 上下文/防溢出清洗: （摘要截断中间件）
   - 沙盒生命周期注入: （为本次调度锁定沙盒句柄） 
   - Token/Memory 持久化: （如果触发生成，则后台抛协程进行 Facts 事实化提取到 memory.json）
   - 反向拦截澄清: （强制捕获 `ask_clarification` Tool 的返回或错误异常并终结当前流程至 `END` 等待用户回复）。
3. **Gateway 和 LangGraph 的分离**: 确保 [langgraph.json](cci:7://file:///Users/liushangxin/work/deer-flow/backend/langgraph.json:0:0-0:0) 直接能起服务，FastAPI (`python -m src.gateway.app`) 和主 Agent 通信不互斥可解耦，且 Gateway 不直接处理复杂的 LangGraph SSE 流，留给 Nginx 代理直接转发给 Agent 进程。
4. **反射工厂 (Reflection System)**: 模型和底层 Tool 允许在 [config.yaml](cci:7://file:///Users/liushangxin/work/deer-flow/config.yaml:0:0-0:0) 定义类似于 `"langchain_openai:ChatOpenAI"` 这样的字符串依赖。要求自行实现一个 `resolve_class` 函数去动态加载对应的包并按需实例化。

## 输出要求
请先梳理架构依赖及各个模块初始化顺序的启动脚本 (如 Makefile/README)，接着输出基础的 `State` 定义、主控 `factory.py` (反射工厂构建模型)、以及 `lead_agent.py` 的精简但完整的图构建代码 (使用 `StateGraph`)。
