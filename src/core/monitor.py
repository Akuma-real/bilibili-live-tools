from ..utils.screenshot import LiveScreenshot
import time
import os
from src.core.database import DatabaseManager
from src.core.config import ConfigManager
from loguru import logger
import json
import requests
import random
from ..utils.notifier import LiveNotifier
from datetime import datetime
import sys
from typing import Dict, Any

class BilibiliMonitor:
    def __init__(self):
        # 首先定义数据库文件路径
        self.db_file = os.path.join('data', 'database.db')
        
        # 创建必要的目录
        os.makedirs('data', exist_ok=True)
        os.makedirs('temp', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # 配置日志 - 修改为每天一个文件
        log_path = os.path.join("logs", "monitor_{time:YYYY-MM-DD}.log")
        # 移除之前的所有处理器
        logger.remove()
        # 添加新的文件处理器
        logger.add(
            log_path,
            rotation="00:00",  # 每天午夜轮转
            retention="7 days",  # 保留7天的日志
            level=os.getenv('LOG_LEVEL', 'INFO'),
            encoding='utf-8',
            enqueue=True,  # 异步写入
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}"
        )
        # 添加控制台输出
        logger.add(
            sys.stderr,
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}"
        )
        
        # 初始化数据库
        self.db_manager = DatabaseManager(self.db_file)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager(self.db_manager)
        
        # 验证配置
        if not self.config_manager.validate_config():
            raise Exception("配置不完整，请检查配置")
        
        # 获取配置
        bilibili_config = self.config_manager.get_bilibili_config()
        self.monitor_mids = bilibili_config['monitor_mids']
        self.check_interval = bilibili_config['check_interval']
        self.cookies = bilibili_config['cookies']
        
        # 添加新的配置项
        self.retry_delay = 10  # 重试等待时间（秒
        self.between_checks_delay = 5  # UP主之间的检查间隔（秒）
        
        # 添加截图间隔配置
        self.screenshot_interval = int(os.getenv('SCREENSHOT_INTERVAL', '3600'))  # 默认1小时
        self.last_screenshot_times = {}  # 记录每个主播的上次截图时间
        
        logger.info(f"初始化完成，监控配置：")
        logger.info(f"- 监控列表：{self.monitor_mids}")
        logger.info(f"- 检查间隔：{self.check_interval}秒")
        logger.info(f"- 重试延迟：{self.retry_delay}秒")
        logger.info(f"- 截图间隔：{self.screenshot_interval}秒")
        
        # 初始化其他组件
        self.screenshot = LiveScreenshot()
        
        # 修改请求会话的初始化 - 不使用cookie
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })
        
        # 添加状态缓存
        self.status_cache = {}
        
        # 初始化通知器
        server_chan_config = self.config_manager.get_server_chan_config()
        self.notifier = LiveNotifier(server_chan_config['sendkey'])
        
        # 初始化图片上传器
        cloudflare_config = self.config_manager.get_cloudflare_config()
        from ..utils.uploader import ImageUploader  # 添加导入
        self.uploader = ImageUploader(cloudflare_config)
        
    def check_live_status(self, mid: str, retry_count=3) -> Dict[str, Any]:
        """检查直播状态"""
        for attempt in range(retry_count):
            try:
                if attempt > 0:
                    delay = self.retry_delay + random.uniform(0, 3)
                    logger.debug(f"第{attempt + 1}次重试，等待{delay:.1f}秒")
                    time.sleep(delay)
                
                url = f'https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids'
                referer = 'https://live.bilibili.com'
                
                logger.debug(f"请求API: {url} (uid: {mid})")
                
                response = self.session.post(
                    url,
                    json={'uids': [int(mid)]},
                    timeout=10,
                    headers={
                        'Referer': referer,
                        'Origin': 'https://live.bilibili.com'
                    }
                )
                
                data = response.json()
                
                if data['code'] == 0 and 'data' in data:
                    user_data = data['data'].get(str(mid), {})
                    status_info = {
                        'status': user_data.get('live_status', 0),
                        'room_id': user_data.get('room_id', 0),
                        'title': user_data.get('title', ''),
                        'name': user_data.get('uname', ''),
                        'timestamp': time.time()
                    }
                    
                    # 更新状态缓存
                    self.status_cache[mid] = status_info
                    logger.debug(f"获取状态成功: {status_info}")
                    return status_info
                else:
                    logger.warning(f"API返回异常: {data}")
                    if data['code'] in [-352, -412, -799]:  # 风控、请求过快
                        continue
                
            except Exception as e:
                logger.error(f"检查直播状态失败: {str(e)}")
                if attempt < retry_count - 1:
                    continue
        
        # 如果所有重试都失败了，返回缓存的状态
        if mid in self.status_cache:
            cache_time = time.time() - self.status_cache[mid]['timestamp']
            if cache_time < 300:  # 缓存时间小于5分钟
                logger.info(f"使用缓存的状态（{cache_time:.0f}秒前）")
                return self.status_cache[mid]
        
        return None

    def check_multiple_live_status(self, mids, retry_count=3):
        """批量检查直播状态"""
        for attempt in range(retry_count):
            try:
                if attempt > 0:
                    delay = self.retry_delay + random.uniform(0, 3)
                    logger.debug(f"第{attempt + 1}次重试，等待{delay:.1f}秒")
                    time.sleep(delay)
                
                url = 'https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids'
                referer = 'https://live.bilibili.com'
                
                # 转换所有mid为整数
                uid_list = [int(mid) for mid in mids]
                logger.debug(f"批量请求API: {url} (uids: {uid_list})")
                
                response = self.session.post(
                    url,
                    json={'uids': uid_list},
                    timeout=10,
                    headers={
                        'Referer': referer,
                        'Origin': 'https://live.bilibili.com'
                    }
                )
                
                data = response.json()
                
                if data['code'] == 0 and 'data' in data:
                    result = {}
                    for mid, user_data in data['data'].items():
                        status_info = {
                            'status': user_data.get('live_status', 0),
                            'room_id': user_data.get('room_id', 0),
                            'title': user_data.get('title', ''),
                            'name': user_data.get('uname', ''),
                            'timestamp': time.time()
                        }
                        result[mid] = status_info
                        self.status_cache[mid] = status_info
                    
                    # 修改日志格式，让它更易读
                    log_info = "\n".join([
                        f"[{info['name']}] 状态: {'直播中' if info['status'] == 1 else '未直播'}, "
                        f"标题: {info['title']}"
                        for mid, info in result.items()
                    ])
                    logger.debug(f"批量获取状态成功:\n{log_info}")
                    return result
                else:
                    logger.warning(f"API返回异常: {data}")
                    if data['code'] in [-352, -412, -799]:  # 风控、请求过快
                        continue
                
            except Exception as e:
                logger.error(f"批量检查状态失败: {str(e)}")
                if attempt < retry_count - 1:
                    continue
        
        # 如果所有重试都失败了，返回缓存的状态
        result = {}
        for mid in mids:
            if mid in self.status_cache:
                cache_time = time.time() - self.status_cache[mid]['timestamp']
                if cache_time < 300:  # 缓存时间小于5分钟
                    logger.info(f"使用缓存的状态（{cache_time:.0f}秒前）: {mid}")
                    result[mid] = self.status_cache[mid]
        
        return result if result else None

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

    def handle_screenshot(self, mid: str, live_status: dict) -> None:
        """处理直播截图
        
        Args:
            mid: UP主ID
            live_status: 直播状态信息
        """
        current_time = time.time()
        last_time = self.last_screenshot_times.get(mid, 0)
        
        # 判断是否需要截图
        need_screenshot = (
            # 从未截图
            last_time == 0 or
            # 达到截图间隔
            (current_time - last_time) >= self.screenshot_interval
        )
        
        if need_screenshot:
            logger.info(f"开始获取直播截图: {live_status['name']}")
            
            # 获取截图
            screenshot_file, success = self.screenshot.capture(
                live_status['room_id'],
                self.cookies
            )
            
            if success and screenshot_file:
                try:
                    # 获取直播信息
                    live_info = self.notifier.get_live_info(live_status['room_id'])
                    live_time = live_info.get('live_time', '')
                    duration = self.get_live_duration(live_time)
                    
                    # 上传截图
                    image_url = self.uploader.upload_screenshot(screenshot_file)
                    
                    if image_url:
                        logger.info(f"截图上传成功: {image_url}")
                        
                        # 更新数据库
                        self.last_screenshot_times[mid] = current_time
                        live_id = self.db_manager.get_current_live_id(mid)
                        if live_id:
                            self.db_manager.add_screenshot(live_id, image_url)
                        
                        # 发送截图通知
                        title = f"📸 直播截图：{live_status['name']}"
                        content = (
                            f"# {live_status['name']} 的直播截图\n\n"
                            f"## 📺 直播信息\n\n"
                            f"- 📝 标题：**{live_status['title']}**\n"
                            f"- 🏠 房间号：**{live_status['room_id']}**\n"
                            f"- ⏰ 开播时间：**{live_time}**\n"
                            f"- ⌛ 已播时长：**{duration}**\n"
                            f"- 🔗 直播间：[点击进入直播间](https://live.bilibili.com/{live_status['room_id']})\n\n"
                            f"## 🖼️ 直播画面\n\n"
                            f"![直播画面]({image_url})\n\n"
                            "---\n"
                            "*由 Bilibili Live Monitor 自动发送*"
                        )
                        
                        self.notifier.notifier.send(
                            title=title,
                            content=content,
                            short=f"{live_status['name']} 直播截图"
                        )
                        
                finally:
                    # 清理临时文件
                    try:
                        if os.path.exists(screenshot_file):
                            os.remove(screenshot_file)
                            logger.debug(f"已删除临时文件: {screenshot_file}")
                    except Exception as e:
                        logger.error(f"删除临时文件失败: {str(e)}")

    def run(self):
        """运行监控循环"""
        while True:
            try:
                # 更新监控列表
                self.update_monitor_list()
                
                # 遍历监控列表
                for mid in self.monitor_mids:
                    # 获取当前状态
                    live_status = self.check_live_status(mid)
                    if not live_status:
                        logger.warning(f"获取直播状态失败: {mid}")
                        continue
                    
                    # 获取上次状态
                    last_status_str = self.db_manager.get_config(f'last_status_{mid}')
                    last_status = int(last_status_str) if last_status_str is not None else 0
                    
                    # 获取当前状态
                    current_status = int(live_status.get('status', 0))
                    
                    # 更新状态缓存
                    self.status_cache[mid] = {
                        'status': current_status,
                        'room_id': live_status.get('room_id'),
                        'title': live_status.get('title'),
                        'name': live_status.get('name'),
                        'timestamp': time.time() + self.check_interval
                    }
                    
                    # 如果状态发生变化
                    if current_status != last_status:
                        if current_status == 1:
                            # 开播通知
                            self.notifier.notify_live_start(
                                name=live_status['name'],
                                room_id=live_status['room_id'],
                                title=live_status['title']
                            )
                            
                            logger.info(f"[开播] {live_status['name']} ({mid})")
                            self.db_manager.add_live_record(
                                mid=mid,
                                room_id=live_status['room_id'],
                                title=live_status['title']
                            )
                        else:
                            # 下播通知
                            self.notifier.notify_live_end(
                                name=live_status['name'],
                                room_id=live_status['room_id'],
                                title=live_status['title']
                            )
                            
                            logger.info(f"[下播] {live_status['name']} ({mid})")
                            self.db_manager.update_live_status(mid, status=0)
                            
                            # 下播时清除截图时间记录
                            self.last_screenshot_times.pop(mid, None)
                        
                        self.db_manager.set_config(f'last_status_{mid}', str(current_status))
                    
                    # 如果正在直播，检查是否需要定时截图
                    elif current_status == 1:
                        current_time = time.time()
                        last_time = self.last_screenshot_times.get(mid, 0)
                        
                        # 只在达到截图间隔时才截图
                        if (current_time - last_time) >= self.screenshot_interval:
                            self.handle_screenshot(mid, live_status)
            
                # 等待下次检查
                logger.debug(f"等待 {self.check_interval} 秒后进行下次检查")
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"监控循环出错: {str(e)}")
                time.sleep(10)  # 出错后等待10秒再继续

    # 在 BilibiliMonitor 类中添加方法
    def update_monitor_list(self):
        """更新监控列表"""
        try:
            # 从数据库获取最新的监控列表
            monitor_mids = json.loads(self.config_manager.get('monitor_mids', '[]'))
            self.monitor_mids = monitor_mids
            logger.info(f"监控列表已更新: {self.monitor_mids}")
        except Exception as e:
            logger.error(f"更新监控列表失败: {str(e)}")

