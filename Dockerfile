# 使用Alpine作为基础镜像
FROM python:3.12-alpine

# 设置工作目录
WORKDIR /app

# 安装必要的系统依赖
RUN apk add --no-cache \
    # 基础工具
    wget \
    xvfb \
    # Chrome相关依赖
    chromium \
    chromium-chromedriver \
    # 字体支持
    wqy-zenhei \
    # 其他依赖
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    # 编译工具(用于安装某些Python包)
    gcc \
    musl-dev \
    python3-dev \
    jpeg-dev \
    zlib-dev \
    libffi-dev \
    cairo-dev \
    pango-dev \
    gdk-pixbuf-dev

# 设置Chrome环境变量
ENV CHROME_BIN=/usr/bin/chromium-browser \
    CHROME_PATH=/usr/lib/chromium/ \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99

# 创建必要的目录
RUN mkdir -p data logs temp

# 复制项目文件
COPY requirements.txt .
COPY src/ src/
COPY run.py .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 清理编译依赖
RUN apk del gcc musl-dev python3-dev jpeg-dev zlib-dev libffi-dev cairo-dev pango-dev gdk-pixbuf-dev

# 复制并设置启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN apk add --no-cache dos2unix \
    && dos2unix /docker-entrypoint.sh \
    && chmod +x /docker-entrypoint.sh \
    && apk del dos2unix

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 设置目录权限（移除用户切换，使用 root 权限）
RUN chmod -R 777 /app/logs /app/data /app/temp

ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE 8000
