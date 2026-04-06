FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 【修改点 1】
# 不再使用 curl 下载脚本，而是直接用 pip 安装 uv
# 同时指定清华源 (-i)，解决国内网络连接问题
# build-essential 保留，以防某些库需要编译
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && rm -rf /var/lib/apt/lists/*

# 【修改点 2】
# 因为是用 pip 全局安装的，uv 已经在 PATH 里了，所以不需要再配置 ENV PATH
# 这行可以删掉，或者留着也没坏处
# ENV PATH="/root/.local/bin:$PATH" 

WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock* ./

# 【修改点 3】
# 运行 uv sync 时，也加上清华源参数，防止拉取依赖时超时
RUN uv sync --frozen --no-cache -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制所有源代码
COPY . .
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 这里添加系统依赖，或者先更新源
    # 注意：如果 apt-get update 失败，下面的安装也会失败

# 【关键修改】更换为国内源
# 对于 Debian 13 (Trixie)，使用清华源
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list && \
    sed -i 's|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list

# 然后更新包列表（这次应该能成功连接）
RUN apt-get update

# 安装 Playwright 浏览器及其系统依赖
# 因为上面设置了 ENV，这里会自动从国内源下载 Chromium 并安装系统库
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium
# 默认命令
CMD ["echo", "Usage: docker run <image> python <script_path>.py"]
