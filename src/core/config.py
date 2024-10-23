"""配置管理模块"""
from typing import Any, Dict
import json
from loguru import logger
import os
from dotenv import load_dotenv
import time

class ConfigManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.config_cache = {}
        self.last_load_time = 0
        self.load_config()

    def load_config(self, force=False) -> None:
        """从.env文件和数据库加载配置
        
        Args:
            force: 是否强制重新加载
        """
        current_time = time.time()
        # 如果距离上次加载不到1秒，且不是强制加载，则跳过
        if not force and (current_time - self.last_load_time) < 1:
            return
            
        # 更新加载时间
        self.last_load_time = current_time
        
        # 从.env加载配置
        load_dotenv(override=True)
        
        # 从环境变量读取配置
        env_configs = {
            'cloudflare_domain': os.getenv('CLOUDFLARE_DOMAIN', ''),
            'cloudflare_auth_code': os.getenv('CLOUDFLARE_AUTH_CODE', ''),
            'server_chan_key': os.getenv('SERVER_CHAN_KEY', ''),
            'bilibili_cookies': os.getenv('BILIBILI_COOKIES', ''),
            'monitor_mids': os.getenv('MONITOR_MIDS', '[]'),
            'check_interval': os.getenv('CHECK_INTERVAL', '60')
        }
        
        # 检查配置是否有变化
        changed = False
        for key, value in env_configs.items():
            if value and self.config_cache.get(key) != value:
                changed = True
                self.config_cache[key] = value
                self.db.set_config(key, value)
                logger.debug(f"从.env更新配置: {key}")
        
        if changed:
            logger.info("配置已更新")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        self.load_config()  # 自动检查是否需要重新加载
        return self.config_cache.get(key, default)

    def set(self, key: str, value: str) -> None:
        """设置配置值"""
        self.config_cache[key] = value
        self.db.set_config(key, value)

    def get_all(self) -> Dict[str, str]:
        """获取所有配置"""
        self.load_config()  # 确保配置是最新的
        return self.config_cache.copy()

    def get_bilibili_config(self) -> Dict[str, Any]:
        """获取B站相关配置"""
        self.load_config()  # 确保配置是最新的
        return {
            'monitor_mids': json.loads(self.get('monitor_mids', '[]')),
            'check_interval': int(self.get('check_interval', '60')),
            'cookies': self.get('bilibili_cookies')
        }

    def get_cloudflare_config(self) -> Dict[str, str]:
        """获取Cloudflare配置"""
        self.load_config()  # 确保配置是最新的
        return {
            'domain': self.get('cloudflare_domain', ''),
            'auth_code': self.get('cloudflare_auth_code', '')
        }

    def get_server_chan_config(self) -> Dict[str, str]:
        """获取Server酱配置"""
        self.load_config()  # 确保配置是最新的
        return {
            'sendkey': self.get('server_chan_key', '')
        }

    def update_bilibili_cookies(self, cookies_str: str) -> None:
        """更新B站cookies"""
        self.set('bilibili_cookies', cookies_str)
        logger.info("B站cookies已更新")

    def validate_config(self) -> bool:
        """验证配置完整性"""
        self.load_config(force=True)  # 强制重新加载以确保配置正确
        
        required_configs = {
            'cloudflare_domain': '图床域名',
            'cloudflare_auth_code': '图床认证码',
            'server_chan_key': 'Server酱密钥',
            'bilibili_cookies': 'B站cookies',
            'monitor_mids': '监控列表'
        }
        
        missing = []
        for key, name in required_configs.items():
            if not self.get(key):
                missing.append(name)
        
        if missing:
            logger.warning(f"缺少必要配置: {', '.join(missing)}")
            return False
        return True
