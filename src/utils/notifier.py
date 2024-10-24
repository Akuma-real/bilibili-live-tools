"""通知模块"""
import requests
from loguru import logger
from typing import Dict, Any
from datetime import datetime
import time
import os
from src.core.database import DatabaseManager

class ServerChanNotifier:
    """Server酱通知器"""
    def __init__(self, sendkey: str):
        self.sendkey = sendkey
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        })
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """发送通知
        
        Args:
            title: 通知标题
            content: 通知内容（支持markdown）
            **kwargs: 其他参数，如 short（消息卡片内容）
            
        Returns:
            bool: 是否发送成功
        """
        retry_count = 3  # 添加重试次数
        retry_delay = 5  # 重试延迟（秒）
        
        for attempt in range(retry_count):
            try:
                if not self.sendkey:
                    logger.warning("未配置Server酱密钥，跳过通知发送")
                    return False
                
                # 修改URL格式
                url = f"https://sctapi.ftqq.com/{self.sendkey}.send"
                
                data = {
                    'title': title,
                    'desp': content,
                }
                
                # 添加可选参数
                if 'short' in kwargs:
                    data['short'] = kwargs['short']
                
                response = self.session.post(
                    url,
                    json=data,
                    timeout=30  # 增加超时时间
                )
                result = response.json()
                
                if result.get('code') == 0:
                    logger.info(f"Server酱通知发送成功: {title}")
                    return True
                else:
                    error_msg = f"Server酱通知发送失败: {result}"
                    if attempt < retry_count - 1:  # 如果不是最后一次尝试
                        logger.warning(f"{error_msg}，将在{retry_delay}秒后重试")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(error_msg)
                    return False
                    
            except Exception as e:
                error_msg = f"Server酱通知发送出错: {str(e)}"
                if attempt < retry_count - 1:  # 如果不是最后一次尝试
                    logger.warning(f"{error_msg}，将在{retry_delay}秒后重试")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(error_msg)
                return False

class LiveNotifier:
    """直播通知管理器"""
    def __init__(self, server_chan_key: str):
        """初始化通知管理器
        
        Args:
            server_chan_key: Server酱密钥
        """
        self.notifier = ServerChanNotifier(server_chan_key)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
    
    def get_live_info(self, room_id: int) -> Dict[str, Any]:
        """获取直播间信息"""
        try:
            url = "https://api.live.bilibili.com/room/v1/Room/get_info"
            params = {'room_id': room_id}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data['code'] == 0 and 'data' in data:
                return {
                    'cover': data['data'].get('user_cover', ''),
                    'keyframe': data['data'].get('keyframe', ''),
                    'title': data['data'].get('title', ''),
                    'live_time': data['data'].get('live_time', '')
                }
            else:
                logger.warning(f"获取直播间信息失败: {data}")
                
        except Exception as e:
            logger.error(f"获取直播间信息失败: {str(e)}")
        return {}
    
    def get_live_duration(self, start_time: str) -> str:
        """计算直播时长
        
        Args:
            start_time: 开播时间字符串
            
        Returns:
            str: 格式化的时长字符串
        """
        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            duration = datetime.now() - start
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            return f"{int(hours)}小时{int(minutes)}分钟"
        except:
            return "未知"
    
    def notify_live_start(self, name: str, room_id: int, title: str) -> bool:
        """发送开播通知"""
        # 获取直播间信息
        live_info = self.get_live_info(room_id)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        live_time = live_info.get('live_time', current_time)
        
        title_text = f"🔴直播通知：{name} 开播啦！"
        content = (
            f"# {name} 开播啦！\n\n"
            f"## 📺 直播信息\n\n"
            f"- 📝 标题：**{title}**\n"
            f"- 🏠 房间号：**{room_id}**\n"
            f"- ⏰ 开播时间：**{live_time}**\n"
            f"- 🔗 直播间：[点击进入直播间](https://live.bilibili.com/{room_id})\n\n"
        )
        
        # 优先使用关键帧，如果没有则使用封面
        image_url = live_info.get('keyframe') or live_info.get('cover')
        if image_url:
            content += f"## 🖼️ 直播画面\n\n![直播画面]({image_url})\n\n"
        
        content += (
            "## 🎮 操作指引\n\n"
            "点击上方直播间链接即可前往观看直播！\n\n"
            "---\n"
            "*由 Bilibili Live Monitor 自动发送*"
        )
        
        short = f"{name} 开播了：{title}"
        return self.notifier.send(
            title=title_text,
            content=content,
            short=short
        )
    
    def notify_live_end(self, name: str, room_id: int, title: str) -> bool:
        """发送下播通知"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 获取直播信息
        live_info = self.get_live_info(room_id)
        # 从数据库获取开播时间,以防API获取失败
        db = DatabaseManager(os.path.join('data', 'database.db'))
        live_record = db.get_current_live_record(room_id)
        
        # 优先使用数据库中的开播时间
        live_time = ''
        if live_record and live_record.get('start_time'):
            live_time = live_record['start_time']
        elif live_info.get('live_time'):
            live_time = live_info['live_time']
        
        duration = "未知"
        if live_time:
            try:
                start = datetime.strptime(live_time, "%Y-%m-%d %H:%M:%S")
                duration = datetime.now() - start
                hours = duration.total_seconds() // 3600
                minutes = (duration.total_seconds() % 3600) // 60
                duration = f"{int(hours)}小时{int(minutes)}分钟"
            except Exception as e:
                logger.error(f"计算直播时长失败: {str(e)}")
                duration = "未知"
        
        title_text = f"⭕直播结束：{name} 下播了"
        content = (
            f"# {name} 的直播已结束\n\n"
            f"## 📺 直播信息\n\n"
            f"- 📝 标题：**{title}**\n"
            f"- 🏠 房间号：**{room_id}**\n"
            f"- ⏰ 开播时间：**{live_time}**\n"
            f"- ⌛ 直播时长：**{duration}**\n"
            f"- 🕐 下播时间：**{current_time}**\n"
            f"- 🔗 主页：[{name} 的直播间](https://live.bilibili.com/{room_id})\n\n"
            "---\n"
            "*由 Bilibili Live Monitor 自动发送*"
        )
        
        short = f"{name} 的直播已结束（直播了{duration}）"
        return self.notifier.send(
            title=title_text,
            content=content,
            short=short
        )
