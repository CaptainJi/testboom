from src.config.settings import settings

def test_settings():
    """测试配置加载"""
    print("基础配置:")
    print(f"应用名称: {settings.APP_NAME}")
    print(f"应用版本: {settings.APP_VERSION}")
    print(f"调试模式: {settings.DEBUG}")
    print()
    
    print("AI配置:")
    print(f"API密钥: {'已设置' if settings.ai.ZHIPU_API_KEY else '未设置'}")
    print(f"对话模型: {settings.ai.ZHIPU_MODEL_CHAT}")
    print(f"视觉模型: {settings.ai.ZHIPU_MODEL_VISION}")
    print()
    
    print("日志配置:")
    print(f"日志级别: {settings.log.LOG_LEVEL}")
    print(f"日志文件: {settings.log.LOG_FILE}")
    print()
    
    print("数据库配置:")
    print(f"数据库URL: {settings.db.DB_URL}")
    print(f"SQL打印: {settings.db.DB_ECHO}")

if __name__ == "__main__":
    test_settings() 