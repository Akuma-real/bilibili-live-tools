#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import uvicorn
from src.api.app import create_app

def main():
    try:
        app = create_app()
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False
        )
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
