"""监控相关路由"""
from fastapi import APIRouter, Depends, HTTPException, Security
from typing import Dict, Any, List
from ..dependencies import get_monitor, get_config_manager, verify_api_key
from src.core.monitor import BilibiliMonitor
from src.core.config import ConfigManager
import json

router = APIRouter(
    prefix="/monitor",
    tags=["监控管理"],
    dependencies=[Depends(verify_api_key)]
)

@router.get("/status")
async def get_monitor_status(
    monitor: BilibiliMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """获取监控状态"""
    return {
        "monitor_mids": monitor.monitor_mids,
        "check_interval": monitor.check_interval,
        "status_cache": monitor.status_cache
    }

@router.get("/live/{mid}")
async def get_live_status(
    mid: str,
    monitor: BilibiliMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """获取指定UP主的直播状态"""
    status = monitor.check_live_status(mid)
    if not status:
        raise HTTPException(status_code=404, detail="获取直播状态失败")
    return status

@router.get("/subscribers")
async def get_subscribers(
    config: ConfigManager = Depends(get_config_manager)
) -> List[Dict[str, Any]]:
    """获取当前监控列表"""
    monitor_mids = json.loads(config.get('monitor_mids', '[]'))
    result = []
    for mid in monitor_mids:
        status = config.db.get_config(f'last_status_{mid}')
        name = config.db.get_config(f'name_{mid}', '')
        result.append({
            "mid": mid,
            "name": name,
            "status": status
        })
    return result

@router.post("/subscribers/{mid}")
async def add_subscriber(
    mid: str,
    config: ConfigManager = Depends(get_config_manager),
    monitor: BilibiliMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """添加监控用户"""
    try:
        # 验证用户ID是否有效
        status = monitor.check_live_status(mid)
        if not status:
            raise HTTPException(status_code=400, detail="无效的用户ID")
        
        # 获取当前列表
        current_mids = json.loads(config.get('monitor_mids', '[]'))
        
        # 检查是否已存在
        if mid in current_mids:
            return {
                "message": "用户已在监控列表中",
                "name": status.get('name', '未知'),
                "mid": mid
            }
        
        # 添加到列表
        current_mids.append(mid)
        config.set('monitor_mids', json.dumps(current_mids))
        
        # 保存用户名
        config.db.set_config(f'name_{mid}', status.get('name', '未知'))
        
        # 更新监控器的列表
        monitor.monitor_mids = current_mids
        
        return {
            "message": "添加成功",
            "name": status.get('name', '未知'),
            "mid": mid
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的用户ID格式")

@router.delete("/subscribers/{mid}")
async def remove_subscriber(
    mid: str,
    config: ConfigManager = Depends(get_config_manager),
    monitor: BilibiliMonitor = Depends(get_monitor)
) -> Dict[str, str]:
    """移除监控用户"""
    try:
        # 获取当前列表
        current_mids = json.loads(config.get('monitor_mids', '[]'))
        
        # 检查是否存在
        if mid not in current_mids:
            raise HTTPException(status_code=404, detail="用户不在监控列表中")
        
        # 从列表中移除
        current_mids.remove(mid)
        config.set('monitor_mids', json.dumps(current_mids))
        
        # 更新监控器的列表
        monitor.monitor_mids = current_mids
        
        return {"message": f"已移除用户 {mid}"}
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的用户ID格式")

@router.get("/subscribers/{mid}")
async def get_subscriber_info(
    mid: str,
    monitor: BilibiliMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """获取指定用户的详细信息"""
    status = monitor.check_live_status(mid)
    if not status:
        raise HTTPException(status_code=404, detail="获取用户信息失败")
    return status
