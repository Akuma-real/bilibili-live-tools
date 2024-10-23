#!/bin/sh

# 启动虚拟显示服务
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &

# 等待虚拟显示服务启动
sleep 1

# 运行Python程序
exec python run.py
