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
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

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
if 'new_exp_data' not in st.session_state:
    st.session_state.new_exp_data = {}
if 'composition_list' not in st.session_state:
    st.session_state.composition_list = []
if 'optional_params' not in st.session_state:
    st.session_state.optional_params = {}
if 'data_groups_new' not in st.session_state:
    st.session_state.data_groups_new = []
if 'current_dg_columns' not in st.session_state:
    st.session_state.current_dg_columns = []


def main():
    """主函数"""
    st.title("🔥 燃烧实验数据管理系统")
    st.markdown("---")
    
    # 侧边栏
    with st.sidebar:
        st.header("📍 功能选择")
        mode = st.radio(
            "选择操作模式",
            ["📂 加载文件", "✨ 新建实验", "📊 数据可视化", "📈 数据分析", "🔄 数据转换", "📥 数据导出"]
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
        
        # 新建实验状态
        if st.session_state.data_groups_new:
            st.success(f"📊 新建数据组: {len(st.session_state.data_groups_new)}")
        
        st.markdown("---")
        
        # 快速操作
        if st.button("🗑️ 清除所有数据", use_container_width=True):
            for key in ['current_experiment', 'new_exp_data', 'composition_list', 
                       'optional_params', 'data_groups_new', 'current_dg_columns']:
                if key in st.session_state:
                    if key in ['current_experiment']:
                        st.session_state[key] = None
                    elif key == 'experiment_loaded':
                        st.session_state[key] = False
                    else:
                        st.session_state[key] = [] if key != 'new_exp_data' and key != 'optional_params' else {}
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
    elif mode == "✨ 新建实验":
        create_new_experiment()
    elif mode == "📊 数据可视化":
        visualize_data()
    elif mode == "📈 数据分析":
        analyze_data()
    elif mode == "🔄 数据转换":
        convert_data()
    elif mode == "📥 数据导出":
        export_data()


def create_new_experiment():
    """新建实验数据 - 增强版"""
    st.header("✨ 新建实验数据")
    
    # 使用标签页组织
    tabs = st.tabs(["📋 基本信息", "⚙️ 实验条件", "🔬 可选参数", "📊 数据组管理", "💾 生成XML"])
    
    with tabs[0]:
        create_basic_info()
    
    with tabs[1]:
        create_experimental_conditions()
    
    with tabs[2]:
        create_optional_parameters()
    
    with tabs[3]:
        manage_data_groups()
    
    with tabs[4]:
        generate_xml_enhanced()


def create_basic_info():
    """创建基本信息"""
    st.subheader("📋 基本信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 作者信息
        author = st.text_input("作者姓名 *", key="new_author", 
                               placeholder="例如: John Smith")
        doi = st.text_input("DOI (可选)", key="new_doi",
                           placeholder="10.1234/example.2024")
        
        # 实验类型
        exp_type = st.selectbox(
            "实验类型 *",
            EXPERIMENT_TYPES,
            key="new_exp_type"
        )
        
        # 反应器类型
        reactor = st.selectbox(
            "反应器类型 *",
            list(REACTOR_TYPES.keys()),
            format_func=lambda x: REACTOR_TYPES[x],
            key="new_reactor"
        )
    
    with col2:
        # 描述
        description = st.text_area(
            "实验描述",
            height=100,
            key="new_description",
            placeholder="详细描述实验条件和目的..."
        )
        
        # 参考文献
        st.markdown("**参考文献（可选）**")
        ref_author = st.text_input("文献作者", key="ref_author")
        ref_title = st.text_input("文献标题", key="ref_title")
        ref_journal = st.text_input("期刊", key="ref_journal")
        ref_year = st.number_input("年份", min_value=1900, max_value=2100, value=2024, key="ref_year")
        ref_doi = st.text_input("文献DOI", key="ref_doi")
    
    # 保存基本信息
    if st.button("保存基本信息", type="primary", key="save_basic"):
        if author and exp_type and reactor:
            st.session_state.new_exp_data['basic_info'] = {
                'author': author,
                'doi': doi,
                'exp_type': exp_type,
                'reactor': reactor,
                'description': description,
                'reference': {
                    'author': ref_author,
                    'title': ref_title,
                    'journal': ref_journal,
                    'year': ref_year,
                    'doi': ref_doi
                }
            }
            st.success("✅ 基本信息已保存")
        else:
            st.error("请填写所有必填项（带*号）")


def create_experimental_conditions():
    """创建实验条件 - 必需参数"""
    st.subheader("⚙️ 实验条件（必需参数）")
    
    # 温度和压力
    st.markdown("### 🌡️ 基本参数")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        temp = st.number_input("温度 *", min_value=0.0, value=300.0, key="new_temp")
        temp_unit = st.selectbox("温度单位", UNITS['temperature'], key="new_temp_unit")
    
    with col2:
        pressure = st.number_input("压力 *", min_value=0.0, value=1.0, key="new_pressure")
        pressure_unit = st.selectbox("压力单位", UNITS['pressure'], key="new_pressure_unit")
    
    with col3:
        # 根据反应器类型显示必需参数
        reactor = st.session_state.new_exp_data.get('basic_info', {}).get('reactor', 'JSR')
        required_params = get_required_params_for_reactor(reactor)
        
        st.markdown(f"**{reactor} 特定参数**")
        reactor_params = {}
        
        if 'residence_time' in required_params:
            reactor_params['residence_time'] = st.number_input(
                "停留时间 (s)", min_value=0.0, value=1.0, key="residence_time")
        
        if 'volume' in required_params:
            reactor_params['volume'] = st.number_input(
                "体积 (cm³)", min_value=0.0, value=100.0, key="volume")
        
        if 'flow_rate' in required_params:
            reactor_params['flow_rate'] = st.number_input(
                "流量 (sccm)", min_value=0.0, value=100.0, key="flow_rate")
        
        if 'length' in required_params:
            reactor_params['length'] = st.number_input(
                "长度 (cm)", min_value=0.0, value=10.0, key="length")
        
        if 'diameter' in required_params:
            reactor_params['diameter'] = st.number_input(
                "直径 (cm)", min_value=0.0, value=1.0, key="diameter")
        
        if 'ignition_delay' in required_params:
            reactor_params['ignition_delay'] = st.number_input(
                "点火延迟 (ms)", min_value=0.0, value=1.0, key="ignition_delay")
    
    # 初始组分
    st.markdown("### 🧪 初始组分 *")
    
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1, 0.5])
    
    with col1:
        species = st.selectbox(
            "物种",
            ["自定义"] + list(COMMON_SPECIES.keys()),
            key="species_select"
        )
        if species == "自定义":
            species = st.text_input("输入物种名称", key="custom_species")
    
    with col2:
        amount = st.number_input("含量", min_value=0.0, format="%.6f", key="species_amount")
    
    with col3:
        units = st.selectbox("单位", UNITS['composition'], key="species_units")
    
    with col4:
        # CAS号（可选）
        cas_number = st.text_input("CAS号", key="cas_number", placeholder="可选")
    
    with col5:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕", help="添加物种"):
            if species and amount > 0:
                comp_entry = {
                    'species': species,
                    'amount': amount,
                    'units': units
                }
                
                # 如果是已知物种，添加额外信息
                if species in COMMON_SPECIES:
                    comp_entry.update(COMMON_SPECIES[species])
                elif cas_number:
                    comp_entry['CAS'] = cas_number
                
                st.session_state.composition_list.append(comp_entry)
                st.success(f"✅ 已添加 {species}")
                st.rerun()
    
    # 显示当前组分
    if st.session_state.composition_list:
        st.markdown("**当前组分：**")
        comp_df = pd.DataFrame(st.session_state.composition_list)
        
        # 编辑和删除功能
        col1, col2 = st.columns([4, 1])
        with col1:
            st.dataframe(comp_df[['species', 'amount', 'units']], use_container_width=True)
        with col2:
            if st.button("🗑️ 清除所有", key="clear_comp"):
                st.session_state.composition_list = []
                st.rerun()
        
        # 验证组分总和
        if all(c['units'] == 'mole_fraction' for c in st.session_state.composition_list):
            total = sum(c['amount'] for c in st.session_state.composition_list)
            if abs(total - 1.0) > 0.01:
                st.warning(f"⚠️ 摩尔分数总和为 {total:.4f}，应该为 1.0")
    
    # 保存实验条件
    if st.button("保存实验条件", type="primary", key="save_conditions"):
        if temp > 0 and pressure > 0 and st.session_state.composition_list:
            conditions = {
                'temperature': {'value': temp, 'units': temp_unit},
                'pressure': {'value': pressure, 'units': pressure_unit},
                'composition': st.session_state.composition_list,
                'reactor_params': reactor_params
            }
            
            st.session_state.new_exp_data['conditions'] = conditions
            st.success("✅ 实验条件已保存")
        else:
            st.error("请填写温度、压力并至少添加一个组分")


def create_optional_parameters():
    """创建可选参数"""
    st.subheader("🔬 可选参数")
    
    st.info("以下参数为可选，根据实验需要填写")
    
    # 使用列布局组织参数
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 反应条件")
        
        # 当量比
        equiv_ratio = st.number_input(
            "当量比 (φ)", 
            min_value=0.0, 
            value=0.0,
            format="%.3f",
            help="0表示不设置",
            key="equiv_ratio"
        )
        
        # 燃料
        fuel = st.text_input("燃料", key="fuel", placeholder="例如: CH4")
        
        # 氧化剂
        oxidizer = st.text_input("氧化剂", key="oxidizer", placeholder="例如: Air")
        
        # 稀释气体
        diluent = st.text_input("稀释气体", key="diluent", placeholder="例如: N2, Ar")
        
        # 反射激波条件（如果适用）
        if st.session_state.new_exp_data.get('basic_info', {}).get('reactor') == 'shock_tube':
            st.markdown("### 激波管参数")
            reflected_T = st.number_input("反射激波温度 (K)", min_value=0.0, value=0.0, key="reflected_T")
            reflected_P = st.number_input("反射激波压力 (atm)", min_value=0.0, value=0.0, key="reflected_P")
    
    with col2:
        st.markdown("### 测量与诊断")
        
        # 点火判据
        ignition_criterion = st.selectbox(
            "点火判据",
            ["无"] + IGNITION_CRITERIA,
            key="ignition_criterion"
        )
        
        # 点火类型
        ignition_type = st.selectbox(
            "点火类型",
            ["无"] + list(IGNITION_TYPES.keys()),
            format_func=lambda x: "无" if x == "无" else IGNITION_TYPES.get(x, x),
            key="ignition_type_select"
        )
        
        # 诊断方法
        diagnostics = st.multiselect(
            "诊断方法",
            list(DIAGNOSTIC_METHODS.keys()),
            format_func=lambda x: DIAGNOSTIC_METHODS[x],
            key="diagnostics"
        )
        
        # 不确定度
        uncertainty_type = st.selectbox(
            "不确定度类型",
            ["无"] + UNCERTAINTY_TYPES,
            key="uncertainty_type"
        )
        
        if uncertainty_type != "无":
            uncertainty_value = st.number_input(
                "不确定度值 (%)", 
                min_value=0.0, 
                max_value=100.0,
                value=5.0,
                key="uncertainty_value"
            )
    
    # 额外备注
    st.markdown("### 📝 备注")
    comments = st.text_area(
        "实验备注",
        height=100,
        key="exp_comments",
        placeholder="任何额外的实验信息..."
    )
    
    # 保存可选参数
    if st.button("保存可选参数", type="primary", key="save_optional"):
        optional = {}
        
        if equiv_ratio > 0:
            optional['equivalence_ratio'] = equiv_ratio
        if fuel:
            optional['fuel'] = fuel
        if oxidizer:
            optional['oxidizer'] = oxidizer
        if diluent:
            optional['diluent'] = diluent
        
        if ignition_criterion != "无":
            optional['ignition_criterion'] = ignition_criterion
        if ignition_type != "无":
            optional['ignition_type'] = ignition_type
        
        if diagnostics:
            optional['diagnostics'] = diagnostics
        
        if uncertainty_type != "无":
            optional['uncertainty'] = {
                'type': uncertainty_type,
                'value': uncertainty_value if 'uncertainty_value' in locals() else 0
            }
        
        if comments:
            optional['comments'] = comments
        
        # 激波管特定参数
        if 'reflected_T' in st.session_state and st.session_state.reflected_T > 0:
            optional['reflected_shock_temperature'] = st.session_state.reflected_T
        if 'reflected_P' in st.session_state and st.session_state.reflected_P > 0:
            optional['reflected_shock_pressure'] = st.session_state.reflected_P
        
        st.session_state.optional_params = optional
        st.success(f"✅ 已保存 {len(optional)} 个可选参数")


def manage_data_groups():
    """管理数据组 - 支持多数据组和多列"""
    st.subheader("📊 数据组管理")
    
    # 显示现有数据组
    if st.session_state.data_groups_new:
        st.info(f"当前有 {len(st.session_state.data_groups_new)} 个数据组")
        
        # 列出所有数据组
        for idx, dg in enumerate(st.session_state.data_groups_new):
            with st.expander(f"数据组 {idx+1}: {dg['name']}", expanded=False):
                st.write(f"**ID:** {dg['id']}")
                st.write(f"**列数:** {len(dg['columns'])}")
                st.write(f"**数据点:** {len(dg['data']) if 'data' in dg else 0}")
                
                if 'data' in dg and dg['data']:
                    df = pd.DataFrame(dg['data'])
                    st.dataframe(df.head(10), use_container_width=True)
                
                # 删除按钮
                if st.button(f"删除数据组 {idx+1}", key=f"delete_dg_{idx}"):
                    st.session_state.data_groups_new.pop(idx)
                    st.rerun()
    
    st.markdown("---")
    
    # 创建新数据组
    st.markdown("### ➕ 创建新数据组")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        dg_name = st.text_input("数据组名称", key="new_dg_name", 
                                placeholder="例如: Temperature Profile")
    with col2:
        dg_id = st.text_input("数据组ID", key="new_dg_id",
                             value=f"dg{len(st.session_state.data_groups_new)+1}")
    
    # 定义数据列
    st.markdown("#### 定义数据列")
    
    # X轴（独立变量）
    with st.container():
        st.markdown("**X轴（独立变量）**")
        col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])
        
        with col1:
            x_name = st.text_input("X轴名称", value="Temperature", key="x_name_new")
        with col2:
            x_unit = st.selectbox("X轴单位", UNITS['temperature'], key="x_unit_new")
        with col3:
            x_label = st.text_input("X轴标签", value="T", key="x_label_new")
        with col4:
            x_id = st.text_input("X轴ID", value="x1", key="x_id_new")
    
    # Y轴（因变量） - 支持多列
    st.markdown("**Y轴（因变量）- 可添加多列**")
    
    # 添加新列
    col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1, 1, 0.5])
    
    with col1:
        y_name = st.text_input("列名称", key="y_name_add", placeholder="例如: CH4")
    with col2:
        y_unit = st.selectbox("单位", UNITS['composition'], key="y_unit_add")
    with col3:
        y_species = st.selectbox("关联物种", ["无"] + list(COMMON_SPECIES.keys()), key="y_species_add")
    with col4:
        y_label = st.text_input("标签", key="y_label_add", placeholder="可选")
    with col5:
        y_id = st.text_input("ID", value=f"x{len(st.session_state.current_dg_columns)+2}", key="y_id_add")
    with col6:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕", help="添加列", key="add_column"):
            if y_name:
                col_info = {
                    'name': y_name,
                    'unit': y_unit,
                    'species': y_species if y_species != "无" else None,
                    'label': y_label or y_name,
                    'id': y_id,
                    'type': 'y'
                }
                st.session_state.current_dg_columns.append(col_info)
                st.success(f"✅ 已添加列: {y_name}")
                st.rerun()
    
    # 显示当前列
    if st.session_state.current_dg_columns:
        st.markdown("**当前Y轴列：**")
        cols_df = pd.DataFrame(st.session_state.current_dg_columns)
        st.dataframe(cols_df[['name', 'unit', 'species', 'id']], use_container_width=True)
        
        if st.button("清除所有列", key="clear_columns"):
            st.session_state.current_dg_columns = []
            st.rerun()
    
    # 数据输入方式
    st.markdown("#### 输入数据")
    
    input_method = st.radio(
        "选择数据输入方式",
        ["📝 手动输入", "📋 粘贴数据", "📁 上传文件"],
        key="dg_input_method"
    )
    
    data_ready = False
    data_to_save = None
    
    if input_method == "📝 手动输入":
        if x_name and st.session_state.current_dg_columns:
            n_points = st.number_input("数据点数量", min_value=1, max_value=1000, value=10, key="n_points_manual")
            
            # 创建数据表
            columns = [x_name] + [col['name'] for col in st.session_state.current_dg_columns]
            df = pd.DataFrame(0.0, index=range(n_points), columns=columns)
            
            # 数据编辑器
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                num_rows="dynamic",
                key="dg_data_editor"
            )
            
            if st.button("确认数据", key="confirm_manual_data"):
                data_to_save = edited_df
                data_ready = True
        else:
            st.warning("请先定义X轴和至少一个Y轴列")
    
    elif input_method == "📋 粘贴数据":
        csv_text = st.text_area(
            "粘贴CSV/TSV数据（第一行为列名）",
            height=200,
            key="paste_dg_data"
        )
        
        if st.button("解析数据", key="parse_paste"):
            if csv_text:
                try:
                    from io import StringIO
                    df = pd.read_csv(StringIO(csv_text))
                    st.success("✅ 数据解析成功")
                    st.dataframe(df.head(), use_container_width=True)
                    
                    # 列映射
                    st.markdown("**列映射**")
                    col_mapping = {}
                    
                    # X轴映射
                    x_map = st.selectbox(f"X轴 ({x_name}) 对应列", df.columns, key="x_map")
                    col_mapping[x_name] = x_map
                    
                    # Y轴映射
                    for col in st.session_state.current_dg_columns:
                        y_map = st.selectbox(
                            f"{col['name']} 对应列",
                            ["无"] + list(df.columns),
                            key=f"y_map_{col['id']}"
                        )
                        if y_map != "无":
                            col_mapping[col['name']] = y_map
                    
                    if st.button("确认映射", key="confirm_mapping"):
                        # 根据映射创建新DataFrame
                        new_df = pd.DataFrame()
                        for new_col, old_col in col_mapping.items():
                            if old_col in df.columns:
                                new_df[new_col] = df[old_col]
                        
                        data_to_save = new_df
                        data_ready = True
                        
                except Exception as e:
                    st.error(f"解析失败: {e}")
    
    elif input_method == "📁 上传文件":
        uploaded_file = st.file_uploader(
            "选择CSV或Excel文件",
            type=['csv', 'xlsx', 'xls'],
            key="upload_dg_file"
        )
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.success("✅ 文件加载成功")
                st.dataframe(df.head(), use_container_width=True)
                
                # 使用相同的列映射逻辑
                st.markdown("**列映射**")
                col_mapping = {}
                
                x_map = st.selectbox(f"X轴 ({x_name}) 对应列", df.columns, key="x_map_file")
                col_mapping[x_name] = x_map
                
                for col in st.session_state.current_dg_columns:
                    y_map = st.selectbox(
                        f"{col['name']} 对应列",
                        ["无"] + list(df.columns),
                        key=f"y_map_file_{col['id']}"
                    )
                    if y_map != "无":
                        col_mapping[col['name']] = y_map
                
                if st.button("确认映射", key="confirm_file_mapping"):
                    new_df = pd.DataFrame()
                    for new_col, old_col in col_mapping.items():
                        if old_col in df.columns:
                            new_df[new_col] = df[old_col]
                    
                    data_to_save = new_df
                    data_ready = True
                    
            except Exception as e:
                st.error(f"文件加载失败: {e}")
    
    # 保存数据组
    if data_ready and data_to_save is not None:
        if st.button("💾 保存数据组", type="primary", key="save_datagroup"):
            if dg_name and dg_id:
                # 构建数据组结构
                datagroup = {
                    'id': dg_id,
                    'name': dg_name,
                    'x_axis': {
                        'name': x_name,
                        'unit': x_unit,
                        'label': x_label,
                        'id': x_id
                    },
                    'y_axes': st.session_state.current_dg_columns,
                    'columns': [x_name] + [col['name'] for col in st.session_state.current_dg_columns],
                    'data': data_to_save.to_dict('records')
                }
                
                st.session_state.data_groups_new.append(datagroup)
                st.session_state.current_dg_columns = []  # 清空当前列定义
                st.success(f"✅ 数据组 '{dg_name}' 已保存！")
                st.rerun()
            else:
                st.error("请填写数据组名称和ID")


def generate_xml_enhanced():
    """生成XML文件 - 增强版"""
    st.subheader("💾 生成XML文件")
    
    # 检查数据完整性
    checks = {
        '基本信息': 'basic_info' in st.session_state.new_exp_data,
        '实验条件': 'conditions' in st.session_state.new_exp_data,
        '可选参数': bool(st.session_state.optional_params),
        '数据组': bool(st.session_state.data_groups_new)
    }
    
    # 显示检查状态
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if checks['基本信息']:
            st.success("✅ 基本信息")
        else:
            st.error("❌ 基本信息")
    
    with col2:
        if checks['实验条件']:
            st.success("✅ 实验条件")
        else:
            st.error("❌ 实验条件")
    
    with col3:
        if checks['可选参数']:
            st.info(f"✅ 可选参数 ({len(st.session_state.optional_params)})")
        else:
            st.info("⭕ 无可选参数")
    
    with col4:
        if checks['数据组']:
            st.success(f"✅ 数据组 ({len(st.session_state.data_groups_new)})")
        else:
            st.error("❌ 无数据组")
    
    # 必须有基本信息、实验条件和至少一个数据组
    can_generate = checks['基本信息'] and checks['实验条件'] and checks['数据组']
    
    if can_generate:
        st.markdown("---")
        
        # 预览信息
        with st.expander("📋 预览实验信息"):
            basic = st.session_state.new_exp_data.get('basic_info', {})
            st.write(f"**作者:** {basic.get('author')}")
            st.write(f"**实验类型:** {basic.get('exp_type')}")
            st.write(f"**反应器:** {basic.get('reactor')}")
            
            conditions = st.session_state.new_exp_data.get('conditions', {})
            st.write(f"**温度:** {conditions.get('temperature', {}).get('value')} {conditions.get('temperature', {}).get('units')}")
            st.write(f"**压力:** {conditions.get('pressure', {}).get('value')} {conditions.get('pressure', {}).get('units')}")
            st.write(f"**组分数:** {len(conditions.get('composition', []))}")
            
            st.write(f"**数据组数:** {len(st.session_state.data_groups_new)}")
            for dg in st.session_state.data_groups_new:
                st.write(f"  - {dg['name']}: {len(dg['columns'])} 列, {len(dg.get('data', []))} 数据点")
    
    # 生成按钮
    if st.button("🚀 生成XML文件", type="primary", disabled=not can_generate, key="generate_xml"):
        try:
            xml_content = create_enhanced_xml()
            
            # 提供下载
            st.download_button(
                label="📥 下载XML文件",
                data=xml_content,
                file_name=f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
                mime="application/xml"
            )
            
            # 显示预览
            with st.expander("XML预览（前2000字符）"):
                st.code(xml_content[:2000] + "..." if len(xml_content) > 2000 else xml_content, 
                       language='xml')
            
            st.success("✅ XML文件生成成功！")
            
        except Exception as e:
            st.error(f"❌ 生成失败: {e}")
            import traceback
            with st.expander("错误详情"):
                st.code(traceback.format_exc())
    
    if not can_generate:
        st.warning("⚠️ 请完成基本信息、实验条件的填写，并至少创建一个数据组")


def create_enhanced_xml():
    """创建增强版XML内容"""
    root = ET.Element('experiment')
    
    # 1. 文件元数据
    basic_info = st.session_state.new_exp_data.get('basic_info', {})
    
    ET.SubElement(root, 'fileAuthor').text = basic_info.get('author', 'Unknown')
    if basic_info.get('doi'):
        ET.SubElement(root, 'fileDOI').text = basic_info['doi']
    
    # 版本信息
    version_elem = ET.SubElement(root, 'fileVersion')
    ET.SubElement(version_elem, 'major').text = '1'
    ET.SubElement(version_elem, 'minor').text = '0'
    
    # 2. 实验类型和设备
    ET.SubElement(root, 'experimentType').text = basic_info.get('exp_type', '')
    
    apparatus_elem = ET.SubElement(root, 'apparatus')
    ET.SubElement(apparatus_elem, 'kind').text = basic_info.get('reactor', 'JSR')
    
    # 3. 参考文献
    ref = basic_info.get('reference', {})
    if ref.get('author') and ref.get('title'):
        bib_elem = ET.SubElement(root, 'bibliographyLink')
        details = ET.SubElement(bib_elem, 'details')
        ET.SubElement(details, 'author').text = ref['author']
        ET.SubElement(details, 'title').text = ref['title']
        if ref.get('journal'):
            ET.SubElement(details, 'journal').text = ref['journal']
        if ref.get('year'):
            ET.SubElement(details, 'year').text = str(ref['year'])
        if ref.get('doi'):
            ET.SubElement(bib_elem, 'referenceDOI').text = ref['doi']
    
    # 4. 通用属性（必需参数和可选参数）
    common_props = ET.SubElement(root, 'commonProperties')
    conditions = st.session_state.new_exp_data.get('conditions', {})
    
    # 温度
    if 'temperature' in conditions:
        temp_prop = ET.SubElement(common_props, 'property', 
                                 attrib={'name': 'temperature',
                                        'label': 'T',
                                        'units': conditions['temperature']['units'],
                                        'sourcetype': 'reported'})
        ET.SubElement(temp_prop, 'value').text = str(conditions['temperature']['value'])
    
    # 压力
    if 'pressure' in conditions:
        press_prop = ET.SubElement(common_props, 'property',
                                   attrib={'name': 'pressure',
                                          'label': 'P',
                                          'units': conditions['pressure']['units'],
                                          'sourcetype': 'reported'})
        ET.SubElement(press_prop, 'value').text = str(conditions['pressure']['value'])
    
    # 反应器特定参数
    reactor_params = conditions.get('reactor_params', {})
    for param_name, param_value in reactor_params.items():
        if param_value and param_value > 0:
            param_prop = ET.SubElement(common_props, 'property',
                                      attrib={'name': param_name.replace('_', ' '),
                                             'sourcetype': 'reported'})
            ET.SubElement(param_prop, 'value').text = str(param_value)
    
    # 可选参数
    optional = st.session_state.optional_params
    for key, value in optional.items():
        if key in ['equivalence_ratio', 'fuel', 'oxidizer', 'diluent']:
            opt_prop = ET.SubElement(common_props, 'property',
                                    attrib={'name': key.replace('_', ' '),
                                           'sourcetype': 'reported'})
            ET.SubElement(opt_prop, 'value').text = str(value)
    
    # 初始组分
    if 'composition' in conditions and conditions['composition']:
        comp_prop = ET.SubElement(common_props, 'property',
                                  attrib={'name': 'initial composition',
                                         'sourcetype': 'reported'})
        
        for comp in conditions['composition']:
            comp_elem = ET.SubElement(comp_prop, 'component')
            
            species_attrib = {'preferredKey': comp['species']}
            if 'CAS' in comp:
                species_attrib['CAS'] = comp['CAS']
            if 'chemName' in comp:
                species_attrib['chemName'] = comp['chemName']
            if 'InChI' in comp:
                species_attrib['InChI'] = comp['InChI']
            if 'SMILES' in comp:
                species_attrib['SMILES'] = comp['SMILES']
            
            ET.SubElement(comp_elem, 'speciesLink', attrib=species_attrib)
            ET.SubElement(comp_elem, 'amount', 
                         attrib={'units': comp['units']}).text = str(comp['amount'])
    
    # 5. 数据组
    for dg in st.session_state.data_groups_new:
        dg_elem = ET.SubElement(root, 'dataGroup', 
                               attrib={'id': dg['id'], 'label': dg['name']})
        
        # 定义属性（列）
        # X轴
        x_info = dg['x_axis']
        x_prop = ET.SubElement(dg_elem, 'property',
                              attrib={'id': x_info['id'],
                                     'name': x_info['name'],
                                     'label': x_info['label'],
                                     'units': x_info['unit'],
                                     'sourcetype': 'digitized'})
        
        # Y轴
        for y_info in dg['y_axes']:
            y_attrib = {
                'id': y_info['id'],
                'name': y_info['name'],
                'label': y_info.get('label', y_info['name']),
                'units': y_info['unit'],
                'sourcetype': 'digitized'
            }
            
            y_prop = ET.SubElement(dg_elem, 'property', attrib=y_attrib)
            
            # 如果有物种信息
            if y_info.get('species') and y_info['species'] in COMMON_SPECIES:
                species_info = COMMON_SPECIES[y_info['species']]
                species_attrib = {'preferredKey': y_info['species']}
                species_attrib.update(species_info)
                ET.SubElement(y_prop, 'speciesLink', attrib=species_attrib)
        
        # 添加数据点
        for row in dg.get('data', []):
            dp_elem = ET.SubElement(dg_elem, 'dataPoint')
            
            # X值
            x_name = x_info['name']
            if x_name in row:
                ET.SubElement(dp_elem, x_info['id']).text = str(row[x_name])
            
            # Y值
            for y_info in dg['y_axes']:
                y_name = y_info['name']
                if y_name in row:
                    ET.SubElement(dp_elem, y_info['id']).text = str(row[y_name])
    
    # 美化XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="    ")
    
    # 移除空行
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    return '\n'.join(lines)


# 保留其他原有函数不变...
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


# 保留所有其他原有函数（display_experiment_summary, display_experiment_details, 
# visualize_data, analyze_data, convert_data, export_data等）不变...

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


def convert_data():
    """数据转换"""
    st.header("🔄 数据转换")
    
    # 单位转换工具
    st.subheader("单位转换器")
    
    converter = UnitConverter()
    
    conversion_type = st.selectbox(
        "选择转换类型",
        ["温度", "压力", "浓度"]
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


# 添加页脚
def add_footer():
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        <p>燃烧实验数据管理系统 v2.0</p>
        <p>支持ReSpecTh XML格式 | 完整实验参数 | 多数据组管理</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
    add_footer()
