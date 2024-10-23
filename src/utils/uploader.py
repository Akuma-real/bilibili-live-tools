"""图床上传模块"""
import requests
import os
import mimetypes
from loguru import logger
from typing import Optional, Tuple

class CloudflareUploader:
    """Cloudflare图床上传器"""
    def __init__(self, domain: str, auth_code: str):
        """初始化上传器
        
        Args:
            domain: 图床域名
            auth_code: 认证码
        """
        self.domain = domain.rstrip('/')  # 移除末尾的斜杠
        self.auth_code = auth_code
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
    
    def upload(self, file_path: str, compress: bool = True) -> Tuple[Optional[str], bool]:
        """上传文件到图床
        
        Args:
            file_path: 文件路径
            compress: 是否压缩图片
            
        Returns:
            Tuple[Optional[str], bool]: (图片URL, 是否成功)
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return None, False
            
            # 获取文件类型
            content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            
            # 准备上传
            url = f"https://{self.domain}/upload"
            params = {
                'authCode': self.auth_code,
                'serverCompress': 'true' if compress else 'false'
            }
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, content_type)
                }
                
                logger.debug(f"开始上传文件: {file_path}")
                response = self.session.post(
                    url,
                    params=params,
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        file_path = data[0].get('src', '')
                        if file_path:
                            image_url = f"https://{self.domain}{file_path}"
                            logger.info(f"文件上传成功: {image_url}")
                            return image_url, True
                
                logger.error(f"上传失败，响应: {response.text}")
                return None, False
                
        except Exception as e:
            logger.error(f"上传文件时出错: {str(e)}")
            return None, False
    
    def upload_screenshot(self, screenshot_path: str) -> Tuple[Optional[str], bool]:
        """上传截图
        
        Args:
            screenshot_path: 截图文件路径
            
        Returns:
            Tuple[Optional[str], bool]: (图片URL, 是否成功)
        """
        try:
            # 检查文件大小
            file_size = os.path.getsize(screenshot_path)
            # 如果大于5MB，启用压缩
            compress = file_size > 5 * 1024 * 1024
            
            return self.upload(screenshot_path, compress=compress)
            
        except Exception as e:
            logger.error(f"上传截图时出错: {str(e)}")
            return None, False

class ImageUploader:
    """图片上传管理器"""
    def __init__(self, config):
        """初始化上传管理器
        
        Args:
            config: 配置字典，包含 domain 和 auth_code
        """
        self.uploader = CloudflareUploader(
            domain=config['domain'],
            auth_code=config['auth_code']
        )
    
    def upload_image(self, image_path: str, compress: bool = True) -> Optional[str]:
        """上传图片
        
        Args:
            image_path: 图片路径
            compress: 是否压缩
            
        Returns:
            Optional[str]: 成功返回图片URL，失败返回None
        """
        url, success = self.uploader.upload(image_path, compress)
        return url if success else None
    
    def upload_screenshot(self, screenshot_path: str) -> Optional[str]:
        """上传截图
        
        Args:
            screenshot_path: 截图路径
            
        Returns:
            Optional[str]: 成功返回图片URL，失败返回None
        """
        url, success = self.uploader.upload_screenshot(screenshot_path)
        return url if success else None
