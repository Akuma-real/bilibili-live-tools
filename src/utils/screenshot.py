"""截图模块"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import time
import os
from datetime import datetime
from loguru import logger

class LiveScreenshot:
    def __init__(self):
        self.chrome_options = self._init_chrome_options()

    def _init_chrome_options(self):
        """初始化Chrome选项"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.binary_location = '/usr/bin/chromium-browser'  # Alpine中的Chrome位置
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-webgl')
        options.add_argument('--autoplay-policy=no-user-gesture-required')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # 添加自动播放策略
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_setting_values.notifications": 1
        })
        
        return options

    def _parse_cookies(self, cookies_str: str) -> list:
        """解析cookie字符串为列表"""
        cookies = []
        if not cookies_str:
            return cookies
            
        for cookie in cookies_str.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.bilibili.com'
                })
        return cookies

    def capture(self, room_id: int, cookies_str: str) -> tuple:
        """获取直播间截图
        
        Args:
            room_id: 直播间ID
            cookies_str: B站cookies字符串
            
        Returns:
            tuple: (临时文件路径, 是否成功)
        """
        driver = None
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            
            # 访问直播间
            url = f'https://live.bilibili.com/{room_id}'
            driver.get(url)
            
            # 设置cookies
            cookies = self._parse_cookies(cookies_str)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"设置cookie失败: {cookie['name']} - {str(e)}")
            
            # 刷新页面以应用cookies
            driver.refresh()
            
            # 等待直播画面加载
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'live-player-mounter')))
            
            # 等待加载完成
            time.sleep(5)
            
            # 生成临时文件路径
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_path = os.path.join('temp', f'temp_{timestamp}.png')
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # 截取页面
            driver.save_screenshot(temp_path)
            
            # 裁剪直播画面区域
            img = Image.open(temp_path)
            img_cropped = img.crop((197, 149, 1387, 818))  # 固定坐标
            img_cropped.save(temp_path)
            
            logger.info(f"截图成功: {temp_path}")
            return temp_path, True
            
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return None, False
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
