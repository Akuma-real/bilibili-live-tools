"""项目初始化工具"""
import os
import shutil
from loguru import logger
from src.core.database import DatabaseManager
from dotenv import load_dotenv
import sys

def init_project():
    """初始化项目目录结构"""
    # 首先移除默认的日志处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=os.getenv('LOG_LEVEL', 'INFO'),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}"
    )
    
    directories = {
        'data': '数据存储',
        'logs': '日志文件',
        'temp': '临时文件'
    }
    
    # 确保目录存在并有正确的权限
    for dir_name, description in directories.items():
        path = os.path.join(os.getcwd(), dir_name)
        os.makedirs(path, exist_ok=True)
        # 设置目录权限
        os.chmod(path, 0o777)
        logger.info(f"创建目录: {dir_name}/ ({description})")
    
    # 配置文件日志
    log_file = os.path.join('logs', 'monitor_{time:YYYY-MM-DD}.log')
    try:
        logger.add(
            log_file,
            rotation="00:00",  # 每天轮换
            retention="7 days",  # 保留7天
            level=os.getenv('LOG_LEVEL', 'INFO'),
            encoding='utf-8',
            enqueue=True,  # 异步写入
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}"
        )
    except Exception as e:
        logger.error(f"配置日志文件失败: {str(e)}")
        # 继续运行，但只使用控制台输出
    
    # 创建 .env 文件（仅当不存在时）
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            shutil.copy2('.env.example', '.env')
            logger.info("创建配置文件: .env")
        else:
            logger.warning("未找到 .env.example 文件")
    
    # 初始化数据库
    db = DatabaseManager(os.path.join('data', 'database.db'))
    
    # 从环境变量加载配置
    load_dotenv()
    
    # 设置配置（仅当数据库中不存在时）
    configs = {
        'cloudflare_domain': os.getenv('CLOUDFLARE_DOMAIN', ''),
        'cloudflare_auth_code': os.getenv('CLOUDFLARE_AUTH_CODE', ''),
        'server_chan_key': os.getenv('SERVER_CHAN_KEY', ''),
        'bilibili_cookies': os.getenv('BILIBILI_COOKIES', ''),
        'monitor_mids': os.getenv('MONITOR_MIDS', '[]'),
        'check_interval': os.getenv('CHECK_INTERVAL', '60')
    }
    
    # 仅设置不存在的配置
    for key, value in configs.items():
        if value and not db.get_config(key):  # 只在值不为空且数据库中不存在时设置
            db.set_config(key, value)
            logger.debug(f"设置初始配置: {key}")
    
    logger.info("项目初始化完成")

if __name__ == "__main__":
    init_project()
