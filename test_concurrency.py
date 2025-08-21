#!/usr/bin/env python3
"""
并发测试脚本
用于测试系统的并发处理能力
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import List, Dict

class ConcurrencyTester:
    def __init__(self, base_url: str, num_requests: int = 20, concurrent_limit: int = 10):
        self.base_url = base_url.rstrip('/')
        self.num_requests = num_requests
        self.concurrent_limit = concurrent_limit
        self.results = []
        self.start_time = None
        self.end_time = None
        
    async def test_outline_generation(self):
        """测试大纲生成的并发性能"""
        print(f"🚀 开始并发测试大纲生成")
        print(f"   目标URL: {self.base_url}")
        print(f"   请求数量: {self.num_requests}")
        print(f"   并发限制: {self.concurrent_limit}")
        print(f"   开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # 创建信号量来控制并发数
        semaphore = asyncio.Semaphore(self.concurrent_limit)
        
        # 创建所有任务
        tasks = []
        for i in range(self.num_requests):
            task = self._make_outline_request(semaphore, i)
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        self.end_time = time.time()
        self._print_results()
        
    async def _make_outline_request(self, semaphore: asyncio.Semaphore, request_id: int):
        """发送单个大纲生成请求"""
        async with semaphore:
            start_time = time.time()
            
            # 构造请求数据
            payload = {
                "session_id": f"test_session_{request_id}_{int(time.time())}",
                "task_prompt": f"请生成一个关于人工智能技术发展趋势的大纲，包含{request_id + 3}个章节",
                "is_online": True,
                "is_es_search": True,
                "context_files": [],
                "style_guide_content": "学术风格，结构清晰",
                "requirements": "内容要准确，结构要合理"
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/api/v1/jobs/outline",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        if response.status == 202:
                            result_data = await response.json()
                            self.results.append({
                                'request_id': request_id,
                                'status': 'success',
                                'status_code': response.status,
                                'duration': duration,
                                'task_id': result_data.get('redis_stream_key'),
                                'session_id': result_data.get('session_id')
                            })
                            print(f"✅ 请求 {request_id:2d} 成功 - 耗时: {duration:.2f}s - TaskID: {result_data.get('redis_stream_key')}")
                        else:
                            error_text = await response.text()
                            self.results.append({
                                'request_id': request_id,
                                'status': 'failed',
                                'status_code': response.status,
                                'duration': duration,
                                'error': error_text
                            })
                            print(f"❌ 请求 {request_id:2d} 失败 - 状态码: {response.status} - 耗时: {duration:.2f}s")
                            
            except asyncio.TimeoutError:
                end_time = time.time()
                duration = end_time - start_time
                self.results.append({
                    'request_id': request_id,
                    'status': 'timeout',
                    'duration': duration,
                    'error': '请求超时'
                })
                print(f"⏰ 请求 {request_id:2d} 超时 - 耗时: {duration:.2f}s")
                
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                self.results.append({
                    'request_id': request_id,
                    'status': 'error',
                    'duration': duration,
                    'error': str(e)
                })
                print(f"💥 请求 {request_id:2d} 异常 - 错误: {str(e)} - 耗时: {duration:.2f}s")
    
    def _print_results(self):
        """打印测试结果统计"""
        total_time = self.end_time - self.start_time
        
        # 统计结果
        successful = len([r for r in self.results if r['status'] == 'success'])
        failed = len([r for r in self.results if r['status'] == 'failed'])
        timeout = len([r for r in self.results if r['status'] == 'timeout'])
        error = len([r for r in self.results if r['status'] == 'error'])
        
        # 计算平均响应时间
        successful_durations = [r['duration'] for r in self.results if r['status'] == 'success']
        avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
        
        # 计算吞吐量
        requests_per_second = self.num_requests / total_time if total_time > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 并发测试结果统计")
        print("=" * 60)
        print(f"   总测试时间: {total_time:.2f}秒")
        print(f"   总请求数: {self.num_requests}")
        print(f"   成功请求: {successful}")
        print(f"   失败请求: {failed}")
        print(f"   超时请求: {timeout}")
        print(f"   异常请求: {error}")
        print(f"   成功率: {(successful/self.num_requests)*100:.1f}%")
        print(f"   平均响应时间: {avg_duration:.2f}秒")
        print(f"   吞吐量: {requests_per_second:.2f} 请求/秒")
        print(f"   结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 显示并发配置建议
        print("\n💡 并发性能分析:")
        if requests_per_second > 5:
            print("   ✅ 并发性能良好，系统能够处理高并发请求")
        elif requests_per_second > 2:
            print("   ⚠️  并发性能一般，可以考虑增加并发配置")
        else:
            print("   ❌ 并发性能较低，建议检查系统配置")
            
        if avg_duration < 2:
            print("   ✅ 响应时间良好")
        elif avg_duration < 5:
            print("   ⚠️  响应时间一般")
        else:
            print("   ❌ 响应时间较长，建议优化")
            
        print("\n🔧 优化建议:")
        print("   - 增加 MAX_CONCURRENT_TASKS 环境变量值")
        print("   - 增加 UVICORN_WORKERS_PER_PORT 环境变量值")
        print("   - 增加 Worker 端口数量")
        print("   - 检查 Redis 和数据库连接池配置")

async def main():
    """主函数"""
    import sys
    
    # 默认配置
    base_url = "http://127.0.0.1:8081"
    num_requests = 20
    concurrent_limit = 10
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        num_requests = int(sys.argv[2])
    if len(sys.argv) > 3:
        concurrent_limit = int(sys.argv[3])
    
    print("🔧 并发测试工具")
    print("使用方法: python test_concurrency.py [base_url] [num_requests] [concurrent_limit]")
    print("示例: python test_concurrency.py http://127.0.0.1:8081 30 15")
    print()
    
    # 创建测试器并运行测试
    tester = ConcurrencyTester(base_url, num_requests, concurrent_limit)
    await tester.test_outline_generation()

if __name__ == "__main__":
    asyncio.run(main())
