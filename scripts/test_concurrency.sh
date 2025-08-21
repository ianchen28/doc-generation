#!/bin/bash

# 并发测试脚本
# 用于快速测试系统的并发处理能力

set -e

echo "🧪 并发测试工具"
echo "=================================================="

# 检查服务是否运行
echo "🔍 检查服务状态..."
if ! curl -s "http://127.0.0.1:8081/health" > /dev/null 2>&1; then
    echo "❌ 服务未运行，请先启动服务:"
    echo "   ./manage.sh start 10 8081 20 4"
    exit 1
fi

echo "✅ 服务运行正常"

# 显示当前配置
echo ""
echo "📊 当前并发配置:"
CURRENT_MAX_TASKS=${MAX_CONCURRENT_TASKS:-10}
CURRENT_WORKERS_PER_PORT=${UVICORN_WORKERS_PER_PORT:-4}
echo "   - MAX_CONCURRENT_TASKS: $CURRENT_MAX_TASKS"
echo "   - UVICORN_WORKERS_PER_PORT: $CURRENT_WORKERS_PER_PORT"
echo ""

# 选择测试类型
echo "💡 选择测试类型:"
echo "   1) 基本测试 (20个请求，10个并发)"
echo "   2) 中等测试 (50个请求，20个并发)"
echo "   3) 压力测试 (100个请求，30个并发)"
echo "   4) 自定义测试"
echo ""

read -p "请选择测试类型 (1-4): " test_choice

case $test_choice in
    1)
        echo "🧪 执行基本测试..."
        python test_concurrency.py http://127.0.0.1:8081 20 10
        ;;
    2)
        echo "🧪 执行中等测试..."
        python test_concurrency.py http://127.0.0.1:8081 50 20
        ;;
    3)
        echo "🧪 执行压力测试..."
        python test_concurrency.py http://127.0.0.1:8081 100 30
        ;;
    4)
        echo "🧪 自定义测试..."
        read -p "请输入请求数量 (默认20): " num_requests
        read -p "请输入并发限制 (默认10): " concurrent_limit
        
        num_requests=${num_requests:-20}
        concurrent_limit=${concurrent_limit:-10}
        
        echo "🧪 执行自定义测试: $num_requests 个请求，$concurrent_limit 个并发"
        python test_concurrency.py http://127.0.0.1:8081 $num_requests $concurrent_limit
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "✅ 测试完成！"
echo ""
echo "💡 优化建议:"
echo "   - 如果吞吐量 < 5 请求/秒，建议增加并发配置"
echo "   - 如果平均响应时间 > 5 秒，建议检查系统资源"
echo "   - 如果成功率 < 90%，建议检查服务稳定性"
echo ""
echo "🔧 调整并发配置:"
echo "   ./manage.sh stop"
echo "   ./manage.sh start 10 8081 30 8  # 增加并发配置"
echo "   ./scripts/test_concurrency.sh   # 重新测试"
