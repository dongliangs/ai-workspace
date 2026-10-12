# Agent 模块包
#
# 不在此自动导入 tools 子模块。
# 工具注册应在应用启动时显式执行（如 main.py 或 agent_service.py），
# 这样可以清晰控制哪些工具可用，也便于测试时注入 mock 工具。
