Movie Agent 使用 Tool Calling 查询真实电影数据。DeepSeek 负责选择工具和生成工具参数，Python 程序负责真正执行函数。

user_id 表示一个用户，用于长期 Memory。session_id 表示一场聊天，用于 Conversation State 和 Short-term Memory。

长期 Memory 当前保存在 SQLite 的 user_memory 表中。

update_user_memory 是一个有副作用的 Tool，因为它会修改数据库。

为了避免模型决定修改哪个用户的数据，user_id 不由模型生成，而是由 Python 从可信请求上下文中自动注入。