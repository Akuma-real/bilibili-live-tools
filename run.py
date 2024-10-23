#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加src目录到Python路径
sys.path.append(os.path.dirname(__file__))

# 修改导入语句
from src.core.monitor import BilibiliMonitor  # 改为从 core 子模块导入
from src.utils.init_project import init_project

def main():
    try:
        # 首先初始化项目
        init_project()
        
        # 然后启动监控
        monitor = BilibiliMonitor()
        monitor.run()
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
