#!/bin/bash

# 主管理脚本
# 使用方法: ./manage.sh [命令] [参数]
# 示例: ./manage.sh start 8
# 示例: ./manage.sh monitor realtime

set -e

SCRIPT_DIR="scripts"

echo "🎛️  AIDocGenerator 主管理脚本"
echo "=================================================="

# 检查脚本目录
if [ ! -d "$SCRIPT_DIR" ]; then
    echo "❌ 脚本目录不存在: $SCRIPT_DIR"
    exit 1
fi

# 获取命令和参数
COMMAND=${1:-"help"}
shift || true

case $COMMAND in
    "start"|"s")
        echo "🚀 启动多 Worker 服务"
        echo "使用方法: ./manage.sh start [worker_num] [lb_port] [concurrent_tasks_per_worker] [uvicorn_workers_per_port]"
        echo ""
        
        NUM_WORKERS=${1:-8}
        LB_PORT=${2:-8081}
        CONCURRENT_TASKS_PER_WORKER=${3:-10}
        UVICORN_WORKERS_PER_PORT=${4:-4}
        
        echo "启动参数:"
        echo "   Worker 数量: $NUM_WORKERS"
        echo "   负载均衡器端口: $LB_PORT"
        echo "   每个Worker的并发任务数: $CONCURRENT_TASKS_PER_WORKER"
        echo "   每个端口的uvicorn worker数: $UVICORN_WORKERS_PER_PORT"
        echo "   总理论并发容量: $((NUM_WORKERS * CONCURRENT_TASKS_PER_WORKER * UVICORN_WORKERS_PER_PORT))"
        echo ""
        
        # 检查 conda 环境
        if [ "$CONDA_DEFAULT_ENV" != "ai-doc" ]; then
            echo "❌ 当前环境不是 'ai-doc'，请先运行 'conda activate ai-doc'"
            exit 1
        fi
        
        echo "✅ 当前环境是 'ai-doc'"
        echo "🔄 启动服务..."
        
        # 设置环境变量
        export MAX_CONCURRENT_TASKS="$CONCURRENT_TASKS_PER_WORKER"
        export UVICORN_WORKERS_PER_PORT="$UVICORN_WORKERS_PER_PORT"
        
        # 调用启动脚本
        "$SCRIPT_DIR/quick_start_multi.sh" "$NUM_WORKERS" "$LB_PORT"
        ;;
        
    "stop"|"st")
        echo "🛑 停止多 Worker 服务"
        echo ""
        
        echo "🔄 停止服务..."
        
        # 切换到脚本目录并调用停止脚本
        cd "$SCRIPT_DIR"
        ./stop_multi.sh
        ;;
        
    "monitor"|"m")
        echo "📊 监控日志"
        echo "使用方法: ./manage.sh monitor [模式] [worker_num]"
        echo ""
        
        MONITOR_MODE=${1:-"realtime"}
        NUM_WORKERS=${2:-8}
        
        echo "监控参数:"
        echo "   模式: $MONITOR_MODE"
        echo "   Worker 数量: $NUM_WORKERS"
        echo ""
        
        # 切换到脚本目录并调用监控脚本
        cd "$SCRIPT_DIR"
        ./monitor_all_workers.sh "$NUM_WORKERS" "$MONITOR_MODE"
        ;;
        
    "logs"|"l")
        echo "📄 日志管理"
        echo "使用方法: ./manage.sh logs [命令]"
        echo ""
        
        LOG_COMMAND=${1:-"help"}
        
        case $LOG_COMMAND in
            "rotate"|"r")
                echo "🔄 手动轮转日志"
                echo ""
                cd "$SCRIPT_DIR"
                ./log_rotate.sh 8
                ;;
            "cleanup"|"c")
                echo "🧹 清理过老日志"
                echo ""
                cd "$SCRIPT_DIR"
                ./cleanup_logs.sh 30
                ;;
            "status"|"s")
                echo "📊 日志状态"
                echo ""
                echo "主日志目录:"
                ls -lh logs/*.log 2>/dev/null || echo "   无日志文件"
                
                echo "备份文件:"
                ls -lh logs/*.log.* 2>/dev/null || echo "   无备份文件"
                
                echo "归档目录:"
                if [ -d "logs/archive" ]; then
                    find logs/archive -type f -name "*.log.*" | head -10 | while read -r file; do
                        file_size=$(du -h "$file" | cut -f1)
                        echo "   - $file ($file_size)"
                    done
                    
                    total_archived=$(find logs/archive -type f -name "*.log.*" | wc -l)
                    if [ "$total_archived" -gt 10 ]; then
                        echo "   ... 还有 $((total_archived - 10)) 个归档文件"
                    fi
                else
                    echo "   无归档目录"
                fi
                ;;
            "help"|"h")
                echo "💡 日志管理命令:"
                echo "   - rotate/r: 手动轮转日志"
                echo "   - cleanup/c: 清理过老日志"
                echo "   - status/s: 显示日志状态"
                echo ""
                echo "示例:"
                echo "   ./manage.sh logs rotate"
                echo "   ./manage.sh logs cleanup"
                echo "   ./manage.sh logs status"
                ;;
            *)
                echo "❌ 无效的日志命令: $LOG_COMMAND"
                echo "运行 './manage.sh logs help' 查看可用命令"
                exit 1
                ;;
        esac
        ;;
        
    "demo"|"d")
        echo "🎬 演示功能"
        echo "使用方法: ./manage.sh demo [类型]"
        echo ""
        
        DEMO_TYPE=${1:-"help"}
        
        case $DEMO_TYPE in
            "rotation"|"r")
                echo "🔄 演示日志轮转"
                echo ""
                cd "$SCRIPT_DIR"
                ./demo_log_rotation.sh
                ;;
            "archive"|"a")
                echo "📦 演示日志归档"
                echo ""
                cd "$SCRIPT_DIR"
                ./demo_archive.sh
                ;;
            "help"|"h")
                echo "💡 演示类型:"
                echo "   - rotation/r: 日志轮转演示"
                echo "   - archive/a: 日志归档演示"
                echo ""
                echo "示例:"
                echo "   ./manage.sh demo rotation"
                echo "   ./manage.sh demo archive"
                ;;
            *)
                echo "❌ 无效的演示类型: $DEMO_TYPE"
                echo "运行 './manage.sh demo help' 查看可用类型"
                exit 1
                ;;
        esac
        ;;
        
    "test"|"t")
        echo "🧪 运行并发测试"
        echo ""
        
        # 调用测试脚本
        "$SCRIPT_DIR/test_concurrency.sh"
        ;;
        
    "help"|"h"|"")
        echo "💡 可用命令:"
        echo ""
        echo "🚀 服务管理:"
        echo "   - start/s [worker_num] [lb_port] [concurrent_tasks] [uvicorn_workers]: 启动服务"
        echo "   - stop/st: 停止服务"
        echo ""
        echo "📊 监控管理:"
        echo "   - monitor/m [模式] [worker_num]: 监控日志"
        echo "     模式: realtime, errors, warnings, summary, worker"
        echo ""
        echo "📄 日志管理:"
        echo "   - logs/l [命令]: 日志管理"
        echo "     命令: rotate, cleanup, status"
        echo ""
        echo "🧪 测试功能:"
        echo "   - test/t: 运行并发测试"
        echo ""
        echo "🎬 演示功能:"
        echo "   - demo/d [类型]: 功能演示"
        echo "     类型: rotation, archive"
        echo ""
        echo "📖 帮助:"
        echo "   - help/h: 显示此帮助"
        echo ""
        echo "🔧 并发配置示例:"
        echo "   # 标准配置 (总并发容量: 400)"
        echo "   ./manage.sh start 10 8081 10 4"
        echo ""
        echo "   # 高并发配置 (总并发容量: 1,600)"
        echo "   ./manage.sh start 10 8081 20 8"
        echo ""
        echo "   # 超高并发配置 (总并发容量: 4,000)"
        echo "   ./manage.sh start 10 8081 40 10"
        echo ""
        echo "📊 其他示例:"
        echo "   ./manage.sh monitor realtime 8"
        echo "   ./manage.sh logs status"
        echo "   ./manage.sh test"
        echo "   ./manage.sh demo rotation"
        ;;
        
    *)
        echo "❌ 无效的命令: $COMMAND"
        echo "运行 './manage.sh help' 查看可用命令"
        exit 1
        ;;
esac
