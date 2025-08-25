#!/usr/bin/env python3
"""
TaskManager 简单监控脚本
不需要额外依赖，直接查看 Redis 中的任务状态
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

import redis.asyncio as redis
from src.doc_agent.core.config import settings
from src.doc_agent.core.task_manager import RUNNING_TASKS_KEY, CANCELLATION_CHANNEL


class SimpleTaskMonitor:
    """简单的任务监控器"""

    def __init__(self):
        self.redis_client = None

    async def connect(self):
        """连接 Redis"""
        try:
            self.redis_client = redis.from_url(settings.redis_url,
                                               encoding="utf-8",
                                               decode_responses=True)
            await self.redis_client.ping()
            print(f"✅ 已连接到 Redis: {settings.redis_url}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

    async def get_tasks(self) -> Dict[str, Dict]:
        """获取所有任务"""
        try:
            all_tasks = await self.redis_client.hgetall(RUNNING_TASKS_KEY)
            tasks_info = {}

            for task_id, task_data in all_tasks.items():
                try:
                    tasks_info[task_id] = json.loads(task_data)
                except:
                    tasks_info[task_id] = {
                        "worker_id": "unknown",
                        "status": "error"
                    }

            return tasks_info
        except Exception as e:
            print(f"❌ 获取任务失败: {e}")
            return {}

    async def show_status(self):
        """显示当前状态"""
        tasks = await self.get_tasks()

        print("\n" + "=" * 70)
        print(f"📋 TaskManager 任务状态")
        print(f"🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        if not tasks:
            print("✨ 当前没有运行中的任务")
        else:
            print(f"\n📊 总任务数: {len(tasks)}")

            # 统计 worker
            worker_stats = {}
            for task_info in tasks.values():
                worker_id = task_info.get("worker_id", "unknown")
                worker_stats[worker_id] = worker_stats.get(worker_id, 0) + 1

            print(f"👥 活跃 Workers: {len(worker_stats)}")
            print("\n🔍 Worker 分布:")
            for worker_id, count in sorted(worker_stats.items()):
                print(f"  - PID {worker_id}: {count} 个任务")

            print("\n📝 任务列表:")
            print("-" * 70)
            # 按照 task 中的 created_at 时间先后排序
            tasks_sorted = sorted(tasks.items(),
                                  key=lambda x: x[1].get("created_at", 0))
            for i, (task_id, task_info) in enumerate(tasks_sorted, 1):
                print(f"{i}. 任务ID: {task_id}")
                print(
                    f"   Worker: PID {task_info.get('worker_id', 'unknown')}")
                print(f"   状态: {task_info.get('status', 'unknown')}")
                print(f"   创建时间: {task_info.get('created_at', 'unknown')}")
                print("-" * 70)

    async def monitor_realtime(self, interval=2):
        """实时监控"""
        print("🚀 开始实时监控 (按 Ctrl+C 退出)")
        print(f"刷新间隔: {interval} 秒\n")

        try:
            while True:
                # 清屏（Unix/Linux/Mac）
                os.system('clear' if os.name != 'nt' else 'cls')

                await self.show_status()
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")

    async def listen_cancellations(self):
        """监听取消事件"""
        print("👂 开始监听取消事件 (按 Ctrl+C 退出)\n")

        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(CANCELLATION_CHANNEL)

            async for message in pubsub.listen():
                if message["type"] == "message":
                    task_id = message["data"]
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] 🚫 收到取消请求: {task_id}")

        except KeyboardInterrupt:
            print("\n👋 监听已停止")
        except Exception as e:
            print(f"❌ 监听失败: {e}")

    async def cleanup(self):
        """清理连接"""
        if self.redis_client:
            await self.redis_client.close()


async def main():
    """主函数"""
    monitor = SimpleTaskMonitor()

    if not await monitor.connect():
        return

    print("\n请选择操作:")
    print("1. 查看当前状态")
    print("2. 实时监控")
    print("3. 监听取消事件")
    print("4. 退出")

    try:
        choice = input("\n请输入选项 (1-4): ").strip()

        if choice == "1":
            await monitor.show_status()
        elif choice == "2":
            interval = input("输入刷新间隔(秒, 默认2): ").strip()
            interval = float(interval) if interval else 2
            await monitor.monitor_realtime(interval)
        elif choice == "3":
            await monitor.listen_cancellations()
        elif choice == "4":
            print("👋 再见!")
        else:
            print("❌ 无效选项")

    finally:
        await monitor.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
