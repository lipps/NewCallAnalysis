"""Streamlit可视化Dashboard"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import requests

from src.models.schemas import CallAnalysisResult, CallInput, AnalysisConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CallAnalysisDashboard:
    """通话分析可视化Dashboard"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        
    def setup_page(self):
        """设置页面配置"""
        st.set_page_config(
            page_title="销售通话质检系统",
            page_icon="📞",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("📞 销售通话质检系统")
        st.markdown("---")
    
    def render_sidebar(self) -> Dict[str, Any]:
        """渲染侧边栏配置"""
        st.sidebar.header("⚙️ 配置")
        
        # 分析配置
        st.sidebar.subheader("分析设置")
        enable_vector = st.sidebar.checkbox("启用向量检索", value=True)
        enable_llm = st.sidebar.checkbox("启用LLM验证", value=True)
        confidence_threshold = st.sidebar.slider("置信度阈值", 0.0, 1.0, 0.7, 0.1)
        
        # 显示设置
        st.sidebar.subheader("显示设置")
        show_evidence = st.sidebar.checkbox("显示证据片段", value=True)
        show_confidence = st.sidebar.checkbox("显示置信度", value=True)
        
        return {
            "config": AnalysisConfig(
                enable_vector_search=enable_vector,
                enable_llm_validation=enable_llm,
                confidence_threshold=confidence_threshold
            ),
            "display": {
                "show_evidence": show_evidence,
                "show_confidence": show_confidence
            }
        }
    
    def render_input_section(self) -> Optional[Dict[str, Any]]:
        """渲染输入区域"""
        st.header("📝 通话文本输入")
        
        # 输入方式选择
        input_method = st.radio(
            "选择输入方式",
            ["直接输入", "文件上传", "示例数据"]
        )
        
        call_data = None
        
        if input_method == "直接输入":
            call_id = st.text_input("通话ID", value=f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            transcript = st.text_area(
                "通话转写文本",
                height=200,
                placeholder="请输入销售与客户的通话文本..."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                customer_id = st.text_input("客户ID（可选）")
            with col2:
                sales_id = st.text_input("销售员ID（可选）")
            
            if transcript.strip():
                call_data = {
                    "call_id": call_id,
                    "transcript": transcript,
                    "customer_id": customer_id or None,
                    "sales_id": sales_id or None,
                    "call_time": datetime.now().isoformat()
                }
        
        elif input_method == "文件上传":
            uploaded_file = st.file_uploader(
                "上传文本文件",
                type=['txt', 'json'],
                help="支持.txt文本文件或.json格式文件"
            )
            
            if uploaded_file:
                try:
                    if uploaded_file.type == "application/json":
                        call_data = json.loads(uploaded_file.read().decode())
                    else:
                        content = uploaded_file.read().decode('utf-8')
                        call_data = {
                            "call_id": f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            "transcript": content,
                            "call_time": datetime.now().isoformat()
                        }
                except Exception as e:
                    st.error(f"文件解析失败: {e}")
        
        elif input_method == "示例数据":
            example_data = self._get_example_data()
            selected_example = st.selectbox(
                "选择示例",
                list(example_data.keys())
            )
            
            if selected_example:
                call_data = example_data[selected_example]
                st.text_area(
                    "示例文本预览",
                    value=call_data["transcript"][:500] + "...",
                    height=150,
                    disabled=True
                )
        
        return call_data
    
    def _get_example_data(self) -> Dict[str, Dict[str, Any]]:
        """获取示例数据"""
        return {
            "成功案例": {
                "call_id": "example_success",
                "transcript": """销售：您好，我是益盟操盘手的专员小王，很高兴为您服务。
客户：你好。
销售：是这样的，我们是腾讯投资的上市公司，专门为股民提供专业的股票分析服务。耽误您两分钟时间，我给您免费讲解一下我们的买卖点功能。
客户：好的，你说。
销售：咱们的核心功能是BS点提示，B点代表最佳买入时机，S点代表卖出信号。比如您持有的招商银行，我们来具体看一下。
客户：这个功能听起来不错，收费吗？
销售：根据历史数据，使用我们信号的客户平均能提升20%的收益率。另外我们还有步步高VIP专属功能。
客户：可以试用一下吗？""",
                "customer_id": "customer_001",
                "sales_id": "sales_001",
                "call_time": "2024-01-15T10:30:00"
            },
            "一般案例": {
                "call_id": "example_normal",
                "transcript": """销售：您好，请问是王先生吗？
客户：是的，什么事？
销售：我这边是做股票分析的，想跟您聊聊投资的事情。
客户：不需要，我没空。
销售：不会耽误您太久，就两分钟。我们有个很好的买卖点提示功能。
客户：不感兴趣，谢谢。""",
                "customer_id": "customer_002", 
                "sales_id": "sales_002",
                "call_time": "2024-01-15T14:20:00"
            }
        }
    
    def analyze_call(self, call_data: Dict[str, Any], config: AnalysisConfig) -> Optional[CallAnalysisResult]:
        """调用API分析通话"""
        try:
            with st.spinner("正在分析通话..."):
                response = requests.post(
                    f"{self.api_base_url}/analyze",
                    json={
                        "call_input": call_data,
                        "config": config.dict()
                    },
                    timeout=280
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    return CallAnalysisResult(**result_data)
                else:
                    st.error(f"分析失败: {response.status_code} - {response.text}")
                    return None
                    
        except requests.exceptions.Timeout:
            st.error("请求超时，请检查网络连接")
            return None
        except requests.exceptions.ConnectionError:
            st.error("无法连接到分析服务，请确保服务正在运行")
            return None
        except Exception as e:
            st.error(f"分析过程出错: {e}")
            return None
    
    def render_results(self, result: CallAnalysisResult, display_config: Dict[str, Any]):
        """渲染分析结果"""
        
        # 结果概览
        st.header("📊 分析结果")
        
        # KPI卡片
        self._render_kpi_cards(result)
        
        # 详细结果
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_icebreak_results(result.icebreak, display_config)
            self._render_process_metrics(result.process)
        
        with col2:
            self._render_deduction_results(result.演绎, display_config)
            self._render_customer_analysis(result.customer)
        
        # 客户拒绝沟通面板（独立展示结构化输出）
        self._render_rejection_panel(result.icebreak)

        # 动作执行情况
        self._render_action_execution(result.actions)
        
        # 原始数据
        with st.expander("🔍 查看原始JSON数据"):
            st.json(result.dict())
    
    def _render_kpi_cards(self, result: CallAnalysisResult):
        """渲染KPI卡片"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            icebreak_hits = sum(1 for field in ['professional_identity', 'value_help', 'time_notice', 
                                               'company_background', 'free_teach']
                               if getattr(result.icebreak, field).hit)
            st.metric(
                "破冰命中率",
                f"{icebreak_hits}/5",
                f"{icebreak_hits/5*100:.1f}%"
            )
        
        with col2:
            deduction_hits = sum(1 for field in ['bs_explained', 'period_resonance_explained', 
                                                'control_funds_explained', 'bubugao_explained',
                                                'value_quantify_explained', 'customer_stock_explained']
                                if getattr(result.演绎, field).hit)
            st.metric(
                "演绎覆盖率",
                f"{deduction_hits}/6",
                f"{deduction_hits/6*100:.1f}%"
            )
        
        with col3:
            st.metric(
                "通话时长",
                f"{result.process.explain_duration_min:.1f}分钟",
                "正常" if 5 <= result.process.explain_duration_min <= 20 else "异常"
            )
        
        with col4:
            st.metric(
                "互动频率",
                f"{result.process.interaction_rounds_per_min:.1f}/分钟",
                "良好" if 1 <= result.process.interaction_rounds_per_min <= 3 else "偏低"
            )
    
    def _render_icebreak_results(self, icebreak_data, display_config: Dict[str, Any]):
        """渲染破冰结果"""
        st.subheader("🤝 破冰要点检测")
        
        # 破冰要点数据
        icebreak_points = {
            "专业身份": icebreak_data.professional_identity,
            "帮助价值": icebreak_data.value_help,
            "时间说明": icebreak_data.time_notice,
            "公司背景": icebreak_data.company_background,
            "免费讲解": icebreak_data.free_teach
        }
        
        # 创建数据框
        df_data = []
        for point_name, point_data in icebreak_points.items():
            sig = getattr(point_data, "signals", {}) or {}
            df_data.append({
                "要点": point_name,
                "命中": "✅" if point_data.hit else "❌",
                "置信度": f"{point_data.confidence:.2f}" if display_config.get("show_confidence") else "-",
                "证据片段": point_data.evidence if display_config.get("show_evidence") and point_data.evidence else "-",
                "证据来源": getattr(point_data, "evidence_source", "-"),
                "R信": f"{sig.get('rule_confidence', 0):.2f}" if display_config.get("show_confidence") else "-",
                "V相": f"{sig.get('vector_similarity', 0):.2f}" if display_config.get("show_confidence") else "-",
                "L信": f"{sig.get('llm_confidence', 0):.2f}" if display_config.get("show_confidence") else "-",
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # 饼图
        hit_count = sum(1 for point_data in icebreak_points.values() if point_data.hit)
        miss_count = len(icebreak_points) - hit_count
        
        fig_pie = px.pie(
            values=[hit_count, miss_count],
            names=["命中", "未命中"],
            title="破冰要点命中率",
            color_discrete_map={"命中": "#2E8B57", "未命中": "#DC143C"}
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # KPI: 客户拒绝/应对策略统计
        kpi_col1, kpi_col2 = st.columns(2)
        try:
            if hasattr(icebreak_data, 'rejection_kpi') and icebreak_data.rejection_kpi:
                with kpi_col1:
                    st.markdown("**客户拒绝-KPI**")
                    total_r = icebreak_data.rejection_kpi.get('total', 0)
                    by_type = icebreak_data.rejection_kpi.get('by_type', [])
                    df_r = pd.DataFrame(by_type)
                    if not df_r.empty:
                        df_r['ratio'] = (df_r['ratio'] * 100).map(lambda x: f"{x:.1f}%")
                    st.metric("拒绝总次数", f"{total_r}")
                    if not df_r.empty:
                        st.dataframe(df_r, use_container_width=True)
                        # 饼图（按类型计数）
                        df_r_counts = pd.DataFrame(by_type)
                        df_r_counts = df_r_counts[df_r_counts['count'] > 0]
                        if not df_r_counts.empty:
                            fig_r_pie = px.pie(df_r_counts, values='count', names='type', title='客户拒绝-类型占比')
                            st.plotly_chart(fig_r_pie, use_container_width=True)
                            # 条形图（按次数降序）
                            df_r_counts = df_r_counts.sort_values('count', ascending=False)
                            fig_r_bar = px.bar(df_r_counts, x='type', y='count', title='客户拒绝-类型次数', text='count')
                            fig_r_bar.update_layout(xaxis_title='类型', yaxis_title='次数', showlegend=False)
                            st.plotly_chart(fig_r_bar, use_container_width=True)
            if hasattr(icebreak_data, 'handling_kpi') and icebreak_data.handling_kpi:
                with kpi_col2:
                    st.markdown("**应对策略-KPI**")
                    total_h = icebreak_data.handling_kpi.get('total', 0)
                    by_st = icebreak_data.handling_kpi.get('by_strategy', [])
                    df_h = pd.DataFrame(by_st)
                    if not df_h.empty:
                        df_h['ratio'] = (df_h['ratio'] * 100).map(lambda x: f"{x:.1f}%")
                    st.metric("应对总次数", f"{total_h}")
                    if not df_h.empty:
                        st.dataframe(df_h, use_container_width=True)
                        # 饼图（按策略计数）
                        df_h_counts = pd.DataFrame(by_st)
                        df_h_counts = df_h_counts[df_h_counts['count'] > 0]
                        if not df_h_counts.empty:
                            fig_h_pie = px.pie(df_h_counts, values='count', names='strategy', title='应对策略-占比')
                            st.plotly_chart(fig_h_pie, use_container_width=True)
                            # 条形图（按次数降序）
                            df_h_counts = df_h_counts.sort_values('count', ascending=False)
                            fig_h_bar = px.bar(df_h_counts, x='strategy', y='count', title='应对策略-次数', text='count')
                            fig_h_bar.update_layout(xaxis_title='策略', yaxis_title='次数', showlegend=False)
                            st.plotly_chart(fig_h_bar, use_container_width=True)
        except Exception as _:
            pass

    def _render_rejection_panel(self, icebreak_data):
        """渲染 客户拒绝沟通情况 面板"""
        st.subheader("🙅 客户拒绝沟通情况")
        try:
            count = getattr(icebreak_data, 'handle_objection_count', None)
            if count is None:
                # 兼容旧字段
                count = getattr(icebreak_data, 'refuse_recover_count', 0)
            st.metric("业务员应对拒绝次数", f"{count}")

            rr = getattr(icebreak_data, 'rejection_reasons', []) or []
            hs = getattr(icebreak_data, 'handling_strategies', []) or []

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**客户拒绝沟通原因**")
                if rr:
                    df_rr = pd.DataFrame(rr)
                    # 统一列名
                    if 'type' in df_rr.columns and 'quote' in df_rr.columns:
                        df_rr = df_rr[['type', 'quote']]
                        df_rr.columns = ['类型', '原文片段']
                    st.dataframe(df_rr, use_container_width=True)
                else:
                    st.info("未识别到明显的拒绝/抗拒表达")

            with col2:
                st.markdown("**应对拒绝的做法**")
                if hs:
                    df_hs = pd.DataFrame(hs)
                    if 'strategy' in df_hs.columns and 'quote' in df_hs.columns:
                        df_hs = df_hs[['strategy', 'quote']]
                        df_hs.columns = ['策略', '原文片段']
                    st.dataframe(df_hs, use_container_width=True)
                else:
                    st.info("未识别到明确的应对拒绝动作")
        except Exception as e:
            st.warning(f"拒绝沟通面板渲染异常: {e}")
    
    def _render_deduction_results(self, deduction_data, display_config: Dict[str, Any]):
        """渲染演绎结果"""
        st.subheader("💡 功能演绎检测")
        
        # 演绎要点数据
        deduction_points = {
            "BS点讲解": deduction_data.bs_explained,
            "周期共振": deduction_data.period_resonance_explained,
            "控盘资金": deduction_data.control_funds_explained,
            "步步高": deduction_data.bubugao_explained,
            "价值量化": deduction_data.value_quantify_explained,
            "客户股票": deduction_data.customer_stock_explained
        }
        
        # 创建数据框
        df_data = []
        for point_name, point_data in deduction_points.items():
            sig = getattr(point_data, "signals", {}) or {}
            df_data.append({
                "功能点": point_name,
                "讲解": "✅" if point_data.hit else "❌",
                "置信度": f"{point_data.confidence:.2f}" if display_config.get("show_confidence") else "-",
                "证据片段": point_data.evidence if display_config.get("show_evidence") and point_data.evidence else "-",
                "证据来源": getattr(point_data, "evidence_source", "-"),
                "R信": f"{sig.get('rule_confidence', 0):.2f}" if display_config.get("show_confidence") else "-",
                "V相": f"{sig.get('vector_similarity', 0):.2f}" if display_config.get("show_confidence") else "-",
                "L信": f"{sig.get('llm_confidence', 0):.2f}" if display_config.get("show_confidence") else "-",
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # 柱状图
        hit_data = [point_data.hit for point_data in deduction_points.values()]
        fig_bar = px.bar(
            x=list(deduction_points.keys()),
            y=[1 if hit else 0 for hit in hit_data],
            title="功能演绎覆盖情况",
            color=["已讲解" if hit else "未讲解" for hit in hit_data],
            color_discrete_map={"已讲解": "#4CAF50", "未讲解": "#F44336"}
        )
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    def _render_process_metrics(self, process_data):
        """渲染过程指标"""
        st.subheader("⏱️ 过程指标")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "讲解时长",
                f"{process_data.explain_duration_min:.1f} 分钟",
                delta="正常" if 5 <= process_data.explain_duration_min <= 20 else "异常"
            )
            
            st.metric(
                "总字数",
                f"{process_data.total_words:,}",
                delta=f"销售占比 {process_data.sales_words/max(process_data.total_words,1)*100:.1f}%"
            )
        
        with col2:
            st.metric(
                "互动频率",
                f"{process_data.interaction_rounds_per_min:.1f} 次/分钟",
                delta="良好" if 1 <= process_data.interaction_rounds_per_min <= 3 else "偏低"
            )
            
            deal_status = "✅ 成交/约访" if process_data.deal_or_visit else "❌ 未成交"
            st.metric(
                "成交情况",
                deal_status,
                delta=None
            )

        # 要钱行为展示
        with st.expander("💰 要钱/购买类行为"):
            count = getattr(process_data, 'money_ask_count', 0)
            st.metric("要钱行为次数", f"{count}")
            quotes = getattr(process_data, 'money_ask_quotes', []) or []
            if quotes:
                st.write("**证据片段：**")
                for i, q in enumerate(quotes, 1):
                    st.write(f"{i}. {q}")
    
    def _render_customer_analysis(self, customer_data):
        """渲染客户分析"""
        st.subheader("👤 客户分析")
        
        # 客户态度
        attitude_color = {
            "是": "success",
            "否": "error", 
            "不明": "warning"
        }[customer_data.value_recognition.value]
        
        st.write(f"**价值认同度:** :{attitude_color}[{customer_data.value_recognition.value}]")
        
        # 态度评分
        st.write(f"**态度评分:** {customer_data.attitude_score:.2f} (-1到1)")
        
        # 态度评分可视化
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=customer_data.attitude_score,
            title={'text': "客户态度评分"},
            gauge={
                'axis': {'range': [-1, 1]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [-1, -0.3], 'color': "red"},
                    {'range': [-0.3, 0.3], 'color': "yellow"},
                    {'range': [0.3, 1], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': 0
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # 客户总结
        if customer_data.summary:
            st.write(f"**客户总结:** {customer_data.summary}")
        
        # 客户问题
        if customer_data.questions:
            st.write("**客户问题:**")
            for i, question in enumerate(customer_data.questions, 1):
                st.write(f"{i}. {question}")
    
    def _render_action_execution(self, actions_data):
        """渲染动作执行情况"""
        st.subheader("🎯 标准动作执行情况")
        
        # 收集所有动作数据
        action_items = [
            ("专业身份", actions_data.professional_identity),
            ("帮助价值", actions_data.value_help),
            ("时间说明", actions_data.time_notice),
            ("公司背景", actions_data.company_background),
            ("免费讲解", actions_data.free_teach),
            ("BS点讲解", actions_data.bs_explained),
            ("周期共振", actions_data.period_resonance_explained),
            ("控盘资金", actions_data.control_funds_explained),
            ("步步高", actions_data.bubugao_explained),
            ("价值量化", actions_data.value_quantify_explained),
            ("客户股票", actions_data.customer_stock_explained)
        ]
        
        # 创建执行情况表格
        df_actions = pd.DataFrame([
            {
                "动作": name,
                "执行": "✅" if action.executed else "❌",
                "次数": action.count,
                "证据数量": len(action.evidence_list)
            }
            for name, action in action_items
        ])
        
        st.dataframe(df_actions, use_container_width=True)
        
        # 执行率统计
        executed_count = sum(1 for _, action in action_items if action.executed)
        total_count = len(action_items)
        execution_rate = executed_count / total_count * 100
        
        st.metric(
            "整体执行率",
            f"{executed_count}/{total_count}",
            f"{execution_rate:.1f}%"
        )
    
    def render_batch_analysis(self):
        """渲染批量分析功能"""
        st.header("📊 批量分析")
        
        uploaded_files = st.file_uploader(
            "上传批量文件",
            type=['json', 'csv'],
            accept_multiple_files=True,
            help="支持JSON格式的通话数据文件"
        )
        
        if uploaded_files:
            st.write(f"已上传 {len(uploaded_files)} 个文件")
            
            if st.button("开始批量分析"):
                # 这里实现批量分析逻辑
                st.info("批量分析功能开发中...")
    
    def run(self):
        """运行Dashboard"""
        self.setup_page()
        
        # 渲染侧边栏
        sidebar_config = self.render_sidebar()
        
        # 主要内容区域
        tab1, tab2, tab3 = st.tabs(["单次分析", "批量分析", "系统状态"])
        
        with tab1:
            # 输入区域
            call_data = self.render_input_section()
            
            # 分析按钮
            if call_data and st.button("🔍 开始分析", type="primary"):
                result = self.analyze_call(call_data, sidebar_config["config"])
                if result:
                    st.session_state['analysis_result'] = result
                    st.session_state['display_config'] = sidebar_config["display"]
            
            # 显示结果
            if 'analysis_result' in st.session_state:
                self.render_results(
                    st.session_state['analysis_result'],
                    st.session_state.get('display_config', {})
                )
        
        with tab2:
            self.render_batch_analysis()
        
        with tab3:
            self._render_system_status()
    
    def _render_system_status(self):
        """渲染系统状态"""
        st.header("🖥️ 系统状态")
        
        try:
            # 获取系统统计信息
            response = requests.get(f"{self.api_base_url}/statistics", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.subheader("向量引擎")
                    vector_stats = stats.get("vector_engine", {})
                    st.write(f"文档数量: {vector_stats.get('document_count', 0)}")
                    st.write(f"缓存大小: {vector_stats.get('cache_size', 0)}")
                
                with col2:
                    st.subheader("规则引擎")
                    rule_stats = stats.get("rule_engine", {})
                    st.write(f"规则总数: {rule_stats.get('total_rules', 0)}")
                    st.write(f"缓存大小: {rule_stats.get('cache_size', 0)}")
                
                with col3:
                    st.subheader("LLM引擎")
                    llm_stats = stats.get("llm_engine", {})
                    st.write(f"请求次数: {llm_stats.get('request_count', 0)}")
                    st.write(f"总Token数: {llm_stats.get('total_tokens', 0)}")
                    st.write(f"错误率: {llm_stats.get('error_rate', 0):.2%}")
                
                # 健康检查
                health_response = requests.get(f"{self.api_base_url}/health", timeout=10)
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    st.success("✅ 系统运行正常")
                    
                    with st.expander("详细健康信息"):
                        st.json(health_data)
                else:
                    st.error("❌ 系统健康检查失败")
            
            else:
                st.error(f"获取系统信息失败: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ 无法连接到后端服务")
        except Exception as e:
            st.error(f"❌ 系统状态检查失败: {e}")


def main():
    """主函数"""
    dashboard = CallAnalysisDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
