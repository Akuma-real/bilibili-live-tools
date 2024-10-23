"""配置相关路由"""
from fastapi import APIRouter, Depends, HTTPException, Security
from typing import Dict, Any
from ..dependencies import get_config_manager, verify_api_key
from src.core.config import ConfigManager
import os
from dotenv import load_dotenv

router = APIRouter(
    prefix="/config",
    tags=["配置管理"],
    dependencies=[Depends(verify_api_key)]  # 添加全局依赖
)

@router.get("/")
async def get_all_configs(
    config: ConfigManager = Depends(get_config_manager)
) -> Dict[str, Any]:
    """获取所有配置"""
    return config.get_all()

@router.get("/bilibili")
async def get_bilibili_config(
    config: ConfigManager = Depends(get_config_manager)
) -> Dict[str, Any]:
    """获取B站相关配置"""
    return config.get_bilibili_config()

@router.get("/cloudflare")
async def get_cloudflare_config(
    config: ConfigManager = Depends(get_config_manager)
) -> Dict[str, Any]:
    """获取Cloudflare配置"""
    return config.get_cloudflare_config()

@router.get("/server_chan")
async def get_server_chan_config(
    config: ConfigManager = Depends(get_config_manager)
) -> Dict[str, Any]:
    """获取Server酱配置"""
    return config.get_server_chan_config()

@router.post("/bilibili/cookies")
async def update_bilibili_cookies(
    cookies: str,
    config: ConfigManager = Depends(get_config_manager)
) -> Dict[str, str]:
    """更新B站cookies"""
    config.update_bilibili_cookies(cookies)
    return {"message": "Cookies更新成功"}

@router.post("/reload")
async def reload_config(
    config: ConfigManager = Depends(get_config_manager)
) -> Dict[str, str]:
    """强制从.env重新加载配置"""
    load_dotenv(override=True)
    config.load_config(force=True)
    return {"message": "配置已重新加载"}
