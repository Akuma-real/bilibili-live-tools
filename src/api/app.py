"""FastAPI应用程序"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import ConfigManager
from src.core.database import DatabaseManager
from src.core.monitor import BilibiliMonitor
from src.utils.init_project import init_project
import os
from loguru import logger
import threading
from .routes import config, monitor as monitor_routes  # 重命名避免冲突

def create_app() -> FastAPI:
    # 初始化项目
    init_project()
    
    # 创建FastAPI应用
    app = FastAPI(
        title="Bilibili Live Monitor API",
        description="B站直播监控系统API",
        version="1.0.0"
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 初始化核心组件
    db_manager = DatabaseManager(os.path.join('data', 'database.db'))
    config_manager = ConfigManager(db_manager)
    monitor = BilibiliMonitor()
    
    # 存储实例到应用状态
    app.state.db_manager = db_manager
    app.state.config_manager = config_manager
    app.state.monitor = monitor
    
    # 注册路由
    app.include_router(config.router)
    app.include_router(monitor_routes.router)  # 使用重命名后的路由
    
    @app.on_event("startup")
    async def startup_event():
        """启动时执行"""
        # 验证配置
        if not config_manager.validate_config():
            logger.error("配置验证失败")
            return
            
        # 在新线程中启动监控
        def run_monitor():
            try:
                monitor.run()
            except Exception as e:
                logger.error(f"监控线程异常: {str(e)}")
                
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        logger.info("监控线程已启动")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """关闭时执行"""
        logger.info("应用正在关闭...")
    
    @app.get("/health")
    async def health_check():
        """健康检查端点（无需鉴权）"""
        return {"status": "ok"}
    
    return app
