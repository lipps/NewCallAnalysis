"""向量检索和语义匹配引擎"""

import os
import asyncio
from typing import Dict, List, Any, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import uuid
from datetime import datetime

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class VectorSearchEngine:
    """向量检索和语义匹配引擎"""
    
    def __init__(self, 
                 model_name: str = None,
                 persist_directory: str = None,
                 collection_name: str = None):
        
        self.model_name = model_name or settings.model.embedding_model
        self.persist_directory = persist_directory or settings.database.chroma_persist_directory
        self.collection_name = collection_name or settings.database.collection_name
        
        # 初始化embedding模型
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        
        # 检索缓存
        self.search_cache = {}
        self.cache_size_limit = settings.processing.cache_size
        
    async def initialize(self):
        """异步初始化"""
        try:
            logger.info("初始化向量检索引擎")
            
            # 加载embedding模型
            await self._load_embedding_model()
            
            # 初始化Chroma客户端
            await self._initialize_chroma()
            
            # 初始化知识库数据
            await self._initialize_knowledge_base()
            
            logger.info("向量检索引擎初始化完成")
            
        except Exception as e:
            logger.error(f"向量检索引擎初始化失败: {e}")
            raise
    
    async def _load_embedding_model(self):
        """加载embedding模型"""
        try:
            logger.info(f"加载embedding模型: {self.model_name}")
            
            # 在异步环境中加载模型
            loop = asyncio.get_event_loop()
            self.embedding_model = await loop.run_in_executor(
                None, 
                SentenceTransformer,
                self.model_name
            )
            
            logger.info("Embedding模型加载完成")
            
        except Exception as e:
            logger.error(f"加载embedding模型失败: {e}")
            raise
    
    async def _initialize_chroma(self):
        """初始化Chroma客户端"""
        try:
            logger.info("初始化Chroma数据库")
            
            # 确保持久化目录存在
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # 创建Chroma客户端
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 获取或创建集合
            try:
                self.collection = self.chroma_client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"获取已存在的集合: {self.collection_name}")
            except:
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "销售通话质检知识库"}
                )
                logger.info(f"创建新集合: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"初始化Chroma数据库失败: {e}")
            raise
    
    async def _initialize_knowledge_base(self):
        """初始化知识库数据"""
        try:
            # 检查是否已有数据
            count = self.collection.count()
            if count > 0:
                logger.info(f"知识库已存在 {count} 条记录")
                return
            
            # 加载预定义的知识库数据
            knowledge_data = self._get_knowledge_base_data()
            
            if knowledge_data:
                await self._batch_add_documents(knowledge_data)
                logger.info(f"知识库初始化完成，添加了 {len(knowledge_data)} 条记录")
            
        except Exception as e:
            logger.error(f"初始化知识库失败: {e}")
            # 不抛出异常，允许系统继续运行
    
    def _get_knowledge_base_data(self) -> List[Dict[str, Any]]:
        """获取预定义的知识库数据"""
        
        knowledge_base = [
            # 破冰要点知识
            {
                "text": "我是益盟操盘手的专员，负责为客户提供股票分析服务",
                "category": "icebreak",
                "point": "professional_identity",
                "examples": ["我是益盟操盘手专员", "我是操盘手老师", "我是股票分析师"]
            },
            {
                "text": "我是益盟操盘手高级专员小李，帮助客户更好地使用产品",
                "category": "icebreak",
                "point": "professional_identity",
                "examples": ["我是益盟操盘手高级专员", "我是益盟客服专员", "我是益盟客服"]
            },
            {
                "text": "我是益盟股份客服，帮您激活开通了我们新版VIP体验特权",
                "category": "icebreak",
                "point": "professional_identity",
                "examples": ["我是益盟股份客服", "我是操盘手老师", "我是益盟客服"]
            },
            {
                "text": "我们可以帮助您把握买卖点机会，提升投资收益",
                "category": "icebreak", 
                "point": "value_help",
                "examples": ["帮您提升收益", "帮助您把握机会", "为您解决投资问题"]
            },
            {
                "text": "我们可以帮助您把握后面更好的机会，提高投资胜率",
                "category": "icebreak", 
                "point": "value_help",
                "examples": ["帮您提升收益", "帮助您提高投资胜率", "为您解决投资问题"]
            },
            {
                "text": "耽误您两三分钟时间，简单给您介绍一下我们的服务",
                "category": "icebreak",
                "point": "time_notice", 
                "examples": ["耽误您几分钟", "占用您一点时间", "不会太久"]
            },
            {
                "text": "我们是腾讯投资的上市公司，在行业内有很好的声誉",
                "category": "icebreak",
                "point": "company_background",
                "examples": ["腾讯投资", "上市公司", "知名企业"]
            },
            {
                "text": "这个分析服务是免费为您提供的，不收取任何费用",
                "category": "icebreak",
                "point": "free_teach",
                "examples": ["免费讲解", "免费分析", "不收费"]
            },
            
            # 功能演绎知识
            {
                "text": "B点代表买入信号，S点代表卖出信号，这是我们的核心买卖点提示功能",
                "category": "deduction",
                "point": "bs_explained",
                "examples": ["B点买入", "S点卖出", "买卖点信号", "操盘线提示"]
            },
            {
                "text": "BS点是趋势指标，出现B点代表着这支股票的上涨趋势形成，S点代表着下跌趋势形成，这是我们的核心买卖点提示功能",
                "category": "deduction",
                "point": "bs_explained",
                "examples": ["B点买入", "S点卖出", "买卖点信号", "操盘线提示"]
            },
            {
                "text": "我们分析不同周期的共振，包括日线、周线的趋势配合",
                "category": "deduction", 
                "point": "period_resonance_explained",
                "examples": ["周期共振", "多时间级别", "日线周线配合"]
            },
            {
                "text": "周期共振就是看大做小，看长做短，长周期呢，我们看大趋势，短周期可以做具体操作",
                "category": "deduction", 
                "point": "period_resonance_explained",
                "examples": ["周期共振", "看大做小", "看长做短"]
            },
            {
                "text": "主力控盘资金指标可以看到大资金的进出动向和筹码分布",
                "category": "deduction",
                "point": "control_funds_explained", 
                "examples": ["主力资金", "控盘资金", "筹码分布", "资金流向"]
            },
            {
                "text": "点击右侧【控盘资金VIP】,点设置参数, 把累计天数改为13天，资金我们要看他的趋势行为,13日是我们研发出来比较适合做波段的周期",
                "category": "deduction",
                "point": "control_funds_explained", 
                "examples": ["有控盘能力的主力资金", "控盘资金", "筹码分布", "资金流向"]
            },
            {
                "text": "红色的面积代表这些有控盘能力的主力资金在这段时期的净流入的,也就是说,控盘的主要是主力! 绿色面积代表主力资金该短时间是净流出的,也就是说主力在出货了,股价没有主力的支持,相对也难以维持上涨",
                "category": "deduction",
                "point": "control_funds_explained", 
                "examples": ["有控盘能力的主力资金", "控盘资金", "筹码分布", "净流入", "净流出", "资金流向"]
            },
            {
                "text": "步步高是显示量能活跃，股价还处于加速期",
                "category": "deduction",
                "point": "bubugao_explained",
                "examples": ["步步高功能", "步步高VIP", "步步高波段战法"]
            },
            {
                "text": "步步高是红色线代表活跃指数，柱子代表活跃程度！ 比如刚开始启动的蓝色就是稳上手阶段，黄色呢就是中继接力，橙色就是股价很可能要加速了",
                "category": "deduction",
                "point": "bubugao_explained",
                "examples": ["步步高功能", "步步高VIP", "红色线", "紫柱", "黄柱", "橙柱", "柱子代表活跃程度"]
            },
            {
                "text": "根据历史回测数据，使用我们的信号可以提升20%的收益率",
                "category": "deduction",
                "point": "value_quantify_explained", 
                "examples": ["历史收益", "回测数据", "提升收益率", "实盘效果"]
            },
            {
                "text": "咱们来看看您持有的这只股票，我给您具体分析一下",
                "category": "deduction",
                "point": "customer_stock_explained",
                "examples": ["演绎您的股票", "持仓分析", "具体股票", "您关注的"]
            }
        ]
        
        return knowledge_base
    
    async def _batch_add_documents(self, documents: List[Dict[str, Any]]):
        """批量添加文档到向量数据库"""
        try:
            texts = []
            metadatas = []
            ids = []
            
            for i, doc in enumerate(documents):
                texts.append(doc["text"])
                metadatas.append({
                    "category": doc["category"],
                    "point": doc["point"],
                    "examples": str(doc.get("examples", [])),
                    "timestamp": datetime.now().isoformat()
                })
                ids.append(f"{doc['category']}_{doc['point']}_{i}")
            
            # 生成embeddings
            embeddings = await self._generate_embeddings(texts)
            
            # 添加到数据库
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
        except Exception as e:
            logger.error(f"批量添加文档失败: {e}")
            raise
    
    async def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """生成文本embeddings"""
        try:
            # 在异步环境中生成embeddings
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self.embedding_model.encode,
                texts
            )
            return embeddings
            
        except Exception as e:
            logger.error(f"生成embeddings失败: {e}")
            raise
    
    async def search_similar(self, 
                            query: str,
                            text: str,
                            category: str = None,
                            top_k: int = 5,
                            similarity_threshold: float = 0.5) -> Optional[Dict[str, Any]]:
        """搜索相似文档"""
        
        try:
            # 检查缓存
            cache_key = f"{query}_{text}_{category}"
            if cache_key in self.search_cache:
                return self.search_cache[cache_key]
            
            # 组合查询文本
            search_text = f"{query} {text}"
            
            # 生成查询embedding
            query_embedding = await self._generate_embeddings([search_text])
            
            # 构建查询条件
            where_clause = {}
            if category:
                where_clause["category"] = category
            
            # 执行向量检索
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results["documents"] or not results["documents"][0]:
                return None
            
            # 处理结果
            best_result = None
            best_similarity = 0.0
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0], 
                results["distances"][0]
            )):
                # 转换距离为相似度 (Chroma使用L2距离，需要转换)
                similarity = max(0.0, 1.0 - distance / 2.0)
                
                if similarity > similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_result = {
                        "document": doc,
                        "similarity": similarity,
                        "category": metadata.get("category"),
                        "point": metadata.get("point"),
                        "examples": metadata.get("examples")
                    }
            
            # 添加到缓存
            if len(self.search_cache) >= self.cache_size_limit:
                # 删除最旧的缓存项
                oldest_key = next(iter(self.search_cache))
                del self.search_cache[oldest_key]
            
            self.search_cache[cache_key] = best_result
            
            return best_result
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return None
        """搜索相似文档"""
        
        try:
            # 检查缓存
            cache_key = f"{query}_{text}_{category}"
            if cache_key in self.search_cache:
                return self.search_cache[cache_key]
            
            # 组合查询文本
            search_text = f"{query} {text}"
            
            # 生成查询embedding
            query_embedding = await self._generate_embeddings([search_text])
            
            # 构建查询条件
            where_clause = {}
            if category:
                where_clause["category"] = category
            
            # 执行向量检索
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results["documents"] or not results["documents"][0]:
                return None
            
            # 处理结果
            best_result = None
            best_similarity = 0.0
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0], 
                results["distances"][0]
            )):
                # 转换距离为相似度 (Chroma使用L2距离，需要转换)
                similarity = max(0.0, 1.0 - distance / 2.0)
                
                if similarity > similarity_threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_result = {
                        "document": doc,
                        "similarity": similarity,
                        "category": metadata.get("category"),
                        "point": metadata.get("point"),
                        "examples": metadata.get("examples")
                    }
            
            # 添加到缓存
            if len(self.search_cache) >= self.cache_size_limit:
                # 删除最旧的缓存项
                oldest_key = next(iter(self.search_cache))
                del self.search_cache[oldest_key]
            
            self.search_cache[cache_key] = best_result
            
            return best_result
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return None
    
    async def add_document(self, 
                          text: str,
                          category: str,
                          point: str,
                          metadata: Dict[str, Any] = None) -> bool:
        """添加单个文档"""
        
        try:
            # 生成embedding
            embedding = await self._generate_embeddings([text])
            
            # 准备元数据
            doc_metadata = {
                "category": category,
                "point": point,
                "timestamp": datetime.now().isoformat()
            }
            if metadata:
                doc_metadata.update(metadata)
            
            # 生成ID
            doc_id = f"{category}_{point}_{uuid.uuid4().hex[:8]}"
            
            # 添加到数据库
            self.collection.add(
                embeddings=embedding.tolist(),
                documents=[text],
                metadatas=[doc_metadata],
                ids=[doc_id]
            )
            
            logger.info(f"添加文档成功: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False
    
    async def update_knowledge_base(self, documents: List[Dict[str, Any]]) -> bool:
        """更新知识库"""
        
        try:
            await self._batch_add_documents(documents)
            logger.info(f"知识库更新成功，添加了 {len(documents)} 条记录")
            
            # 清空缓存
            self.search_cache.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"更新知识库失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        
        try:
            collection_count = self.collection.count() if self.collection else 0
            
            return {
                "model_name": self.model_name,
                "collection_name": self.collection_name,
                "document_count": collection_count,
                "cache_size": len(self.search_cache),
                "cache_limit": self.cache_size_limit,
                "persist_directory": self.persist_directory
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    async def close(self):
        """关闭引擎"""
        try:
            if self.chroma_client:
                # Chroma客户端会自动持久化，无需手动保存
                pass
            
            # 清理缓存
            self.search_cache.clear()
            
            logger.info("向量检索引擎已关闭")
            
        except Exception as e:
            logger.error(f"关闭引擎失败: {e}")


# 全局向量引擎实例
_vector_engine_instance = None

async def get_vector_engine() -> VectorSearchEngine:
    """获取全局向量引擎实例"""
    global _vector_engine_instance
    
    if _vector_engine_instance is None:
        _vector_engine_instance = VectorSearchEngine()
        await _vector_engine_instance.initialize()
    
    return _vector_engine_instance
