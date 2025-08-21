#!/bin/bash

# AI文档生成器API - 测试脚本
# 使用方法: ./run_api_tests.sh

echo "🚀 开始API测试..."
echo "=================================================="

# 检查服务是否运行
echo "🔍 检查服务状态..."
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ 服务正在运行"
else
    echo "❌ 服务未运行，请先启动服务: ./start_dev_server.sh"
    exit 1
fi

echo -e "\n"

# ============================================================================
# 1. 健康检查端点
# ============================================================================
echo "📋 1. 测试健康检查端点"
echo "--------------------------------------------------"
curl -X GET "http://localhost:8000/api/v1/health" \
  -H "Content-Type: application/json" \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n"
echo -e "\n"

# ============================================================================
# 2. AI文本编辑端点测试
# ============================================================================
echo "📋 2. 测试AI文本编辑端点"
echo "--------------------------------------------------"

echo "2.1 润色文本测试"
curl -X POST "http://localhost:8000/api/v1/actions/edit" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "polish",
    "text": "人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。",
    "polish_style": "professional"
  }' \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n"
echo -e "\n"

echo "2.2 扩写文本测试"
curl -X POST "http://localhost:8000/api/v1/actions/edit" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "expand",
    "text": "人工智能技术正在快速发展。"
  }' \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n"
echo -e "\n"

echo "2.3 总结文本测试"
curl -X POST "http://localhost:8000/api/v1/actions/edit" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "summarize",
    "text": "人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。"
  }' \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n"
echo -e "\n"

# ============================================================================
# 3. 大纲生成端点测试
# ============================================================================
echo "📋 3. 测试大纲生成端点"
echo "--------------------------------------------------"
OUTLINE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/jobs/outline" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "123456789",
    "taskPrompt": "请生成一份关于人工智能技术发展趋势的详细大纲",
    "isOnline": true,
    "contextFiles": [],
    "attachmentType": 0,
    "attachmentFileToken": null,
    "isContentRefer": 0,
    "isStyleImitative": 0,
    "isWritingRequirement": 0
  }' \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n")

echo "$OUTLINE_RESPONSE"
echo -e "\n"

# 提取taskId用于后续测试
TASK_ID=$(echo "$OUTLINE_RESPONSE" | grep -o '"taskId":"[^"]*"' | cut -d'"' -f4)
if [ -n "$TASK_ID" ]; then
    echo "✅ 获取到taskId: $TASK_ID"
else
    echo "⚠️  未能获取到taskId"
fi
echo -e "\n"

# ============================================================================
# 4. 文档生成端点测试 (从大纲对象)
# ============================================================================
echo "📋 4. 测试文档生成端点 (从大纲对象)"
echo "--------------------------------------------------"
curl -X POST "http://localhost:8000/api/v1/jobs/document" \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "123456789",
    "outline": {
      "title": "人工智能技术发展趋势",
      "nodes": [
        {
          "title": "人工智能概述",
          "contentSummary": "介绍人工智能的基本概念和发展历程",
          "children": []
        },
        {
          "title": "核心技术发展",
          "contentSummary": "分析机器学习、深度学习等核心技术的最新进展",
          "children": [
            {
              "title": "机器学习技术",
              "contentSummary": "传统机器学习算法的发展",
              "children": []
            },
            {
              "title": "深度学习技术",
              "contentSummary": "神经网络和深度学习的最新突破",
              "children": []
            }
          ]
        },
        {
          "title": "应用领域拓展",
          "contentSummary": "探讨AI在各个行业的应用现状和前景",
          "children": []
        }
      ]
    }
  }' \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n"
echo -e "\n"

# ============================================================================
# 5. 文档生成端点测试 (从大纲JSON字符串)
# ============================================================================
echo "📋 5. 测试文档生成端点 (从大纲JSON字符串)"
echo "--------------------------------------------------"
curl -X POST "http://localhost:8000/api/v1/jobs/document-from-outline" \
  -H "Content-Type: application/json" \
  -d '{
    "jobId": "123456789",
    "outlineJson": "{\"title\":\"人工智能技术发展趋势\",\"nodes\":[{\"title\":\"人工智能概述\",\"contentSummary\":\"介绍人工智能的基本概念和发展历程\",\"children\":[]},{\"title\":\"核心技术发展\",\"contentSummary\":\"分析机器学习、深度学习等核心技术的最新进展\",\"children\":[{\"title\":\"机器学习技术\",\"contentSummary\":\"传统机器学习算法的发展\",\"children\":[]},{\"title\":\"深度学习技术\",\"contentSummary\":\"神经网络和深度学习的最新突破\",\"children\":[]}]},{\"title\":\"应用领域拓展\",\"contentSummary\":\"探讨AI在各个行业的应用现状和前景\",\"children\":[]}]}",
    "sessionId": "123456789"
  }' \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n"
echo -e "\n"

# ============================================================================
# 6. 模拟文档生成端点测试
# ============================================================================
echo "📋 6. 测试模拟文档生成端点"
echo "--------------------------------------------------"
MOCK_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/jobs/document-from-outline/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "999888777",
    "outline_json": "{\"title\":\"人工智能技术发展趋势\",\"nodes\":[{\"title\":\"人工智能概述\",\"contentSummary\":\"介绍人工智能的基本概念和发展历程\",\"children\":[]},{\"title\":\"核心技术发展\",\"contentSummary\":\"分析机器学习、深度学习等核心技术的最新进展\",\"children\":[{\"title\":\"机器学习技术\",\"contentSummary\":\"传统机器学习算法的发展\",\"children\":[]},{\"title\":\"深度学习技术\",\"contentSummary\":\"神经网络和深度学习的最新突破\",\"children\":[]}]},{\"title\":\"应用领域拓展\",\"contentSummary\":\"探讨AI在各个行业的应用现状和前景\",\"children\":[]}]}",
    "session_id": "999888777"
  }' \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n")

echo "$MOCK_RESPONSE"
echo -e "\n"

# 提取模拟任务的taskId
MOCK_TASK_ID=$(echo "$MOCK_RESPONSE" | grep -o '"taskId":"[^"]*"' | cut -d'"' -f4)
if [ -n "$MOCK_TASK_ID" ]; then
    echo "✅ 获取到模拟任务taskId: $MOCK_TASK_ID"
    echo "💡 提示: 可以使用 test_mock_endpoint.py 来监听Redis流事件"
else
    echo "⚠️  未能获取到模拟任务taskId"
fi
echo -e "\n"

# ============================================================================
# 7. 根端点测试
# ============================================================================
echo "📋 7. 测试根端点"
echo "--------------------------------------------------"
curl -X GET "http://localhost:8000/" \
  -H "Content-Type: application/json" \
  -w "\n状态码: %{http_code}\n耗时: %{time_total}s\n"
echo -e "\n"

# ============================================================================
# 测试总结
# ============================================================================
echo "🎉 API测试完成!"
echo "=================================================="
echo "📊 测试总结:"
echo "✅ 健康检查端点"
echo "✅ AI文本编辑端点 (流式响应)"
echo "✅ 大纲生成端点"
echo "✅ 文档生成端点 (从大纲对象)"
echo "✅ 文档生成端点 (从大纲JSON字符串)"
echo "✅ 模拟文档生成端点"
echo "✅ 根端点"
echo -e "\n"

echo "💡 使用提示:"
echo "1. 大纲生成会返回taskId，可用于监听Redis流事件"
echo "2. 模拟端点会立即开始生成模拟内容并发布到Redis流"
echo "3. 流式编辑端点返回Server-Sent Events格式"
echo "4. 所有响应字段都使用驼峰命名法 (camelCase)"
echo -e "\n"

echo "🔗 相关文件:"
echo "- test_curl_commands.txt: 详细的curl命令集合"
echo "- test_mock_endpoint.py: Redis流事件监听测试"
echo "- start_dev_server.sh: 启动开发服务器"
echo -e "\n"

echo "✨ 测试脚本执行完毕!"
