"""
燃烧实验数据管理系统
Combustion Experiment Data Management System
"""
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import tempfile
import zipfile
from pathlib import Path

# 导入必要的模块
from utils.xml_parser import parse_experiment_xml, validate_xml_structure
from utils.converters import UnitConverter
from utils.constants import *

# 页面配置
st.set_page_config(
    page_title="燃烧实验数据管理系统",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化session state
if 'current_experiment' not in st.session_state:
    st.session_state.current_experiment = None
if 'experiment_loaded' not in st.session_state:
    st.session_state.experiment_loaded = False
if 'data_groups' not in st.session_state:
    st.session_state.data_groups = []


def main():
    """主函数"""
    st.title("🔥 燃烧实验数据管理系统")
    st.markdown("---")
    
    # 侧边栏
    with st.sidebar:
        st.header("📍 功能选择")
        mode = st.radio(
            "选择操作模式",
            ["📂 加载文件", "📊 数据可视化", "📈 数据分析", "🔄 数据转换", "📥 数据导出"]
        )
        
        st.markdown("---")
        
        # 显示当前状态
        st.header("📌 当前状态")
        if st.session_state.experiment_loaded and st.session_state.current_experiment:
            st.success("✅ 已加载实验数据")
            exp = st.session_state.current_experiment
            st.info(f"类型: {exp.get('experiment_type', 'N/A')}")
            st.info(f"数据组: {len(exp.get('datagroups', []))}")
        else:
            st.info("💤 未加载数据")
        
        st.markdown("---")
        
        # 快速操作
        if st.button("🗑️ 清除数据", use_container_width=True):
            st.session_state.current_experiment = None
            st.session_state.experiment_loaded = False
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 关于")
        st.info(
            "本系统用于管理和分析燃烧实验数据，"
            "支持ReSpecTh XML格式。"
        )
    
    # 主页面内容路由
    if mode == "📂 加载文件":
        load_experiment_file()
    elif mode == "📊 数据可视化":
        visualize_data()
    elif mode == "📈 数据分析":
        analyze_data()
    elif mode == "🔄 数据转换":
        convert_data()
    elif mode == "📥 数据导出":
        export_data()


def load_experiment_file():
    """加载实验数据"""
    st.header("📂 加载实验数据")
    
    # 文件上传器
    uploaded_file = st.file_uploader(
        "选择XML文件",
        type=['xml'],
        help="支持ReSpecTh格式的XML文件"
    )
    
    if uploaded_file is not None:
        # 显示文件信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("文件名", uploaded_file.name)
        with col2:
            st.metric("文件大小", f"{uploaded_file.size / 1024:.2f} KB")
        with col3:
            st.metric("文件类型", uploaded_file.type or "XML")
        
        # 解析按钮
        if st.button("🔄 解析文件", type="primary", use_container_width=True):
            try:
                # 创建临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # 验证XML结构
                with st.spinner("验证文件结构..."):
                    is_valid, errors = validate_xml_structure(tmp_path)
                
                if not is_valid:
                    st.error("❌ XML文件结构验证失败：")
                    for error in errors:
                        st.error(f"  • {error}")
                    os.unlink(tmp_path)
                    return
                
                # 解析XML文件
                with st.spinner("正在解析XML文件..."):
                    exp_data = parse_experiment_xml(tmp_path)
                
                # 删除临时文件
                os.unlink(tmp_path)
                
                if exp_data:
                    # 存储到session state
                    st.session_state.current_experiment = exp_data
                    st.session_state.experiment_loaded = True
                    
                    st.success(f"✅ 成功加载实验数据！")
                    
                    # 显示摘要信息
                    display_experiment_summary(exp_data)
                else:
                    st.error("❌ 解析失败：未能提取数据")
                    
            except Exception as e:
                st.error(f"❌ 加载文件失败: {str(e)}")
                import traceback
                with st.expander("查看详细错误"):
                    st.code(traceback.format_exc())
    
    # 如果已加载数据，显示详细信息
    if st.session_state.experiment_loaded and st.session_state.current_experiment:
        st.markdown("---")
        display_experiment_details(st.session_state.current_experiment)


def display_experiment_summary(exp_data):
    """显示实验数据摘要"""
    st.markdown("### 📋 数据摘要")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("实验类型", exp_data.get('experiment_type', 'N/A'))
    with col2:
        st.metric("数据组数量", len(exp_data.get('datagroups', [])))
    with col3:
        total_points = 0
        for dg in exp_data.get('datagroups', []):
            if 'data_df' in dg and dg['data_df'] is not None:
                total_points += len(dg['data_df'])
            elif 'datapoints' in dg:
                total_points += len(dg['datapoints'])
        st.metric("总数据点", total_points)


def display_experiment_details(exp_data):
    """显示实验详细信息"""
    st.subheader("📊 实验数据详情")
    
    # 使用标签页组织内容
    tabs = st.tabs(["📋 基本信息", "🧪 实验条件", "📊 数据表", "📈 快速预览"])
    
    with tabs[0]:
        display_basic_info(exp_data)
    
    with tabs[1]:
        display_experimental_conditions(exp_data)
    
    with tabs[2]:
        display_data_tables(exp_data)
    
    with tabs[3]:
        display_quick_preview(exp_data)


def display_basic_info(exp_data):
    """显示基本信息"""
    # 元数据
    if 'metadata' in exp_data:
        st.write("**📄 文件元数据**")
        metadata = exp_data['metadata']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"• 作者: {metadata.get('author', 'N/A')}")
            st.write(f"• DOI: {metadata.get('doi', 'N/A')}")
            if 'version' in metadata:
                version = metadata['version']
                if isinstance(version, dict):
                    st.write(f"• 版本: {version.get('major', 0)}.{version.get('minor', 0)}")
                else:
                    st.write(f"• 版本: {version}")
        
        with col2:
            st.write(f"• 首次发布: {metadata.get('first_publication', 'N/A')}")
            st.write(f"• 最后修改: {metadata.get('last_modification', 'N/A')}")
    
    # 文献信息
    if 'bibliography' in exp_data and exp_data['bibliography']:
        st.write("**📚 文献信息**")
        bib = exp_data['bibliography']
        if 'details' in bib:
            details = bib['details']
            st.write(f"• 标题: {details.get('title', 'N/A')}")
            st.write(f"• 作者: {details.get('author', 'N/A')}")
            st.write(f"• 期刊: {details.get('journal', 'N/A')} ({details.get('year', 'N/A')})")
        st.write(f"• DOI: {bib.get('doi', 'N/A')}")


def display_experimental_conditions(exp_data):
    """显示实验条件"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🔬 实验类型**")
        st.info(exp_data.get('experiment_type', 'N/A'))
    
    with col2:
        st.write("**🔧 实验设备**")
        if 'apparatus' in exp_data:
            apparatus = exp_data['apparatus']
            if isinstance(apparatus, dict):
                st.info(apparatus.get('kind', 'N/A'))
            else:
                st.info(str(apparatus))
    
    # 通用属性
    if 'common_properties' in exp_data:
        st.write("**⚙️ 实验条件**")
        props = exp_data['common_properties']
        
        # 显示属性
        prop_data = []
        for key, value in props.items():
            if key != 'initial_composition':
                if isinstance(value, dict):
                    prop_data.append({
                        '参数': key,
                        '值': value.get('value', ''),
                        '单位': value.get('units', '')
                    })
                else:
                    prop_data.append({
                        '参数': key,
                        '值': value,
                        '单位': ''
                    })
        
        if prop_data:
            df = pd.DataFrame(prop_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 显示初始组分
        if 'initial_composition' in props:
            st.write("**🧪 初始组分**")
            comp = props['initial_composition']
            comp_data = []
            for species, info in comp.items():
                if isinstance(info, dict):
                    comp_data.append({
                        '物种': species,
                        '含量': f"{info.get('amount', '')} {info.get('units', '')}",
                        'CAS': info.get('CAS', ''),
                        'SMILES': info.get('SMILES', '')
                    })
                else:
                    comp_data.append({
                        '物种': species,
                        '含量': str(info),
                        'CAS': '',
                        'SMILES': ''
                    })
            
            if comp_data:
                df_comp = pd.DataFrame(comp_data)
                st.dataframe(df_comp, use_container_width=True, hide_index=True)


def display_data_tables(exp_data):
    """显示数据表"""
    datagroups = exp_data.get('datagroups', [])
    
    if not datagroups:
        st.warning("没有数据组")
        return
    
    for i, dg in enumerate(datagroups):
        group_id = dg.get('id', f'group_{i+1}')
        group_name = dg.get('name', f'数据组 {i+1}')
        
        with st.expander(f"📊 {group_name} (ID: {group_id})", expanded=(i==0)):
            # 显示统计信息
            if 'statistics' in dg:
                stats = dg['statistics']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("数据点", stats.get('num_points', 0))
                with col2:
                    st.metric("数据列", len(stats.get('columns', [])))
                with col3:
                    shape = stats.get('shape', [0, 0])
                    st.metric("维度", f"{shape[0]}×{shape[1]}")
            
            # 显示数据表
            if 'data_df' in dg and dg['data_df'] is not None:
                df = dg['data_df']
                st.dataframe(df, use_container_width=True, height=400)
                
                # 下载选项
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 下载CSV",
                    data=csv,
                    file_name=f"data_{group_id}.csv",
                    mime="text/csv",
                    key=f"download_{group_id}"
                )
            elif 'datapoints' in dg and dg['datapoints']:
                # 如果没有data_df但有datapoints，尝试创建DataFrame
                try:
                    df = pd.DataFrame(dg['datapoints'])
                    st.dataframe(df, use_container_width=True, height=400)
                except:
                    st.info("数据格式不支持表格显示")


def display_quick_preview(exp_data):
    """快速预览数据"""
    datagroups = exp_data.get('datagroups', [])
    
    if not datagroups:
        st.warning("没有可预览的数据")
        return
    
    # 选择数据组
    group_names = []
    for i, dg in enumerate(datagroups):
        name = dg.get('name', f'数据组 {i+1}')
        group_names.append(name)
    
    selected_idx = st.selectbox("选择数据组", range(len(group_names)), 
                                format_func=lambda x: group_names[x])
    
    if selected_idx is not None:
        dg = datagroups[selected_idx]
        
        if 'data_df' in dg and dg['data_df'] is not None:
            df = dg['data_df']
            
            # 简单绘图
            if len(df.columns) >= 2:
                col1, col2 = st.columns(2)
                
                with col1:
                    x_col = st.selectbox("X轴", df.columns, key="preview_x")
                
                with col2:
                    available_y = [c for c in df.columns if c != x_col]
                    y_col = st.selectbox("Y轴", available_y, key="preview_y")
                
                if x_col and y_col:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df[x_col],
                        y=df[y_col],
                        mode='lines+markers',
                        name=y_col
                    ))
                    
                    fig.update_layout(
                        xaxis_title=x_col,
                        yaxis_title=y_col,
                        height=400,
                        template="plotly_white"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)


def visualize_data():
    """数据可视化"""
    st.header("📊 数据可视化")
    
    if not st.session_state.experiment_loaded or not st.session_state.current_experiment:
        st.warning("请先加载实验文件")
        return
    
    exp_data = st.session_state.current_experiment
    datagroups = exp_data.get('datagroups', [])
    
    if not datagroups:
        st.warning("没有可视化的数据")
        return
    
    # 选择数据组
    group_names = []
    for i, dg in enumerate(datagroups):
        name = dg.get('name', f'数据组 {i+1}')
        group_names.append(name)
    
    selected_idx = st.selectbox("选择数据组", range(len(group_names)), 
                                format_func=lambda x: group_names[x])
    
    dg = datagroups[selected_idx]
    
    if 'data_df' not in dg or dg['data_df'] is None:
        st.warning("选中的数据组没有可视化数据")
        return
    
    df = dg['data_df']
    
    # 绘图控制
    col1, col2, col3 = st.columns(3)
    
    with col1:
        x_col = st.selectbox("X轴", df.columns)
    
    with col2:
        available_y = [c for c in df.columns if c != x_col]
        y_cols = st.multiselect("Y轴（可多选）", available_y)
    
    with col3:
        chart_type = st.selectbox("图表类型", ["折线图", "散点图", "折线+散点", "柱状图"])
    
    # 高级选项
    with st.expander("高级选项"):
        col1, col2, col3 = st.columns(3)
        with col1:
            x_scale = st.selectbox("X轴缩放", ["线性", "对数"])
            y_scale = st.selectbox("Y轴缩放", ["线性", "对数"])
        with col2:
            show_grid = st.checkbox("显示网格", value=True)
            show_legend = st.checkbox("显示图例", value=True)
        with col3:
            height = st.slider("图表高度", 400, 800, 500)
    
    if y_cols:
        # 创建图表
        fig = go.Figure()
        
        for y_col in y_cols:
            if chart_type == "折线图":
                fig.add_trace(go.Scatter(
                    x=df[x_col], y=df[y_col],
                    mode='lines', name=y_col
                ))
            elif chart_type == "散点图":
                fig.add_trace(go.Scatter(
                    x=df[x_col], y=df[y_col],
                    mode='markers', name=y_col
                ))
            elif chart_type == "折线+散点":
                fig.add_trace(go.Scatter(
                    x=df[x_col], y=df[y_col],
                    mode='lines+markers', name=y_col
                ))
            elif chart_type == "柱状图":
                fig.add_trace(go.Bar(
                    x=df[x_col], y=df[y_col],
                    name=y_col
                ))
        
        # 更新布局
        fig.update_layout(
            title=dg.get('name', '数据可视化'),
            xaxis_title=x_col,
            yaxis_title="值",
            template="plotly_white",
            showlegend=show_legend,
            height=height,
            hovermode='x unified'
        )
        
        # 设置轴类型
        if x_scale == "对数":
            fig.update_xaxes(type="log")
        if y_scale == "对数":
            fig.update_yaxes(type="log")
        
        # 网格设置
        fig.update_xaxes(showgrid=show_grid)
        fig.update_yaxes(showgrid=show_grid)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 数据统计
        if st.checkbox("显示统计信息"):
            st.markdown("### 📊 数据统计")
            stats_data = []
            for y_col in y_cols:
                values = df[y_col].dropna()
                stats_data.append({
                    "数据系列": y_col,
                    "最小值": values.min(),
                    "最大值": values.max(),
                    "平均值": values.mean(),
                    "标准差": values.std(),
                    "数据点数": len(values)
                })
            
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)


def analyze_data():
    """数据分析"""
    st.header("📈 数据分析")
    
    if not st.session_state.experiment_loaded or not st.session_state.current_experiment:
        st.warning("请先加载实验文件")
        return
    
    exp_data = st.session_state.current_experiment
    datagroups = exp_data.get('datagroups', [])
    
    if not datagroups:
        st.warning("没有可分析的数据")
        return
    
    # 选择分析类型
    analysis_type = st.selectbox(
        "选择分析类型",
        ["基础统计", "相关性分析", "趋势分析", "数据对比"]
    )
    
    if analysis_type == "基础统计":
        # 选择数据组
        group_names = [dg.get('name', f'数据组 {i+1}') for i, dg in enumerate(datagroups)]
        selected_idx = st.selectbox("选择数据组", range(len(group_names)), 
                                   format_func=lambda x: group_names[x])
        
        dg = datagroups[selected_idx]
        if 'data_df' in dg and dg['data_df'] is not None:
            df = dg['data_df']
            
            st.markdown("### 📊 描述性统计")
            st.dataframe(df.describe(), use_container_width=True)
            
            # 选择列进行详细分析
            selected_col = st.selectbox("选择列进行详细分析", df.columns)
            
            if selected_col:
                col1, col2 = st.columns(2)
                
                with col1:
                    # 直方图
                    fig_hist = go.Figure()
                    fig_hist.add_trace(go.Histogram(x=df[selected_col], name=selected_col))
                    fig_hist.update_layout(
                        title=f"{selected_col} 分布",
                        xaxis_title=selected_col,
                        yaxis_title="频数",
                        height=400
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                with col2:
                    # 箱线图
                    fig_box = go.Figure()
                    fig_box.add_trace(go.Box(y=df[selected_col], name=selected_col))
                    fig_box.update_layout(
                        title=f"{selected_col} 箱线图",
                        yaxis_title=selected_col,
                        height=400
                    )
                    st.plotly_chart(fig_box, use_container_width=True)
    
    elif analysis_type == "相关性分析":
        # 选择数据组
        group_names = [dg.get('name', f'数据组 {i+1}') for i, dg in enumerate(datagroups)]
        selected_idx = st.selectbox("选择数据组", range(len(group_names)), 
                                   format_func=lambda x: group_names[x])
        
        dg = datagroups[selected_idx]
        if 'data_df' in dg and dg['data_df'] is not None:
            df = dg['data_df']
            
            # 计算相关性矩阵
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                
                # 热力图
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale='RdBu',
                    zmid=0,
                    text=corr_matrix.values.round(2),
                    texttemplate='%{text}',
                    textfont={"size": 10},
                    colorbar=dict(title="相关系数")
                ))
                
                fig.update_layout(
                    title="相关性矩阵热力图",
                    height=600
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示强相关对
                st.markdown("### 强相关变量对（|r| > 0.7）")
                strong_corr = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        corr_val = corr_matrix.iloc[i, j]
                        if abs(corr_val) > 0.7:
                            strong_corr.append({
                                '变量1': corr_matrix.columns[i],
                                '变量2': corr_matrix.columns[j],
                                '相关系数': corr_val
                            })
                
                if strong_corr:
                    st.dataframe(pd.DataFrame(strong_corr), hide_index=True)
                else:
                    st.info("没有发现强相关的变量对")


def convert_data():
    """数据转换"""
    st.header("🔄 数据转换")
    
    # 单位转换工具
    st.subheader("单位转换器")
    
    converter = UnitConverter()
    
    conversion_type = st.selectbox(
        "选择转换类型",
        ["温度", "压力", "浓度", "流量"]
    )
    
    col1, col2, col3 = st.columns(3)
    
    if conversion_type == "温度":
        with col1:
            value = st.number_input("输入值", value=25.0)
        with col2:
            from_unit = st.selectbox("从", ["K", "C", "F"])
        with col3:
            to_unit = st.selectbox("到", ["K", "C", "F"])
        
        if st.button("转换"):
            result = converter.temperature(value, from_unit, to_unit)
            st.success(f"{value} {from_unit} = {result:.2f} {to_unit}")
    
    elif conversion_type == "压力":
        with col1:
            value = st.number_input("输入值", value=1.0)
        with col2:
            from_unit = st.selectbox("从", UNITS['pressure'])
        with col3:
            to_unit = st.selectbox("到", UNITS['pressure'])
        
        if st.button("转换"):
            result = converter.pressure(value, from_unit, to_unit)
            st.success(f"{value} {from_unit} = {result:.6f} {to_unit}")


def export_data():
    """数据导出"""
    st.header("📥 数据导出")
    
    if not st.session_state.experiment_loaded or not st.session_state.current_experiment:
        st.warning("请先加载实验文件")
        return
    
    exp_data = st.session_state.current_experiment
    
    export_format = st.selectbox(
        "选择导出格式",
        ["JSON", "CSV (所有数据组)", "Excel", "Python字典"]
    )
    
    if export_format == "JSON":
        if st.button("生成JSON"):
            json_str = json.dumps(exp_data, indent=2, default=str, ensure_ascii=False)
            st.download_button(
                label="下载JSON文件",
                data=json_str,
                file_name=f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            with st.expander("JSON预览"):
                st.code(json_str[:2000] + "..." if len(json_str) > 2000 else json_str, 
                       language='json')
    
    elif export_format == "CSV (所有数据组)":
        if st.button("生成CSV文件"):
            datagroups = exp_data.get('datagroups', [])
            
            if datagroups:
                # 创建ZIP文件
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
                    with zipfile.ZipFile(tmp_zip.name, 'w') as zf:
                        for i, dg in enumerate(datagroups):
                            if 'data_df' in dg and dg['data_df'] is not None:
                                df = dg['data_df']
                                csv_content = df.to_csv(index=False)
                                filename = f"{dg.get('id', f'group_{i+1}')}_{dg.get('name', 'data')}.csv"
                                zf.writestr(filename, csv_content)
                    
                    with open(tmp_zip.name, 'rb') as f:
                        zip_data = f.read()
                    
                    os.unlink(tmp_zip.name)
                
                st.download_button(
                    label="下载所有CSV (ZIP)",
                    data=zip_data,
                    file_name=f"experiment_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip"
                )
            else:
                st.warning("没有可导出的数据组")
    
    elif export_format == "Python字典":
        if st.button("显示Python代码"):
            code = f"""# Python字典格式的实验数据
import pandas as pd

experiment_data = {{
    'experiment_type': '{exp_data.get('experiment_type', 'N/A')}',
    'datagroups': []
}}

# 添加数据组
"""
            st.code(code, language='python')


# 添加页脚
def add_footer():
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        <p>燃烧实验数据管理系统 v1.0</p>
        <p>支持ReSpecTh XML格式 | 数据分析与可视化</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
    add_footer()
