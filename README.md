# AI Movie Agent

这是一个学习型 AI Agent 原型，用电影资料管理串起 FastAPI、SQLite、DeepSeek Tool Calling、RAG、Memory、LangGraph、流式输出和 MCP Demo。当前版本以便于继续学习为目标。

## 功能与技术栈

- 电影列表、分页、搜索、筛选和增删改查：FastAPI、Pydantic、SQLite。
- 电影问答和工具调用：DeepSeek API、LangGraph；`/ai/chat` 返回 JSON，`/ai/chat/stream` 返回 NDJSON。
- 会话状态：LangGraph `InMemorySaver`；最近讨论的电影：进程内短期记忆；跨会话偏好：SQLite `user_memory`。
- 知识库检索：sentence-transformers 的 `BAAI/bge-small-zh-v1.5` 模型与 Chroma。
- MCP：本地 stdio 服务端和客户端示例。
- 前端：原生 HTML、CSS、JavaScript。

## 主要文件

```text
main.py                    FastAPI 入口和 HTTP 接口
schemas.py                 请求与响应模型
database.py                SQLite 操作
movie_agent.py             模型客户端、工具注册与执行、Memory 辅助函数
langgraph_movie_agent.py   正式 Agent 流程、Checkpoint、流式事件
rag_service.py             知识库构建与检索
build_knowledge_base.py    知识库构建入口
movie_mcp_server.py        MCP 服务端 Demo
movie_mcp_client.py        MCP 客户端 Demo
logging_config.py          日志配置
knowledge/                 RAG 原始文档
front/                     静态前端
tests/                     基础测试
```

## 本地运行

需要 Python 3.12。首次使用 RAG 时会下载 embedding 模型，需要网络连接；构建知识库后会在本地生成 `chroma_db/`。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

在项目根目录创建 `.env`：

```dotenv
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

启动 API；SQLite 数据库 `movies.db` 会自动初始化：

```powershell
python build_knowledge_base.py
uvicorn main:app --reload
```

浏览器打开 `front/index.html`，前端默认连接 `http://localhost:8000`。API 文档见 `http://localhost:8000/docs`。知识库原始文档有变动时，重新运行 `python build_knowledge_base.py`。

运行测试和 MCP Demo：

```powershell
python -m pytest -q
python movie_mcp_client.py
```

测试使用临时 SQLite 数据库，不写入项目的 `movies.db`。

## Docker 基础运行

```powershell
docker build -t ai-movie-agent .
docker run --rm -p 8000:8000 --env-file .env ai-movie-agent
```

`.env`、`movies.db`、`chroma_db/` 不会进入镜像。容器启动时会创建自己的 SQLite 数据库；如需 RAG 数据，容器内可运行 `python build_knowledge_base.py`。首次运行 RAG 仍需下载模型。

## 后续 TODO

- 为会话 Checkpoint 和短期记忆设计明确的生命周期；目前两者都只存在于单个进程内。
- 在后续学习阶段考虑容器数据持久化，并补充针对 Agent 工具流程的隔离测试。
