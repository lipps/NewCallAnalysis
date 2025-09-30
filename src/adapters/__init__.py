"""UI适配器模块

该模块提供UI界面与现有分析系统之间的适配层，
通过适配器模式实现数据格式的无缝转换。
"""

from .ui_adapter import UIAdapter
from .evidence_enhancer import EvidenceEnhancer

__all__ = ['UIAdapter', 'EvidenceEnhancer']