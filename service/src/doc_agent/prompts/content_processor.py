# service/src/doc_agent/prompts/content_processor.py
"""
内容处理器提示词模板
"""

V1_DEFAULT_RESEARCH_DATA_SUMMARY = """
你是一位专业的研究数据分析师。请对以下研究数据进行总结和分析。

**研究数据:**
{research_data}

**任务要求:**
1. 分析数据的主要内容和关键信息
2. 识别重要的观点、事实和数据
3. 总结核心发现和结论
4. 保持客观、准确的表述

**输出格式:**
请提供一份结构化的总结，包括：
- 主要发现
- 关键数据点
- 重要观点
- 结论和建议

请确保总结简洁明了，突出重点信息。
"""

V1_DEFAULT_KEY_POINTS_EXTRACTION = """
你是一位专业的信息提取专家。请从以下研究数据中提取关键要点。

**研究数据:**
{research_data}

**任务要求:**
1. 识别最重要的观点和结论
2. 提取关键的数据和事实
3. 总结核心概念和理论
4. 列出主要发现和见解

**输出格式:**
请提供一份关键要点列表，每个要点应该：
- 简洁明了（1-2句话）
- 具体明确
- 具有实际价值
- 便于理解和记忆

请提取{key_points_count}个最重要的要点。
"""

V1_DEFAULT_CONTENT_COMPRESSION = """
你是一位专业的内容压缩专家。请对以下研究数据进行智能压缩，保留最重要的信息。

**原始研究数据:**
{research_data}

**压缩要求:**
1. 保留核心信息和关键观点
2. 删除冗余和重复内容
3. 简化复杂表述，保持清晰
4. 确保压缩后的内容仍然完整和有意义
5. 目标长度：{target_length}字符

**输出格式:**
请提供压缩后的内容，确保：
- 信息完整性和准确性
- 逻辑结构清晰
- 重点突出
- 易于理解

请直接输出压缩后的内容，不要添加额外的说明。
"""

# 简化版本的内容处理器提示词
V1_SIMPLE_RESEARCH_DATA_SUMMARY = """
你是一位专业的研究数据分析师。请对以下研究数据进行简要总结。

**研究数据:**
{research_data}

**任务要求:**
1. 快速识别数据的主要信息
2. 提取关键观点和事实
3. 保持简洁明了的表述

**输出格式:**
请提供一份简化的总结，包括：
- 主要发现
- 关键数据点
- 重要观点

请确保总结简洁明了，突出重点信息。
"""

V1_SIMPLE_KEY_POINTS_EXTRACTION = """
你是一位专业的信息提取专家。请从以下研究数据中快速提取关键要点。

**研究数据:**
{research_data}

**任务要求:**
1. 快速识别最重要的观点
2. 提取关键的数据和事实
3. 总结核心概念

**输出格式:**
请提供一份关键要点列表，每个要点应该：
- 简洁明了（1句话）
- 具体明确
- 具有实际价值

请提取{key_points_count}个最重要的要点。
"""

V1_SIMPLE_CONTENT_COMPRESSION = """
你是一位专业的内容压缩专家。请对以下研究数据进行快速压缩，保留最重要的信息。

**原始研究数据:**
{research_data}

**压缩要求:**
1. 保留核心信息和关键观点
2. 删除冗余内容
3. 简化复杂表述
4. 确保压缩后的内容仍然有意义
5. 目标长度：{target_length}字符

**输出格式:**
请提供压缩后的内容，确保：
- 信息完整性和准确性
- 逻辑结构清晰
- 重点突出

请直接输出压缩后的内容，不要添加额外的说明。
"""

# 快速版本的内容处理器提示词（来自fast_prompts）
V2_FAST_RESEARCH_DATA_SUMMARY = """
你是一位专业的研究数据分析师。请对以下研究数据进行简要总结。

**研究数据:**
{research_data}

**任务要求:**
1. 快速识别数据的主要信息
2. 提取关键观点和事实
3. 保持简洁明了的表述

**输出格式:**
请提供一份简化的总结，包括：
- 主要发现
- 关键数据点
- 重要观点

请确保总结简洁明了，突出重点信息。
"""

V2_FAST_KEY_POINTS_EXTRACTION = """
你是一位专业的信息提取专家。请从以下研究数据中快速提取关键要点。

**研究数据:**
{research_data}

**任务要求:**
1. 快速识别最重要的观点
2. 提取关键的数据和事实
3. 总结核心概念

**输出格式:**
请提供一份关键要点列表，每个要点应该：
- 简洁明了（1句话）
- 具体明确
- 具有实际价值

请提取{key_points_count}个最重要的要点。
"""

V2_FAST_CONTENT_COMPRESSION = """
你是一位专业的内容压缩专家。请对以下研究数据进行快速压缩，保留最重要的信息。

**原始研究数据:**
{research_data}

**压缩要求:**
1. 保留核心信息和关键观点
2. 删除冗余内容
3. 简化复杂表述
4. 确保压缩后的内容仍然有意义
5. 目标长度：{target_length}字符

**输出格式:**
请提供压缩后的内容，确保：
- 信息完整性和准确性
- 逻辑结构清晰
- 重点突出

请直接输出压缩后的内容，不要添加额外的说明。
"""

# 支持版本选择的PROMPTS字典
DATA_SUMMARY_PROMPTS = {
    "v1_default": V1_DEFAULT_RESEARCH_DATA_SUMMARY,
    "v1_simple": V1_SIMPLE_RESEARCH_DATA_SUMMARY,
}

KEY_POINTS_EXTRACTION_PROMPTS = {
    "v1_default": V1_DEFAULT_KEY_POINTS_EXTRACTION,
    "v1_simple": V1_SIMPLE_KEY_POINTS_EXTRACTION,
}

CONTENT_COMPRESSION_PROMPTS = {
    "v1_default": V1_DEFAULT_CONTENT_COMPRESSION,
    "v1_simple": V1_SIMPLE_CONTENT_COMPRESSION,
}

# 统一的PROMPTS字典，用于PromptSelector
# 包含所有三个prompt的内容，以支持完整的content_processor功能
PROMPTS = {
    "v1_default_research_data_summary": V1_DEFAULT_RESEARCH_DATA_SUMMARY,
    "v1_default_key_points_extraction": V1_DEFAULT_KEY_POINTS_EXTRACTION,
    "v1_default_content_compression": V1_DEFAULT_CONTENT_COMPRESSION,
    "v1_simple_research_data_summary": V1_SIMPLE_RESEARCH_DATA_SUMMARY,
    "v1_simple_key_points_extraction": V1_SIMPLE_KEY_POINTS_EXTRACTION,
    "v1_simple_content_compression": V1_SIMPLE_CONTENT_COMPRESSION,
    "v2_fast_research_data_summary": V2_FAST_RESEARCH_DATA_SUMMARY,
    "v2_fast_key_points_extraction": V2_FAST_KEY_POINTS_EXTRACTION,
    "v2_fast_content_compression": V2_FAST_CONTENT_COMPRESSION
}
