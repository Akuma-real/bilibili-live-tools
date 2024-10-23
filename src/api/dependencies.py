"""依赖注入"""
from fastapi import Request, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from src.core.config import ConfigManager
from src.core.monitor import BilibiliMonitor
import os

# 创建API密钥头部验证器
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(
    api_key: str = Security(api_key_header),
    request: Request = None
) -> str:
    """验证API密钥"""
    correct_api_key = os.getenv("API_KEY", "")
    if not correct_api_key:
        raise HTTPException(
            status_code=500,
            detail="API密钥未配置"
        )
    if api_key != correct_api_key:
        raise HTTPException(
            status_code=403,
            detail="无效的API密钥"
        )
    return api_key

def get_config_manager(
    request: Request,
    api_key: str = Security(verify_api_key)
) -> ConfigManager:
    """获取配置管理器实例"""
    return request.app.state.config_manager

def get_monitor(
    request: Request,
    api_key: str = Security(verify_api_key)
) -> BilibiliMonitor:
    """获取监控实例"""
    return request.app.state.monitor
