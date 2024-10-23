"""项目初始化工具"""
import os
import shutil
from loguru import logger
from src.core.database import DatabaseManager
from dotenv import load_dotenv

def init_project():
    """初始化项目目录结构"""
    directories = {
        'data': '数据存储',
        'logs': '日志文件',
        'temp': '临时文件'
    }
    
    for dir_name, description in directories.items():
        os.makedirs(dir_name, exist_ok=True)
        logger.info(f"创建目录: {dir_name}/ ({description})")
    
    # 创建 .env 文件
    if not os.path.exists('.env'):
        shutil.copy2('.env.example', '.env')
        logger.info("创建配置文件: .env")
    
    # 初始化数据库和默认配置
    db = DatabaseManager(os.path.join('data', 'database.db'))
    
    # 从环境变量加载配置
    load_dotenv()
    
    # 设置所有配置
    configs = {
        'cloudflare_domain': os.getenv('CLOUDFLARE_DOMAIN', ''),
        'cloudflare_auth_code': os.getenv('CLOUDFLARE_AUTH_CODE', ''),
        'server_chan_key': os.getenv('SERVER_CHAN_KEY', ''),
        'bilibili_cookies': os.getenv('BILIBILI_COOKIES', ''),  # 添加B站cookies
        'monitor_mids': os.getenv('MONITOR_MIDS', '[]'),  # 添加监控列表
        'check_interval': os.getenv('CHECK_INTERVAL', '60')
    }
    
    # 设置配置到数据库
    for key, value in configs.items():
        if value:  # 只设置非空值
            db.set_config(key, value)
            logger.debug(f"设置配置: {key}")
    
    logger.info("项目初始化完成")
    
    # 检查必要配置
    missing_configs = []
    required_configs = {
        'cloudflare_domain': '图床域名',
        'cloudflare_auth_code': '图床认证码',
        'server_chan_key': 'Server酱密钥',
        'bilibili_cookies': 'B站cookies',
        'monitor_mids': '监控列表'
    }
    
    for key, name in required_configs.items():
        if not db.get_config(key):
            missing_configs.append(name)
    
    if missing_configs:
        logger.warning(f"请在 .env 文件中设置以下配置: {', '.join(missing_configs)}")

if __name__ == "__main__":
    init_project()
