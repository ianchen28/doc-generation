"""
主编排器节点模块

包含主工作流的各个节点：
- research: 初始研究节点
- generation: 大纲生成、章节拆分、参考文献生成节点
- editor: 融合编辑器节点
- outline_loader: 大纲加载器节点
"""

from .editor import fusion_editor_node
from .generation import bibliography_node, outline_generation_node, split_chapters_node
from .outline_loader import outline_loader_node
from .research import initial_research_node

__all__ = [
    'initial_research_node',
    'outline_generation_node',
    'outline_loader_node',
    'split_chapters_node',
    'bibliography_node',
    'fusion_editor_node',
]
