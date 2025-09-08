"""
燃烧实验数据管理系统 - 完整单文件版本
Combustion Experiment Data Management System
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import tempfile
import zipfile
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from typing import Dict, List, Any, Optional, Union
import logging

# ==================== 设置日志 ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 常量定义 ====================

# 反应器类型
REACTOR_TYPES = {
    'JSR': 'Jet Stirred Reactor',
    'FR': 'Flow Reactor', 
    'PFR': 'Plug Flow Reactor',
    'CSTR': 'Continuously Stirred Tank Reactor',
    'shock_tube': 'Shock Tube',
    'RCM': 'Rapid Compression Machine',
    'flat_flame': 'Flat Flame Burner',
    'counterflow': 'Counterflow Burner',
    'spherical_bomb': 'Spherical Bomb',
    'engine': 'Engine'
}

# 常见物种
COMMON_SPECIES = {
    'CH4': {'CAS': '74-82-8', 'chemName': 'methane', 'InChI': '1S/CH4/h1H4', 'SMILES': 'C'},
    'O2': {'CAS': '7782-44-7', 'chemName': 'oxygen', 'InChI': '1S/O2/c1-2', 'SMILES': 'O=O'},
    'N2': {'CAS': '7727-37-9', 'chemName': 'nitrogen', 'InChI': '1S/N2/c1-2', 'SMILES': 'N#N'},
    'CO': {'CAS': '630-08-0', 'chemName': 'carbon monoxide', 'InChI': '1S/CO/c1-2', 'SMILES': '[C-]#[O+]'},
    'CO2': {'CAS': '124-38-9', 'chemName': 'carbon dioxide', 'InChI': '1S/CO2/c2-1-3', 'SMILES': 'C(=O)=O'},
    'H2O': {'CAS': '7732-18-5', 'chemName': 'water', 'InChI': '1S/H2O/h1H2', 'SMILES': 'O'},
    'H2': {'CAS': '1333-74-0', 'chemName': 'hydrogen', 'InChI': '1S/H2/h1H', 'SMILES': '[H][H]'},
    'NH3': {'CAS': '7664-41-7', 'chemName': 'ammonia', 'InChI': '1S/H3N/h1H3', 'SMILES': 'N'},
    'NO': {'CAS': '10102-43-9', 'chemName': 'nitric oxide', 'InChI': '1S/NO/c1-2', 'SMILES': '[N]=O'},
    'NO2': {'CAS': '10102-44-0', 'chemName': 'nitrogen dioxide', 'InChI': '1S/NO2/c2-1-3', 'SMILES': 'N(=O)[O]'},
    'N2O': {'CAS': '10024-97-2', 'chemName': 'nitrous oxide', 'InChI': '1S/N2O/c1-2-3', 'SMILES': 'N#[N+][O-]'},
    'Ar': {'CAS': '7440-37-1', 'chemName': 'argon', 'InChI': '1S/Ar', 'SMILES': '[Ar]'},
    'He': {'CAS': '7440-59-7', 'chemName': 'helium', 'InChI': '1S/He', 'SMILES': '[He]'},
}

# 单位类型
UNITS = {
    'temperature': ['K', 'C', 'F', 'R'],
    'pressure': ['atm', 'bar', 'Pa', 'kPa', 'MPa', 'Torr', 'psi'],
    'composition': ['mole_fraction', 'ppm', 'ppb', 'mass_fraction', 'percent'],
    'time': ['s', 'ms', 'us', 'ns', 'min', 'h'],
    'flow_rate': ['sccm', 'slpm', 'mol/s', 'kg/s'],
    'volume': ['cm3', 'm3', 'L', 'mL'],
    'length': ['m', 'cm', 'mm', 'inch', 'ft'],
}

# 必需参数
REQUIRED_PARAMS = {
    'JSR': ['temperature', 'pressure', 'residence_time', 'volume'],
    'FR': ['temperature', 'pressure', 'flow_rate', 'length', 'diameter'],
    'shock_tube': ['temperature', 'pressure', 'ignition_delay'],
    'RCM': ['compressed_temperature', 'compressed_pressure', 'ignition_delay'],
    'default': ['temperature', 'pressure', 'composition']
}

# 实验类型
EXPERIMENT_TYPES = [
    'ignition_delay',
    'flame_speed',
    'laminar_flame_speed',
    'species_profile',
    'temperature_profile',
    'pressure_profile',
]

# 点火判据
IGNITION_CRITERIA = [
    'OH*',
    'CH*',
    'pressure_rise',
    'dp/dt_max',
    'temperature_rise',
]

# 点火类型
IGNITION_TYPES = {
    'reflected_shock': '反射激波',
    'incident_shock': '入射激波',
    'compression': '压缩点火',
    'spark': '电火花点火',
}

# 诊断方法
DIAGNOSTIC_METHODS = {
    'pressure_transducer': '压力传感器',
    'OH_emission': 'OH*发射光谱',
    'CH_emission': 'CH*发射光谱',
    'laser_absorption': '激光吸收',
}

# 不确定度类型
UNCERTAINTY_TYPES = [
    'absolute',
    'relative',
    'percentage',
]

OPTIONAL_PARAMS = [
    'equivalence_ratio',
    'phi',
    'fuel',
    'oxidizer',
    'bath_gas',
    'diluent',
]

def get_required_params_for_reactor(reactor_type):
    """根据反应器类型获取必需参数"""
    return REQUIRED_PARAMS.get(reactor_type, REQUIRED_PARAMS.get('default', []))

# ==================== XML解析器 ====================

class XMLParser:
    """XML解析器类"""
    
    def __init__(self):
        self.namespaces = {}
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """解析XML文件"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            return self.parse_experiment(root)
        except Exception as e:
            logger.error(f"解析XML文件失败: {e}")
            raise
    
    def parse_experiment(self, root: ET.Element) -> Dict[str, Any]:
        """解析实验根节点"""
        exp_data = {}
        
        exp_data['metadata'] = self.parse_metadata(root)
        exp_data['experiment_type'] = self._get_text(root, 'experimentType')
        exp_data['apparatus'] = self.parse_apparatus(root)
        exp_data['bibliography'] = self.parse_bibliography(root)
        exp_data['common_properties'] = self.parse_common_properties(root)
        exp_data['datagroups'] = self.parse_datagroups(root)
        
        return exp_data
    
    def parse_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """解析文件元数据"""
        metadata = {}
        metadata['author'] = self._get_text(root, 'fileAuthor')
        metadata['doi'] = self._get_text(root, 'fileDOI')
        
        file_version = root.find('fileVersion')
        if file_version is not None:
            metadata['version'] = {
                'major': self._get_text(file_version, 'major'),
                'minor': self._get_text(file_version, 'minor')
            }
        
        metadata['first_publication'] = self._get_text(root, 'firstPublicationDate')
        metadata['last_modification'] = self._get_text(root, 'lastModificationDate')
        
        return metadata
    
    def parse_apparatus(self, root: ET.Element) -> Dict[str, Any]:
        """解析实验设备信息"""
        apparatus = {}
        app_elem = root.find('apparatus')
        if app_elem is not None:
            apparatus['kind'] = self._get_text(app_elem, 'kind')
            apparatus['type'] = app_elem.get('type', '')
        return apparatus
    
    def parse_bibliography(self, root: ET.Element) -> Dict[str, Any]:
        """解析文献信息"""
        bibliography = {}
        bib_elem = root.find('bibliographyLink')
        if bib_elem is not None:
            bibliography['description'] = self._get_text(bib_elem, 'description')
            bibliography['doi'] = self._get_text(bib_elem, 'referenceDOI')
            
            details = bib_elem.find('details')
            if details is not None:
                bibliography['details'] = {
                    'author': self._get_text(details, 'author'),
                    'journal': self._get_text(details, 'journal'),
                    'title': self._get_text(details, 'title'),
                    'year': self._get_text(details, 'year'),
                }
        
        return bibliography
    
    def parse_common_properties(self, root: ET.Element) -> Dict[str, Any]:
        """解析通用属性"""
        properties = {}
        common_props = root.find('commonProperties')
        
        if common_props is not None:
            for prop in common_props.findall('property'):
                name = prop.get('name', '')
                label = prop.get('label', '')
                units = prop.get('units', '')
                
                value_elem = prop.find('value')
                if value_elem is not None:
                    value = value_elem.text
                    try:
                        value = float(value)
                    except:
                        pass
                else:
                    value = prop.text
                
                key = label if label else name
                properties[key] = {
                    'value': value,
                    'units': units,
                    'name': name,
                }
            
            # 解析初始组分
            initial_comp = common_props.find(".//property[@name='initial composition']")
            if initial_comp is not None:
                composition = {}
                for component in initial_comp.findall('component'):
                    species_link = component.find('speciesLink')
                    amount = component.find('amount')
                    
                    if species_link is not None and amount is not None:
                        species_key = species_link.get('preferredKey', '')
                        composition[species_key] = {
                            'amount': float(amount.text) if amount.text else 0,
                            'units': amount.get('units', ''),
                        }
                
                properties['initial_composition'] = composition
        
        return properties
    
    def parse_datagroups(self, root: ET.Element) -> List[Dict[str, Any]]:
        """解析数据组"""
        datagroups = []
        
        for dg in root.findall('.//dataGroup'):
            dg_data = {
                'id': dg.get('id', ''),
                'label': dg.get('label', ''),
                'properties': [],
                'property_map': {},
                'datapoints': [],
                'data_df': None
            }
            
            property_map = {}
            column_order = []
            
            for prop in dg.findall('property'):
                prop_id = prop.get('id')
                prop_info = {
                    'id': prop_id,
                    'name': prop.get('name', ''),
                    'label': prop.get('label', ''),
                    'units': prop.get('units', ''),
                }
                
                species_link = prop.find('speciesLink')
                if species_link is not None:
                    prop_info['species'] = {
                        'preferredKey': species_link.get('preferredKey', ''),
                    }
                    column_name = f"{prop_info['species']['preferredKey']} ({prop_info['units']})"
                else:
                    if prop_info['label']:
                        column_name = f"{prop_info['label']} ({prop_info['units']})" if prop_info['units'] else prop_info['label']
                    else:
                        column_name = f"{prop_info['name']} ({prop_info['units']})" if prop_info['units'] else prop_info['name']
                
                prop_info['column_name'] = column_name
                property_map[prop_id] = prop_info
                column_order.append(prop_id)
                dg_data['properties'].append(prop_info)
            
            dg_data['property_map'] = property_map
            
            # 解析数据点
            data_rows = []
            
            for dp in dg.findall('dataPoint'):
                point_data = {}
                
                for child in dp:
                    prop_id = child.tag
                    value_text = child.text
                    
                    if prop_id in property_map:
                        prop_info = property_map[prop_id]
                        column_name = prop_info['column_name']
                        
                        try:
                            value = float(value_text)
                        except (ValueError, TypeError):
                            value = value_text
                        
                        point_data[column_name] = value
                
                if point_data:
                    dg_data['datapoints'].append(point_data)
                    data_rows.append(point_data)
            
            if data_rows:
                df = pd.DataFrame(data_rows)
                
                display_columns = [col for col in df.columns if not col.startswith('_')]
                ordered_columns = []
                for prop_id in column_order:
                    if prop_id in property_map:
                        col_name = property_map[prop_id]['column_name']
                        if col_name in display_columns:
                            ordered_columns.append(col_name)
                
                for col in display_columns:
                    if col not in ordered_columns:
                        ordered_columns.append(col)
                
                if ordered_columns:
                    df = df[ordered_columns]
                
                dg_data['data_df'] = df
                dg_data['statistics'] = {
                    'num_points': len(df),
                    'columns': list(df.columns),
                    'shape': df.shape
                }
                
                logger.info(f"数据组 {dg.get('id', 'unknown')}: 解析了 {len(df)} 个数据点，{len(df.columns)} 列")
            
            datagroups.append(dg_data)
        
        return datagroups
    
    def _get_text(self, parent: ET.Element, tag: str, default: str = '') -> str:
        """获取元素文本的辅助方法"""
        elem = parent.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return default

def parse_experiment_xml(file_path: str) -> Dict[str, Any]:
    """解析实验XML文件的便捷函数"""
    parser = XMLParser()
    return parser.parse_file(file_path)

def validate_xml_structure(file_path: str) -> tuple[bool, List[str]]:
    """验证XML文件结构"""
    errors = []
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        required_elements = ['experimentType', 'apparatus', 'commonProperties']
        for elem_name in required_elements:
            if root.find(elem_name) is None:
                errors.append(f"缺少必需元素: {elem_name}")
        
        datagroups = root.findall('.//dataGroup')
        if not datagroups:
            errors.append("没有找到数据组")
        
        return len(errors) == 0, errors
        
    except ET.ParseError as e:
        errors.append(f"XML解析错误: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"验证过程出错: {e}")
        return False, errors

# ==================== 单位转换器 ====================

class UnitConverter:
    """单位转换器"""
    
    @staticmethod
    def temperature(value, from_unit: str, to_unit: str):
        """温度单位转换"""
        if from_unit == to_unit:
            return value
        
        # 先转到K
        if from_unit == 'C':
            kelvin = value + 273.15
        elif from_unit == 'F':
            kelvin = (value - 32) * 5/9 + 273.15
        else:
            kelvin = value
        
        # 从K转到目标单位
        if to_unit == 'C':
            return kelvin - 273.15
        elif to_unit == 'F':
            return (kelvin - 273.15) * 9/5 + 32
        else:
            return kelvin
    
    @staticmethod
    def pressure(value, from_unit: str, to_unit: str):
        """压力单位转换"""
        if from_unit == to_unit:
            return value
        
        # 转换因子（到Pa）
        to_pa = {
            'Pa': 1,
            'kPa': 1000,
            'MPa': 1e6,
            'bar': 1e5,
            'atm': 101325,
            'Torr': 133.322,
            'psi': 6894.76
        }
        
        # 转换
        pa_value = value * to_pa.get(from_unit, 1)
        return pa_value / to_pa.get(to_unit, 1)

# ==================== 页面配置 ====================

st.set_page_config(
    page_title="燃烧实验数据管理系统",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 初始化session state ====================

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

# ==================== 主函数 ====================

def main():
    """主函数"""
    st.title("🔥 燃烧实验数据管理系统")
    st.markdown("---")
    
    # 侧边栏
    with st.sidebar:
        st.header("📍 功能选择")
        mode = st.radio(
            "选择操作模式",
            ["📂 加载文件", "✨ 新建实验", "📊 数据可视化", "📥 数据导出"]
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
    
    # 主页面内容路由
    if mode == "📂 加载文件":
        load_experiment_file()
    elif mode == "✨ 新建实验":
        create_new_experiment()
    elif mode == "📊 数据可视化":
        visualize_data()
    elif mode == "📥 数据导出":
        export_data()

# ==================== 加载文件功能 ====================

def load_experiment_file():
    """加载实验数据"""
    st.header("📂 加载实验数据")
    
    uploaded_file = st.file_uploader(
        "选择XML文件",
        type=['xml'],
        help="支持ReSpecTh格式的XML文件"
    )
    
    if uploaded_file is not None:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("文件名", uploaded_file.name)
        with col2:
            st.metric("文件大小", f"{uploaded_file.size / 1024:.2f} KB")
        with col3:
            st.metric("文件类型", uploaded_file.type or "XML")
        
        if st.button("🔄 解析文件", type="primary", use_container_width=True):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                with st.spinner("验证文件结构..."):
                    is_valid, errors = validate_xml_structure(tmp_path)
                
                if not is_valid:
                    st.error("❌ XML文件结构验证失败：")
                    for error in errors:
                        st.error(f"  • {error}")
                    os.unlink(tmp_path)
                    return
                
                with st.spinner("正在解析XML文件..."):
                    exp_data = parse_experiment_xml(tmp_path)
                
                os.unlink(tmp_path)
                
                if exp_data:
                    st.session_state.current_experiment = exp_data
                    st.session_state.experiment_loaded = True
                    st.success(f"✅ 成功加载实验数据！")
                    display_experiment_summary(exp_data)
                else:
                    st.error("❌ 解析失败：未能提取数据")
                    
            except Exception as e:
                st.error(f"❌ 加载文件失败: {str(e)}")
    
    if st.session_state.experiment_loaded and st.session_state.current_experiment:
        st.markdown("---")
        display_experiment_details(st.session_state.current_experiment)

# ==================== 新建实验功能 ====================

def create_new_experiment():
    """新建实验数据"""
    st.header("✨ 新建实验数据")
    
    tabs = st.tabs(["📋 基本信息", "⚙️ 实验条件", "📊 数据组管理", "💾 生成XML"])
    
    with tabs[0]:
        create_basic_info()
    
    with tabs[1]:
        create_experimental_conditions()
    
    with tabs[2]:
        manage_data_groups()
    
    with tabs[3]:
        generate_xml_enhanced()

def create_basic_info():
    """创建基本信息"""
    st.subheader("📋 基本信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        author = st.text_input("作者姓名 *", key="new_author")
        doi = st.text_input("DOI (可选)", key="new_doi")
        exp_type = st.selectbox("实验类型 *", EXPERIMENT_TYPES, key="new_exp_type")
        reactor = st.selectbox(
            "反应器类型 *",
            list(REACTOR_TYPES.keys()),
            format_func=lambda x: REACTOR_TYPES[x],
            key="new_reactor"
        )
    
    with col2:
        description = st.text_area("实验描述", height=100, key="new_description")
        st.markdown("**参考文献（可选）**")
        ref_author = st.text_input("文献作者", key="ref_author")
        ref_title = st.text_input("文献标题", key="ref_title")
    
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
                }
            }
            st.success("✅ 基本信息已保存")
        else:
            st.error("请填写所有必填项（带*号）")

def create_experimental_conditions():
    """创建实验条件"""
    st.subheader("⚙️ 实验条件")
    
    col1, col2 = st.columns(2)
    
    with col1:
        temp = st.number_input("温度 *", min_value=0.0, value=300.0, key="new_temp")
        temp_unit = st.selectbox("温度单位", UNITS['temperature'], key="new_temp_unit")
    
    with col2:
        pressure = st.number_input("压力 *", min_value=0.0, value=1.0, key="new_pressure")
        pressure_unit = st.selectbox("压力单位", UNITS['pressure'], key="new_pressure_unit")
    
    # 初始组分
    st.markdown("### 🧪 初始组分")
    
    col1, col2, col3, col4 = st.columns([2, 2, 1.5, 0.5])
    
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
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕"):
            if species and amount > 0:
                comp_entry = {
                    'species': species,
                    'amount': amount,
                    'units': units
                }
                
                if species in COMMON_SPECIES:
                    comp_entry.update(COMMON_SPECIES[species])
                
                st.session_state.composition_list.append(comp_entry)
                st.success(f"✅ 已添加 {species}")
                st.rerun()
    
    if st.session_state.composition_list:
        st.markdown("**当前组分：**")
        comp_df = pd.DataFrame(st.session_state.composition_list)
        st.dataframe(comp_df[['species', 'amount', 'units']], use_container_width=True)
        
        if st.button("清除所有组分"):
            st.session_state.composition_list = []
            st.rerun()
    
    if st.button("保存实验条件", type="primary"):
        if temp > 0 and pressure > 0 and st.session_state.composition_list:
            st.session_state.new_exp_data['conditions'] = {
                'temperature': {'value': temp, 'units': temp_unit},
                'pressure': {'value': pressure, 'units': pressure_unit},
                'composition': st.session_state.composition_list
            }
            st.success("✅ 实验条件已保存")
        else:
            st.error("请填写温度、压力并至少添加一个组分")

def manage_data_groups():
    """管理数据组"""
    st.subheader("📊 数据组管理")
    
    if st.session_state.data_groups_new:
        st.info(f"当前有 {len(st.session_state.data_groups_new)} 个数据组")
        
        for idx, dg in enumerate(st.session_state.data_groups_new):
            with st.expander(f"数据组 {idx+1}: {dg['name']}", expanded=False):
                st.write(f"**ID:** {dg['id']}")
                st.write(f"**列数:** {len(dg.get('columns', []))}")
                
                if st.button(f"删除", key=f"delete_dg_{idx}"):
                    st.session_state.data_groups_new.pop(idx)
                    st.rerun()
    
    st.markdown("---")
    st.markdown("### ➕ 创建新数据组")
    
    dg_name = st.text_input("数据组名称", key="new_dg_name")
    dg_id = st.text_input("数据组ID", value=f"dg{len(st.session_state.data_groups_new)+1}", key="new_dg_id")
    
    # 简单的数据输入
    st.markdown("#### 输入数据")
    
    n_cols = st.number_input("列数", min_value=2, max_value=20, value=2, key="n_cols")
    n_rows = st.number_input("行数", min_value=1, max_value=1000, value=10, key="n_rows")
    
    # 创建数据表
    columns = [f"Column_{i+1}" for i in range(n_cols)]
    df = pd.DataFrame(0.0, index=range(n_rows), columns=columns)
    
    edited_df = st.data_editor(df, use_container_width=True, key="dg_data_editor")
    
    if st.button("保存数据组", type="primary"):
        if dg_name and dg_id:
            datagroup = {
                'id': dg_id,
                'name': dg_name,
                'columns': list(edited_df.columns),
                'data': edited_df.to_dict('records')
            }
            
            st.session_state.data_groups_new.append(datagroup)
            st.success(f"✅ 数据组 '{dg_name}' 已保存！")
            st.rerun()

def generate_xml_enhanced():
    """生成XML文件"""
    st.subheader("💾 生成XML文件")
    
    # 检查数据完整性
    has_basic = 'basic_info' in st.session_state.new_exp_data
    has_conditions = 'conditions' in st.session_state.new_exp_data
    has_data = bool(st.session_state.data_groups_new)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if has_basic:
            st.success("✅ 基本信息")
        else:
            st.error("❌ 基本信息")
    
    with col2:
        if has_conditions:
            st.success("✅ 实验条件")
        else:
            st.error("❌ 实验条件")
    
    with col3:
        if has_data:
            st.success(f"✅ 数据组 ({len(st.session_state.data_groups_new)})")
        else:
            st.warning("⚠️ 无数据组")
    
    can_generate = has_basic and has_conditions
    
    if st.button("🚀 生成XML文件", type="primary", disabled=not can_generate):
        try:
            xml_content = create_enhanced_xml()
            
            st.download_button(
                label="📥 下载XML文件",
                data=xml_content,
                file_name=f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
                mime="application/xml"
            )
            
            st.success("✅ XML文件生成成功！")
            
        except Exception as e:
            st.error(f"❌ 生成失败: {e}")

def create_enhanced_xml():
    """创建XML内容"""
    root = ET.Element('experiment')
    
    # 基本信息
    basic_info = st.session_state.new_exp_data.get('basic_info', {})
    
    ET.SubElement(root, 'fileAuthor').text = basic_info.get('author', 'Unknown')
    if basic_info.get('doi'):
        ET.SubElement(root, 'fileDOI').text = basic_info['doi']
    
    ET.SubElement(root, 'experimentType').text = basic_info.get('exp_type', '')
    
    apparatus_elem = ET.SubElement(root, 'apparatus')
    ET.SubElement(apparatus_elem, 'kind').text = basic_info.get('reactor', 'JSR')
    
    # 通用属性
    common_props = ET.SubElement(root, 'commonProperties')
    conditions = st.session_state.new_exp_data.get('conditions', {})
    
    if 'temperature' in conditions:
        temp_prop = ET.SubElement(common_props, 'property', 
                                 attrib={'name': 'temperature',
                                        'units': conditions['temperature']['units']})
        ET.SubElement(temp_prop, 'value').text = str(conditions['temperature']['value'])
    
    if 'pressure' in conditions:
        press_prop = ET.SubElement(common_props, 'property',
                                   attrib={'name': 'pressure',
                                          'units': conditions['pressure']['units']})
        ET.SubElement(press_prop, 'value').text = str(conditions['pressure']['value'])
    
    # 初始组分
    if 'composition' in conditions and conditions['composition']:
        comp_prop = ET.SubElement(common_props, 'property',
                                  attrib={'name': 'initial composition'})
        
        for comp in conditions['composition']:
            comp_elem = ET.SubElement(comp_prop, 'component')
            
            species_attrib = {'preferredKey': comp['species']}
            if 'CAS' in comp:
                species_attrib['CAS'] = comp['CAS']
            
            ET.SubElement(comp_elem, 'speciesLink', attrib=species_attrib)
            ET.SubElement(comp_elem, 'amount', 
                         attrib={'units': comp['units']}).text = str(comp['amount'])
    
    # 数据组
    for dg in st.session_state.data_groups_new:
        dg_elem = ET.SubElement(root, 'dataGroup', attrib={'id': dg['id']})
        
        # 定义属性
        for i, col in enumerate(dg['columns']):
            ET.SubElement(dg_elem, 'property',
                         attrib={'id': f'x{i+1}', 'name': col})
        
        # 数据点
        for row in dg.get('data', []):
            dp_elem = ET.SubElement(dg_elem, 'dataPoint')
            for i, col in enumerate(dg['columns']):
                if col in row:
                    ET.SubElement(dp_elem, f'x{i+1}').text = str(row[col])
    
    # 美化XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="    ")
    
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    return '\n'.join(lines)

# ==================== 显示功能 ====================

def display_experiment_summary(exp_data):
    """显示实验数据摘要"""
    st.markdown("### 📋 数据摘要")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("实验类型", exp_data.get('experiment_type', 'N/A'))
    with col2:
        st.metric("数据组数量", len(exp_data.get('datagroups', [])))
    with col3:
        total_points = sum(len(dg.get('datapoints', [])) for dg in exp_data.get('datagroups', []))
        st.metric("总数据点", total_points)

def display_experiment_details(exp_data):
    """显示实验详细信息"""
    st.subheader("📊 实验数据详情")
    
    tabs = st.tabs(["📋 基本信息", "🧪 实验条件", "📊 数据表"])
    
    with tabs[0]:
        if 'metadata' in exp_data:
            metadata = exp_data['metadata']
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**作者:** {metadata.get('author', 'N/A')}")
                st.write(f"**DOI:** {metadata.get('doi', 'N/A')}")
            with col2:
                st.write(f"**版本:** {metadata.get('version', 'N/A')}")
    
    with tabs[1]:
        if 'common_properties' in exp_data:
            props = exp_data['common_properties']
            prop_data = []
            for key, value in props.items():
                if key != 'initial_composition' and isinstance(value, dict):
                    prop_data.append({
                        '参数': key,
                        '值': value.get('value', ''),
                        '单位': value.get('units', '')
                    })
            if prop_data:
                df = pd.DataFrame(prop_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tabs[2]:
        datagroups = exp_data.get('datagroups', [])
        for i, dg in enumerate(datagroups):
            with st.expander(f"数据组 {i+1}", expanded=(i==0)):
                if 'data_df' in dg and dg['data_df'] is not None:
                    st.dataframe(dg['data_df'], use_container_width=True)

# ==================== 数据可视化 ====================

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
    selected_idx = st.selectbox("选择数据组", range(len(datagroups)))
    dg = datagroups[selected_idx]
    
    if 'data_df' in dg and dg['data_df'] is not None:
        df = dg['data_df']
        
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("X轴", df.columns)
        with col2:
            y_col = st.selectbox("Y轴", [c for c in df.columns if c != x_col])
        
        if x_col and y_col:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], mode='lines+markers'))
            fig.update_layout(xaxis_title=x_col, yaxis_title=y_col, height=400)
            st.plotly_chart(fig, use_container_width=True)

# ==================== 数据导出 ====================

def export_data():
    """数据导出"""
    st.header("📥 数据导出")
    
    if not st.session_state.experiment_loaded or not st.session_state.current_experiment:
        st.warning("请先加载实验文件")
        return
    
    exp_data = st.session_state.current_experiment
    
    if st.button("生成JSON"):
        json_str = json.dumps(exp_data, indent=2, default=str, ensure_ascii=False)
        st.download_button(
            label="下载JSON文件",
            data=json_str,
            file_name=f"experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# ==================== 主程序入口 ====================

if __name__ == "__main__":
    main()
    
    # 页脚
    st.markdown("---")
    st.markdown(
        """<div style='text-align: center; color: gray;'>
        <p>燃烧实验数据管理系统 v2.0 | 支持ReSpecTh XML格式</p>
        </div>""",
        unsafe_allow_html=True
    )
