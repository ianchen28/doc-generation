FROM reg.hdec.com/basicimage/python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY service/requirements.txt .
# Install any dependencies
RUN pip install --upgrade pip -i http://nexus.simulate.com:8081/repository/hdecpypi-group/simple --trusted-host nexus.simulate.com && \
    pip install -r requirements.txt -i http://nexus.simulate.com:8081/repository/hdecpypi-group/simple --trusted-host nexus.simulate.com


COPY service/ .

# 暴露端口
EXPOSE 8081

# 设置启动命令
# 使用启动脚本从NACOS配置中读取worker数量
CMD ["python", "start_server.py"]