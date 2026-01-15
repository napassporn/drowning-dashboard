import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from datetime import datetime
import json
import folium
from folium.plugins import HeatMap
from branca.element import Element
import base64
from io import BytesIO
import numpy as np
import os
import plotly.io as pio

# ลองโหลด geopandas (ถ้ามี)
try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    print("ไม่พบ geopandas - จะใช้ CircleMarker แทน Shapefile")

# สร้าง Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# =============== โหลดโลโก้เป็น Base64 ===============
def load_logo_base64(filepath):
    """โหลดไฟล์รูปภาพเป็น base64 string"""
    try:
        with open(filepath, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
            ext = filepath.lower().split('.')[-1]
            if ext == 'png':
                return f"data:image/png;base64,{encoded}"
            elif ext in ['jpg', 'jpeg']:
                return f"data:image/jpeg;base64,{encoded}"
            elif ext == 'gif':
                return f"data:image/gif;base64,{encoded}"
            else:
                return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"ไม่สามารถโหลดโลโก้จาก {filepath}: {e}")
        return None

# โหลดโลโก้
LOGO_GD_PATH = "gd.png" 
LOGO_KK_PATH = "kk.png"
LOGO_GD_BASE64 = load_logo_base64(LOGO_GD_PATH)
LOGO_KK_BASE64 = load_logo_base64(LOGO_KK_PATH)

# =============== กำหนดชื่อคอลัมน์ ===============
COLUMN_MAPPING = {
    'province': 'จังหวัดที่เกิดเหตุ',
    'district': 'อำเภอที่เกิดเหตุ',
    'subdistrict': 'ตำบลที่เกิดเหตุ',
    'zone': 'สคร',
    'month': 'เดือนที่เกิดเหตุ',
    'year': 'ปีที่เกิดเหตุ',
    'age': 'อายุ (ปี)',
    'status': 'สถานะ'
}

# =============== พิกัดจังหวัดไทย ===============
PROVINCE_COORDS = {
    "กระบี่": [99.0, 8.0], "กรุงเทพมหานคร": [100.5, 13.75], "กาญจนบุรี": [99.5, 14.0],
    "กาฬสินธุ์": [103.5, 16.5], "กำแพงเพชร": [99.5, 16.5], "ขอนแก่น": [102.8, 16.4],
    "จันทบุรี": [102.1, 12.6], "ฉะเชิงเทรา": [101.1, 13.7], "ชลบุรี": [101.0, 13.4],
    "ชัยนาท": [100.1, 15.2], "ชัยภูมิ": [102.0, 15.8], "ชุมพร": [99.2, 10.5],
    "เชียงราย": [99.8, 19.9], "เชียงใหม่": [98.9, 18.8], "ตรัง": [99.6, 7.6],
    "ตราด": [102.5, 12.2], "ตาก": [99.1, 16.9], "นครนายก": [101.2, 14.2],
    "นครปฐม": [100.1, 13.8], "นครพนม": [104.8, 17.4], "นครราชสีมา": [102.1, 14.9],
    "นครศรีธรรมราช": [99.9, 8.4], "นครสวรรค์": [100.1, 15.7], "นนทบุรี": [100.5, 13.9],
    "นราธิวาส": [101.8, 6.4], "น่าน": [100.8, 18.8], "บึงกาฬ": [103.6, 18.4],
    "บุรีรัมย์": [103.1, 14.9], "ปทุมธานี": [100.5, 14.0], "ประจวบคีรีขันธ์": [99.8, 11.8],
    "ปราจีนบุรี": [101.4, 14.1], "ปัตตานี": [101.3, 6.9], "พระนครศรีอยุธยา": [100.6, 14.4],
    "พะเยา": [100.0, 19.2], "พังงา": [98.5, 8.5], "พัทลุง": [100.1, 7.6],
    "พิจิตร": [100.3, 16.4], "พิษณุโลก": [100.3, 16.8], "เพชรบุรี": [99.9, 13.1],
    "เพชรบูรณ์": [101.2, 16.4], "แพร่": [100.1, 18.1], "ภูเก็ต": [98.4, 7.9],
    "มหาสารคาม": [103.3, 16.2], "มุกดาหาร": [104.7, 16.5], "แม่ฮ่องสอน": [97.9, 19.3],
    "ยโสธร": [104.1, 15.8], "ยะลา": [101.3, 6.5], "ร้อยเอ็ด": [103.7, 16.1],
    "ระนอง": [98.6, 9.9], "ระยอง": [101.3, 12.7], "ราชบุรี": [99.8, 13.5],
    "ลพบุรี": [100.6, 14.8], "ลำปาง": [99.5, 18.3], "ลำพูน": [99.0, 18.6],
    "เลย": [101.7, 17.5], "ศรีสะเกษ": [104.3, 15.1], "สกลนคร": [104.1, 17.2],
    "สงขลา": [100.5, 7.2], "สตูล": [100.1, 6.6], "สมุทรปราการ": [100.6, 13.6],
    "สมุทรสงคราม": [100.0, 13.4], "สมุทรสาคร": [100.3, 13.5], "สระแก้ว": [102.1, 13.8],
    "สระบุรี": [100.9, 14.5], "สิงห์บุรี": [100.4, 14.9], "สุโขทัย": [99.8, 17.0],
    "สุพรรณบุรี": [100.0, 14.5], "สุราษฎร์ธานี": [99.3, 9.1], "สุรินทร์": [103.5, 14.9],
    "หนองคาย": [102.8, 17.9], "หนองบัวลำภู": [102.4, 17.2], "อ่างทอง": [100.5, 14.6],
    "อำนาจเจริญ": [104.6, 15.9], "อุดรธานี": [102.8, 17.4], "อุตรดิตถ์": [100.1, 17.6],
    "อุทัยธานี": [99.9, 15.4], "อุบลราชธานี": [104.9, 15.2],
}

# =============== สีสำหรับ Choropleth 6 คลาส ===============
CHOROPLETH_COLORS = {
    0: '#FFFFFF',
    1: '#C8E6C9',
    2: '#4CAF50',
    3: '#FFEB3B',
    4: '#FFB6C1',
    5: '#E53935'
}

# =============== ฟังก์ชันเรียงลำดับเขตตามตัวเลข ===============
def sort_zones_numerically(zones):
    def extract_number(zone_str):
        try:
            return int(str(zone_str).strip())
        except (ValueError, TypeError):
            return float('inf')
    valid_zones = [z for z in zones if str(z) != 'nan' and str(z).strip() != '']
    return sorted(valid_zones, key=extract_number)

# =============== โหลด Shapefile สำหรับข้อมูลการจมน้ำ (ระดับตำบล) ===============
gdf_drowning = None
HAS_DROWNING_SHAPEFILE = False

if HAS_GEOPANDAS:
    try:
        gdf_drowning = gpd.read_file("case_drowning.shp")
        print(f"โหลด Shapefile การจมน้ำสำเร็จ: {len(gdf_drowning)} polygons")
        print(f"คอลัมน์ใน Shapefile การจมน้ำ: {gdf_drowning.columns.tolist()}")
        
        if gdf_drowning.crs is None:
            gdf_drowning.set_crs(epsg=4326, inplace=True)
        elif gdf_drowning.crs.to_epsg() != 4326:
            gdf_drowning = gdf_drowning.to_crs(epsg=4326)
        
        HAS_DROWNING_SHAPEFILE = True
    except Exception as e:
        print(f"ไม่สามารถโหลด Shapefile การจมน้ำ: {e}")

# =============== โหลด Shapefile สำหรับข้อมูลมรณบัตร (ระดับอำเภอ) ===============
gdf_death = None
HAS_DEATH_SHAPEFILE = False

if HAS_GEOPANDAS:
    try:
        gdf_death = gpd.read_file("case_death.shp")
        print(f"โหลด Shapefile มรณบัตรสำเร็จ: {len(gdf_death)} polygons")
        print(f"คอลัมน์ใน Shapefile มรณบัตร: {gdf_death.columns.tolist()}")
        
        if gdf_death.crs is None:
            gdf_death.set_crs(epsg=4326, inplace=True)
        elif gdf_death.crs.to_epsg() != 4326:
            gdf_death = gdf_death.to_crs(epsg=4326)
        
        HAS_DEATH_SHAPEFILE = True
    except Exception as e:
        print(f"ไม่สามารถโหลด Shapefile มรณบัตร: {e}")

# =============== โหลดข้อมูลการจมน้ำ ===============
try:
    df = pd.read_excel("Drowning_Report_สรุป.xlsx")
    print("โหลดไฟล์ข้อมูลการจมน้ำสำเร็จ")
    print(f"จำนวนแถว: {len(df)}")
    print(f"คอลัมน์ดั้งเดิม: {df.columns.tolist()}")
    
    # Rename คอลัมน์
    rename_dict_thai = {
        'จังหวัดที่เกิดเหตุ': 'จังหวัด',
        'อำเภอที่เกิดเหตุ': 'อำเภอ',
        'ตำบลที่เกิดเหตุ': 'ตำบล',
        'สคร': 'เขต',
        'เดือนที่เกิดเหตุ': 'เดือน',
        'ปีที่เกิดเหตุ': 'ปี',
        'อายุ (ปี)': 'อายุ',
        'สถานะ': 'สถานะ'
    }
    
    for old_name, new_name in rename_dict_thai.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)
            print(f"  Renamed: {old_name} → {new_name}")
    
    if 'เขต' in df.columns:
        df['เขต'] = df['เขต'].astype(str).str.strip()
    
    df['lat'] = df['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[1] if x in PROVINCE_COORDS else None)
    df['lon'] = df['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[0] if x in PROVINCE_COORDS else None)
    
    print(f"คอลัมน์หลังแปลง: {df.columns.tolist()}")
    
except Exception as e:
    print(f"Error โหลดข้อมูลการจมน้ำ: {e}")
    import traceback
    traceback.print_exc()
    df = pd.DataFrame()

# =============== โหลดข้อมูลมรณบัตร (ไฟล์แยก) ===============
try:
    df_death_cert = pd.read_excel("Death_Certificate_สรุป.xls")
    print("=" * 50)
    print("โหลดไฟล์ข้อมูลมรณบัตรสำเร็จ")
    print(f"จำนวนแถว: {len(df_death_cert)}")
    print(f"คอลัมน์ดั้งเดิม: {df_death_cert.columns.tolist()}")
    
    rename_mapping = {
        'จังหวัดที่เสียชีวิต': 'จังหวัด',
        'อำเภอที่เสียชีวิต': 'อำเภอ',
        'สคร': 'เขต',
        'Month of death': 'เดือน',
        'Year of death': 'ปี',
        'อายุ': 'อายุ'
    }
    
    for old_name, new_name in rename_mapping.items():
        if old_name in df_death_cert.columns:
            df_death_cert.rename(columns={old_name: new_name}, inplace=True)
            print(f"  Renamed: {old_name} → {new_name}")
    
    for col in df_death_cert.columns:
        if 'สรุป' in str(col) or 'สรุ' in str(col):
            df_death_cert.rename(columns={col: 'สรุป'}, inplace=True)
            print(f"  Renamed: {col} → สรุป")
            break
    
    df_death_cert['สถานะ'] = 'เสียชีวิต'
    
    if 'เขต' in df_death_cert.columns:
        df_death_cert['เขต'] = df_death_cert['เขต'].astype(str).str.strip()
    
    if 'จังหวัด' in df_death_cert.columns:
        df_death_cert['lat'] = df_death_cert['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[1] if x in PROVINCE_COORDS else None)
        df_death_cert['lon'] = df_death_cert['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[0] if x in PROVINCE_COORDS else None)
    
    print("=" * 50)
    
except Exception as e:
    print(f"Error โหลดข้อมูลมรณบัตร: {e}")
    import traceback
    traceback.print_exc()
    df_death_cert = pd.DataFrame()

# =============== ฟังก์ชันคำนวณอัตราสถานะ (สำหรับข้อมูลการจมน้ำ) ===============
def calculate_status_rates(filtered_df):
    if 'สถานะ' not in filtered_df.columns or len(filtered_df) == 0:
        return {
            'deceased': {'count': 0, 'rate': 0},
            'injured': {'count': 0, 'rate': 0},
            'not_injured': {'count': 0, 'rate': 0},
            'total': 0
        }
    
    status_counts = filtered_df['สถานะ'].value_counts()
    
    deceased = status_counts.get('เสียชีวิต', 0)
    injured = status_counts.get('บาดเจ็บ', 0)
    not_injured = status_counts.get('ไม่บาดเจ็บ', 0)
    total = deceased + injured + not_injured
    
    if total == 0:
        return {
            'deceased': {'count': 0, 'rate': 0},
            'injured': {'count': 0, 'rate': 0},
            'not_injured': {'count': 0, 'rate': 0},
            'total': 0
        }
    
    return {
        'deceased': {'count': int(deceased), 'rate': round((deceased * 100) / total, 2)},
        'injured': {'count': int(injured), 'rate': round((injured * 100) / total, 2)},
        'not_injured': {'count': int(not_injured), 'rate': round((not_injured * 100) / total, 2)},
        'total': int(total)
    }

# =============== ฟังก์ชันคำนวณอัตราจาก "สรุป" (สำหรับมรณบัตร) ===============
def calculate_death_summary_rates(filtered_df):
    if 'สรุป' not in filtered_df.columns or len(filtered_df) == 0:
        return {
            'class_1': {'count': 0, 'rate': 0},
            'class_2': {'count': 0, 'rate': 0},
            'class_3': {'count': 0, 'rate': 0},
            'class_4': {'count': 0, 'rate': 0},
            'class_5': {'count': 0, 'rate': 0},
            'total': 0
        }
    
    summary_counts = filtered_df['สรุป'].value_counts()
    
    class_1 = summary_counts.get(1, 0)
    class_2 = summary_counts.get(2, 0)
    class_3 = summary_counts.get(3, 0)
    class_4 = summary_counts.get(4, 0)
    class_5 = sum([summary_counts.get(i, 0) for i in summary_counts.index if i >= 5])
    
    total = class_1 + class_2 + class_3 + class_4 + class_5
    
    if total == 0:
        return {
            'class_1': {'count': 0, 'rate': 0},
            'class_2': {'count': 0, 'rate': 0},
            'class_3': {'count': 0, 'rate': 0},
            'class_4': {'count': 0, 'rate': 0},
            'class_5': {'count': 0, 'rate': 0},
            'total': 0
        }
    
    return {
        'class_1': {'count': int(class_1), 'rate': round((class_1 * 100) / total, 2)},
        'class_2': {'count': int(class_2), 'rate': round((class_2 * 100) / total, 2)},
        'class_3': {'count': int(class_3), 'rate': round((class_3 * 100) / total, 2)},
        'class_4': {'count': int(class_4), 'rate': round((class_4 * 100) / total, 2)},
        'class_5': {'count': int(class_5), 'rate': round((class_5 * 100) / total, 2)},
        'total': int(total)
    }

# =============== ฟังก์ชันคำนวณความถี่ตามปี ===============
def calculate_frequency_by_year(filtered_df):
    if 'ปี' not in filtered_df.columns or 'สถานะ' not in filtered_df.columns:
        return None
    
    years = sorted(filtered_df['ปี'].dropna().unique())
    
    if len(years) == 0:
        return None
    
    incident_counts = []
    death_counts = []
    
    for year in years:
        year_df = filtered_df[filtered_df['ปี'] == year]
        status = year_df['สถานะ'].value_counts()
        
        injured = status.get('บาดเจ็บ', 0)
        not_injured = status.get('ไม่บาดเจ็บ', 0)
        death = status.get('เสียชีวิต', 0)
        
        incident_counts.append(injured + not_injured)
        death_counts.append(death)
    
    total_incident = sum(incident_counts)
    total_death = sum(death_counts)
    grand_total = total_incident + total_death
    
    incident_rates = []
    death_rates = []
    
    for i in range(len(years)):
        incident_rates.append(round((incident_counts[i] * 100) / total_incident, 2) if total_incident > 0 else 0)
        death_rates.append(round((death_counts[i] * 100) / total_death, 2) if total_death > 0 else 0)
    
    return {
        'years': [int(y) for y in years],
        'incident_count': incident_counts,
        'death_count': death_counts,
        'incident_rate': incident_rates,
        'death_rate': death_rates,
        'total_incident': total_incident,
        'total_death': total_death,
        'grand_total': grand_total
    }

# =============== ฟังก์ชันสร้างแผนที่ Heatmap (แก้ไขใหม่ - รายตำบลสำหรับจมน้ำ, รายอำเภอสำหรับมรณบัตร) ===============
def create_shapefile_heatmap(filtered_df, map_type='deceased_rate', data_type='drowning'):
    """
    สร้างแผนที่ Heatmap ตามประเภทอัตรา
    - สำหรับ drowning: แสดงอัตราการเสียชีวิต/บาดเจ็บ/ไม่บาดเจ็บ รายตำบล (คำนวณจากบัญญัติไตรยางค์)
    - สำหรับ death_cert: แสดงอัตราการเสียชีวิตรายอำเภอ (คำนวณจากบัญญัติไตรยางค์)
    """
    
    if len(filtered_df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="ไม่มีข้อมูล", showarrow=False)
        fig.update_layout(height=400)
        return fig
    
    # =============== สำหรับข้อมูลการจมน้ำ - แสดงอัตรารายตำบล ===============
    if data_type == 'drowning':
        if 'จังหวัด' not in filtered_df.columns or 'สถานะ' not in filtered_df.columns:
            fig = go.Figure()
            fig.add_annotation(text="ไม่มีข้อมูลจังหวัด/สถานะ", showarrow=False)
            fig.update_layout(height=400)
            return fig
        
        # ตรวจสอบว่ามีคอลัมน์ อำเภอ และ ตำบล หรือไม่
        has_district = 'อำเภอ' in filtered_df.columns
        has_subdistrict = 'ตำบล' in filtered_df.columns
        
        # =============== รวมข้อมูลเป็นรายตำบล และนับตามสถานะ ===============
        if has_subdistrict and has_district:
            # รวมตามจังหวัด+อำเภอ+ตำบล+สถานะ
            status_pivot = filtered_df.groupby(['จังหวัด', 'อำเภอ', 'ตำบล', 'สถานะ']).size().unstack(fill_value=0)
            subdistrict_data = status_pivot.reset_index()
            area_level = "ตำบล"
            group_cols = ['จังหวัด', 'อำเภอ', 'ตำบล']
        elif has_district:
            # รวมตามจังหวัด+อำเภอ+สถานะ
            status_pivot = filtered_df.groupby(['จังหวัด', 'อำเภอ', 'สถานะ']).size().unstack(fill_value=0)
            subdistrict_data = status_pivot.reset_index()
            subdistrict_data['ตำบล'] = '-'
            area_level = "อำเภอ"
            group_cols = ['จังหวัด', 'อำเภอ']
        else:
            # รวมตามจังหวัด+สถานะ
            status_pivot = filtered_df.groupby(['จังหวัด', 'สถานะ']).size().unstack(fill_value=0)
            subdistrict_data = status_pivot.reset_index()
            subdistrict_data['อำเภอ'] = '-'
            subdistrict_data['ตำบล'] = '-'
            area_level = "จังหวัด"
            group_cols = ['จังหวัด']
        
        # เติมค่า 0 ถ้าไม่มีสถานะนั้น
        for status in ['เสียชีวิต', 'บาดเจ็บ', 'ไม่บาดเจ็บ']:
            if status not in subdistrict_data.columns:
                subdistrict_data[status] = 0
        
        # =============== คำนวณอัตราแบบบัญญัติไตรยางค์ ===============
        # อัตราการเสียชีวิตของตำบล X = (จำนวนเสียชีวิตในตำบล X / จำนวนเสียชีวิตทั้งหมด) × 100
        total_deceased = subdistrict_data['เสียชีวิต'].sum()
        total_injured = subdistrict_data['บาดเจ็บ'].sum()
        total_not_injured = subdistrict_data['ไม่บาดเจ็บ'].sum()
        
        # คำนวณอัตราแต่ละประเภท
        subdistrict_data['อัตราเสียชีวิต'] = np.where(
            total_deceased > 0,
            (subdistrict_data['เสียชีวิต'] * 100 / total_deceased).round(2),
            0
        )
        subdistrict_data['อัตราบาดเจ็บ'] = np.where(
            total_injured > 0,
            (subdistrict_data['บาดเจ็บ'] * 100 / total_injured).round(2),
            0
        )
        subdistrict_data['อัตราไม่บาดเจ็บ'] = np.where(
            total_not_injured > 0,
            (subdistrict_data['ไม่บาดเจ็บ'] * 100 / total_not_injured).round(2),
            0
        )
        
        # =============== ใช้ Centroid จาก Shapefile ถ้ามี ===============
        if HAS_DROWNING_SHAPEFILE and gdf_drowning is not None and has_subdistrict:
            # หาคอลัมน์ชื่อตำบล, อำเภอ, จังหวัดใน Shapefile
            tam_col = None
            amp_col = None
            prov_col = None
            
            for col in gdf_drowning.columns:
                if col in ['ตำบ', 'TAM_TH', 'TAMBON', 'ตำบล', 'TAM_NAME', 'NAME_3', 'TB_TH']:
                    tam_col = col
                if col in ['อำเ', 'AMP_TH', 'AMPHOE', 'อำเภอ', 'AMP_NAME', 'NAME_2', 'AP_TH']:
                    amp_col = col
                if col in ['PRO_TH', 'PROVINCE', 'จังหวัด', 'PRO_NAME', 'NAME_1', 'PV_TH']:
                    prov_col = col
            
            if tam_col:
                # คำนวณ centroid ของแต่ละตำบลจาก Shapefile
                gdf_centroids = gdf_drowning.copy()
                gdf_centroids['centroid'] = gdf_centroids.geometry.centroid
                gdf_centroids['lon'] = gdf_centroids['centroid'].x
                gdf_centroids['lat'] = gdf_centroids['centroid'].y
                
                # สร้าง dict ของพิกัดตำบล
                subdistrict_coords = {}
                for _, row in gdf_centroids.iterrows():
                    tam_name = str(row.get(tam_col, '')).strip()
                    amp_name = str(row.get(amp_col, '')).strip() if amp_col else ''
                    prov_name = str(row.get(prov_col, '')).strip() if prov_col else ''
                    if tam_name:
                        key = f"{prov_name}_{amp_name}_{tam_name}"
                        subdistrict_coords[key] = {'lat': row['lat'], 'lon': row['lon']}
                
                # Join พิกัดกับข้อมูลตำบล
                def get_subdistrict_coords(row):
                    key = f"{row['จังหวัด']}_{row['อำเภอ']}_{row['ตำบล']}"
                    if key in subdistrict_coords:
                        return pd.Series([subdistrict_coords[key]['lat'], subdistrict_coords[key]['lon']])
                    # ลองหาแค่ตำบล+อำเภอ
                    for k, v in subdistrict_coords.items():
                        if row['ตำบล'] in k and row['อำเภอ'] in k:
                            return pd.Series([v['lat'], v['lon']])
                    # ใช้พิกัดจังหวัดแทน
                    prov_coord = PROVINCE_COORDS.get(row['จังหวัด'], [None, None])
                    return pd.Series([prov_coord[1], prov_coord[0]])
                
                subdistrict_data[['lat', 'lon']] = subdistrict_data.apply(get_subdistrict_coords, axis=1)
            else:
                # ใช้พิกัดจังหวัดแทน
                subdistrict_data['lat'] = subdistrict_data['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[1])
                subdistrict_data['lon'] = subdistrict_data['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[0])
        else:
            # ใช้พิกัดจังหวัดแทน (มี offset เล็กน้อยเพื่อให้เห็นความแตกต่าง)
            subdistrict_data['lat'] = subdistrict_data['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[1])
            subdistrict_data['lon'] = subdistrict_data['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[0])
            
            # เพิ่ม offset เล็กน้อยสำหรับแต่ละตำบลในจังหวัดเดียวกัน
            for prov in subdistrict_data['จังหวัด'].unique():
                mask = subdistrict_data['จังหวัด'] == prov
                n_items = mask.sum()
                if n_items > 1:
                    # สร้าง offset แบบ random เล็กน้อย
                    np.random.seed(hash(prov) % 2**32)
                    lat_offsets = np.random.uniform(-0.2, 0.2, n_items)
                    lon_offsets = np.random.uniform(-0.2, 0.2, n_items)
                    subdistrict_data.loc[mask, 'lat'] = subdistrict_data.loc[mask, 'lat'] + lat_offsets
                    subdistrict_data.loc[mask, 'lon'] = subdistrict_data.loc[mask, 'lon'] + lon_offsets
        
        # ลบแถวที่ไม่มีพิกัด
        subdistrict_data = subdistrict_data.dropna(subset=['lat', 'lon'])
        
        if len(subdistrict_data) == 0:
            fig = go.Figure()
            fig.add_annotation(text="ไม่มีข้อมูลพิกัด", showarrow=False)
            fig.update_layout(height=400)
            return fig
        
        # =============== เลือกข้อมูลตามประเภทที่เลือก ===============
        if map_type == 'deceased_rate':
            rate_col = 'อัตราเสียชีวิต'
            count_col = 'เสียชีวิต'
            total_count = total_deceased
            title = f'แผนที่ Heatmap อัตราการเสียชีวิตราย{area_level} (รวม {int(total_count):,} ราย)'
            colorscale = 'Reds'
        elif map_type == 'injured_rate':
            rate_col = 'อัตราบาดเจ็บ'
            count_col = 'บาดเจ็บ'
            total_count = total_injured
            title = f'แผนที่ Heatmap อัตราการบาดเจ็บราย{area_level} (รวม {int(total_count):,} ราย)'
            colorscale = 'Oranges'
        else:  # not_injured_rate
            rate_col = 'อัตราไม่บาดเจ็บ'
            count_col = 'ไม่บาดเจ็บ'
            total_count = total_not_injured
            title = f'แผนที่ Heatmap อัตราการไม่บาดเจ็บราย{area_level} (รวม {int(total_count):,} ราย)'
            colorscale = 'Greens'
        
        # =============== สร้าง Heatmap ด้วย Plotly Density ===============
        fig = go.Figure()
        
        # สร้าง customdata สำหรับ hover
        if has_subdistrict:
            customdata = subdistrict_data[['จังหวัด', 'อำเภอ', 'ตำบล', count_col]].values
            hovertemplate = ("<b>จังหวัด: %{customdata[0]}</b><br>" +
                           "อำเภอ: %{customdata[1]}<br>" +
                           "ตำบล: %{customdata[2]}<br>" +
                           f"จำนวน: %{{customdata[3]:,}} ราย<br>" +
                           "อัตรา: %{z:.2f}%<extra></extra>")
        elif has_district:
            customdata = subdistrict_data[['จังหวัด', 'อำเภอ', count_col]].values
            hovertemplate = ("<b>จังหวัด: %{customdata[0]}</b><br>" +
                           "อำเภอ: %{customdata[1]}<br>" +
                           f"จำนวน: %{{customdata[2]:,}} ราย<br>" +
                           "อัตรา: %{z:.2f}%<extra></extra>")
        else:
            customdata = subdistrict_data[['จังหวัด', count_col]].values
            hovertemplate = ("<b>จังหวัด: %{customdata[0]}</b><br>" +
                           f"จำนวน: %{{customdata[1]:,}} ราย<br>" +
                           "อัตรา: %{z:.2f}%<extra></extra>")
        
        fig.add_trace(go.Densitymapbox(
            lat=subdistrict_data['lat'],
            lon=subdistrict_data['lon'],
            z=subdistrict_data[rate_col],
            radius=20,  # ลดขนาดเพื่อให้เห็นรายละเอียดตำบล
            colorscale=colorscale,
            zmin=0,
            zmax=subdistrict_data[rate_col].max() if subdistrict_data[rate_col].max() > 0 else 1,
            colorbar=dict(
                title=dict(text='อัตรา (%)', font=dict(family='Sarabun', size=10)),
                ticksuffix='%',
                len=0.7
            ),
            hovertemplate=hovertemplate,
            customdata=customdata
        ))
        
        fig.update_layout(
            title=None,
            
            # title=dict(
            #     text=title, 
            #     x=0.5, 
            #     font=dict(size=12, family='Sarabun')
            # ),
            mapbox=dict(
                style='carto-positron',
                center=dict(lat=13.5, lon=101),
                zoom=5
            ),
            margin=dict(l=0, r=0, t=35, b=0),
            height=400,
            font=dict(family='Sarabun')
        )
        
        return fig
    
    # =============== สำหรับข้อมูลมรณบัตร - แสดงอัตราการเสียชีวิตรายอำเภอ ===============
    if data_type == 'death_cert':
        if 'จังหวัด' not in filtered_df.columns or 'อำเภอ' not in filtered_df.columns:
            fig = go.Figure()
            fig.add_annotation(text="ไม่มีข้อมูลจังหวัด/อำเภอ", showarrow=False)
            fig.update_layout(height=400)
            return fig
        
        if 'สรุป' not in filtered_df.columns:
            fig = go.Figure()
            fig.add_annotation(text="ไม่มีคอลัมน์ 'สรุป' ในข้อมูล", showarrow=False)
            fig.update_layout(height=400)
            return fig
        
        # รวมจำนวนเสียชีวิต (สรุป) ตามจังหวัด+อำเภอ
        district_data = filtered_df.groupby(['จังหวัด', 'อำเภอ']).agg({
            'สรุป': 'sum'
        }).reset_index()
        district_data.columns = ['จังหวัด', 'อำเภอ', 'จำนวนเสียชีวิต']
        
        total_deaths = district_data['จำนวนเสียชีวิต'].sum()
        
        if total_deaths == 0:
            fig = go.Figure()
            fig.add_annotation(text="ไม่มีข้อมูลการเสียชีวิต", showarrow=False)
            fig.update_layout(height=400)
            return fig
        
        district_data['อัตราการเสียชีวิต'] = (district_data['จำนวนเสียชีวิต'] * 100 / total_deaths).round(2)
        
        # ใช้ Centroid จาก Shapefile ถ้ามี
        if HAS_DEATH_SHAPEFILE and gdf_death is not None:
            amp_col = None
            prov_col = None
            
            for col in gdf_death.columns:
                if col in ['อำเ', 'AMP_TH', 'AMPHOE', 'อำเภอ', 'AMP_NAME', 'NAME_2', 'DISTRICT', 'AP_TH']:
                    amp_col = col
                if col in ['PRO_TH', 'PROVINCE', 'จังหวัด', 'PRO_NAME', 'NAME_1', 'PROV_NAM_T', 'PV_TH']:
                    prov_col = col
            
            if amp_col:
                gdf_centroids = gdf_death.copy()
                gdf_centroids['centroid'] = gdf_centroids.geometry.centroid
                gdf_centroids['lon'] = gdf_centroids['centroid'].x
                gdf_centroids['lat'] = gdf_centroids['centroid'].y
                
                district_coords = {}
                for _, row in gdf_centroids.iterrows():
                    amp_name = str(row.get(amp_col, '')).strip()
                    prov_name = str(row.get(prov_col, '')).strip() if prov_col else ''
                    if amp_name:
                        key = f"{prov_name}_{amp_name}"
                        district_coords[key] = {'lat': row['lat'], 'lon': row['lon']}
                
                def get_district_coords(row):
                    key = f"{row['จังหวัด']}_{row['อำเภอ']}"
                    if key in district_coords:
                        return pd.Series([district_coords[key]['lat'], district_coords[key]['lon']])
                    for k, v in district_coords.items():
                        if row['อำเภอ'] in k:
                            return pd.Series([v['lat'], v['lon']])
                    prov_coord = PROVINCE_COORDS.get(row['จังหวัด'], [None, None])
                    return pd.Series([prov_coord[1], prov_coord[0]])
                
                district_data[['lat', 'lon']] = district_data.apply(get_district_coords, axis=1)
            else:
                district_data['lat'] = district_data['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[1])
                district_data['lon'] = district_data['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[0])
        else:
            district_data['lat'] = district_data['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[1])
            district_data['lon'] = district_data['จังหวัด'].map(lambda x: PROVINCE_COORDS.get(x, [None, None])[0])
            
            for prov in district_data['จังหวัด'].unique():
                mask = district_data['จังหวัด'] == prov
                n_districts = mask.sum()
                if n_districts > 1:
                    offsets = np.linspace(-0.15, 0.15, n_districts)
                    np.random.shuffle(offsets)
                    district_data.loc[mask, 'lat'] = district_data.loc[mask, 'lat'] + offsets[:n_districts]
                    district_data.loc[mask, 'lon'] = district_data.loc[mask, 'lon'] + offsets[:n_districts] * 0.5
        
        district_data = district_data.dropna(subset=['lat', 'lon'])
        
        if len(district_data) == 0:
            fig = go.Figure()
            fig.add_annotation(text="ไม่มีข้อมูลพิกัด", showarrow=False)
            fig.update_layout(height=400)
            return fig
        
        fig = go.Figure()
        
        fig.add_trace(go.Densitymapbox(
            lat=district_data['lat'],
            lon=district_data['lon'],
            z=district_data['อัตราการเสียชีวิต'],
            radius=25,
            colorscale='Reds',
            zmin=0,
            zmax=district_data['อัตราการเสียชีวิต'].max(),
            colorbar=dict(
                title=dict(text='อัตรา (%)', font=dict(family='Sarabun', size=10)),
                ticksuffix='%',
                len=0.7
            ),
            hovertemplate="<b>จังหวัด: %{customdata[0]}</b><br>" +
                          "อำเภอ: %{customdata[1]}<br>" +
                          "จำนวน: %{customdata[2]:,} ราย<br>" +
                          "อัตรา: %{z:.2f}%<extra></extra>",
            customdata=district_data[['จังหวัด', 'อำเภอ', 'จำนวนเสียชีวิต']].values
        ))
        
        fig.update_layout(
            title=None,
            
            # title=dict(
            #     text=f'แผนที่ Heatmap อัตราการเสียชีวิตรายอำเภอ (รวม {int(total_deaths):,} ราย)', 
            #     x=0.5, 
            #     font=dict(size=12, family='Sarabun')
            # ),
            mapbox=dict(
                style='carto-positron',
                center=dict(lat=13.5, lon=101),
                zoom=5
            ),
            margin=dict(l=0, r=0, t=35, b=0),
            height=400,
            font=dict(family='Sarabun')
        )
        
        return fig
    
    # Default empty figure
    fig = go.Figure()
    fig.add_annotation(text="ไม่รู้จักประเภทข้อมูล", showarrow=False)
    fig.update_layout(height=400)
    return fig

# =============== ฟังก์ชันกำหนด class จากค่า attribute 'สรุ' ===============
def get_class_from_attribute(value):
    if pd.isna(value) or value == 0:
        return 0
    elif value == 1:
        return 1
    elif value == 2:
        return 2
    elif value == 3:
        return 3
    elif value == 4:
        return 4
    else:
        return 5

# =============== ฟังก์ชันสร้างแผนที่ Choropleth จาก Shapefile โดยตรง ===============
def create_choropleth_from_shapefile(data_type='drowning'):
    m = folium.Map(location=[13.7563, 100.5018], zoom_start=6, tiles='cartodbpositron')
    
    if data_type == 'death_cert':
        if not HAS_DEATH_SHAPEFILE or gdf_death is None:
            return _create_fallback_map("ไม่พบ Shapefile มรณบัตร (case_death.shp)")
        
        gdf = gdf_death.copy()
        title_text = "จำนวนครั้งที่เกิดเหตุจมน้ำเสียชีวิต (2563-2567)"
        area_level = "อำเภอ"
    else:
        if not HAS_DROWNING_SHAPEFILE or gdf_drowning is None:
            return _create_fallback_map("ไม่พบ Shapefile การจมน้ำ (case_drowning.shp)")
        
        gdf = gdf_drowning.copy()
        title_text = "จำนวนครั้งที่เกิดเหตุจมน้ำเสียชีวิต (2563-2567)"
        area_level = "ตำบล"
    
    summary_col = None
    possible_summary_cols = ['สรุ', 'สรุป', 'SUMMARY', 'summary', 'Sum', 'SUM']
    for col in possible_summary_cols:
        if col in gdf.columns:
            summary_col = col
            break
    
    if summary_col is None:
        print(f"คอลัมน์ที่มีใน Shapefile: {gdf.columns.tolist()}")
        return _create_fallback_map(f"ไม่พบคอลัมน์ 'สรุ' ใน Shapefile\nคอลัมน์ที่มี: {gdf.columns.tolist()}")
    
    print(f"ใช้คอลัมน์: {summary_col}")
    
    gdf['class'] = gdf[summary_col].apply(get_class_from_attribute)
    gdf['color'] = gdf['class'].map(CHOROPLETH_COLORS)
    
    name_col = None
    if data_type == 'death_cert':
        possible_name_cols = ['อำเ', 'AMP_TH', 'AMPHOE', 'อำเภอ', 'AMP_NAME', 'NAME_2', 'DISTRICT', 'AP_TH']
    else:
        possible_name_cols = ['ตำบ', 'TAM_TH', 'TAMBON', 'ตำบล', 'TAM_NAME', 'NAME_3', 'SUBDISTRICT', 'TB_TH']
    
    for col in possible_name_cols:
        if col in gdf.columns:
            name_col = col
            break
    
    prov_col = None
    possible_prov_cols = ['PRO_TH', 'PROVINCE', 'จังหวัด', 'PRO_NAME', 'NAME_1', 'PROV_NAM_T', 'PV_TH']
    for col in possible_prov_cols:
        if col in gdf.columns:
            prov_col = col
            break
    
    for idx, row in gdf.iterrows():
        if row.geometry is None:
            continue
        
        area_name = row.get(name_col, 'N/A') if name_col else 'N/A'
        prov_name = row.get(prov_col, 'N/A') if prov_col else 'N/A'
        summary_value = row.get(summary_col, 0)
        if pd.isna(summary_value):
            summary_value = 0
        
        popup_text = f"""
        <div style="font-family: Sarabun, sans-serif;">
            <b>จังหวัด:</b> {prov_name}<br>
            <b>{area_level}:</b> {area_name}<br>
            <b>จำนวนครั้ง:</b> {int(summary_value)} ครั้ง
        </div>
        """
        
        fill_color = row['color']
        
        try:
            folium.GeoJson(
                row.geometry.__geo_interface__,
                style_function=lambda x, fc=fill_color: {
                    'fillColor': fc,
                    'color': '#666666',
                    'weight': 0.5,
                    'fillOpacity': 0.7
                },
                popup=folium.Popup(popup_text, max_width=250)
            ).add_to(m)
        except Exception as e:
            print(f"Error adding geometry {idx}: {e}")
            continue
    
    legend_css = '''
    <style>
    .legend-box {
        position: fixed !important;
        bottom: 30px !important;
        right: 10px !important;
        z-index: 9999 !important;
        background-color: rgba(255,255,255,0.95) !important;
        padding: 8px 12px !important;
        font-family: Sarabun, Tahoma, sans-serif !important;
        font-size: 11px !important;
        border-radius: 4px !important;
        box-shadow: 0 1px 5px rgba(0,0,0,0.3) !important;
        border: 1px solid #ccc !important;
    }
    .legend-title {
        font-weight: bold;
        text-align: center;
        margin-bottom: 6px;
        font-size: 11px;
        color: #333;
    }
    .legend-items {
        display: flex;
        align-items: flex-start;
        justify-content: center;
        gap: 3px;
    }
    .legend-item {
        text-align: center;
    }
    .legend-item.wide {
        width: 50px;
    }
    .legend-item.normal {
        width: 38px;
    }
    .legend-color {
        width: 100%;
        height: 18px;
        border: 1px solid #999;
    }
    .legend-label {
        font-size: 9px;
        margin-top: 2px;
        color: #333;
    }
    </style>
    '''
    
    legend_content = f'''
    <div class="legend-box">
        <div class="legend-title">{title_text}</div>
        <div class="legend-items">
            <div class="legend-item wide">
                <div class="legend-color" style="background-color: #FFFFFF;"></div>
                <div class="legend-label">ไม่มีรายงาน</div>
            </div>
            <div class="legend-item normal">
                <div class="legend-color" style="background-color: #C8E6C9;"></div>
                <div class="legend-label">1 ครั้ง</div>
            </div>
            <div class="legend-item normal">
                <div class="legend-color" style="background-color: #4CAF50;"></div>
                <div class="legend-label">2 ครั้ง</div>
            </div>
            <div class="legend-item normal">
                <div class="legend-color" style="background-color: #FFEB3B;"></div>
                <div class="legend-label">3 ครั้ง</div>
            </div>
            <div class="legend-item normal">
                <div class="legend-color" style="background-color: #FFB6C1;"></div>
                <div class="legend-label">4 ครั้ง</div>
            </div>
            <div class="legend-item normal">
                <div class="legend-color" style="background-color: #E53935;"></div>
                <div class="legend-label">≥ 5 ครั้ง</div>
            </div>
        </div>
    </div>
    '''
    
    m.get_root().header.add_child(Element(legend_css))
    m.get_root().html.add_child(Element(legend_content))
    
    logo_img_tags = ""
    if LOGO_GD_BASE64:
        logo_img_tags += f'<img src="{LOGO_GD_BASE64}" style="height: 40px; width: auto;">'
    if LOGO_KK_BASE64:
        logo_img_tags += f'<img src="{LOGO_KK_BASE64}" style="height: 40px; width: auto;">'
    
    if logo_img_tags:
        logo_html = f'''
        <div style="position: fixed; 
                    top: 10px; right: 20px;
                    z-index: 9999; 
                    background-color: white;
                    padding: 5px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    display: flex;
                    gap: 5px;">
            {logo_img_tags}
        </div>
        '''
        m.get_root().html.add_child(folium.Element(logo_html))
    
    source_html = '''
    <div style="position: fixed; 
                bottom: 10px; left: 10px;
                z-index: 9999; 
                background-color: rgba(255,255,255,0.9);
                padding: 5px 10px;
                font-family: Sarabun, sans-serif;
                font-size: 10px;
                border-radius: 3px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);">
        <b>แหล่งที่มา:</b> กรมควบคุมโรค กระทรวงสาธารณสุข
    </div>
    '''
    m.get_root().html.add_child(folium.Element(source_html))
    
    return m._repr_html_()

def _create_fallback_map(message):
    m = folium.Map(location=[13.7563, 100.5018], zoom_start=6, tiles='cartodbpositron')
    
    error_html = f'''
    <div style="position: fixed; 
                top: 50%; left: 50%; transform: translate(-50%, -50%);
                z-index: 9999; 
                background-color: rgba(255,255,255,0.95);
                padding: 20px;
                font-family: Sarabun, sans-serif;
                font-size: 14px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 400px;">
        <p style="color: #E53935; font-weight: bold; margin-bottom: 10px;">⚠️ ไม่สามารถแสดงแผนที่ได้</p>
        <p style="color: #666; margin: 0;">{message}</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(error_html))
    
    return m._repr_html_()

# =============== สร้าง Zone Dropdown Options ===============
def get_zone_options():
    if 'เขต' not in df.columns or len(df) == 0:
        return [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    
    sorted_zones = sort_zones_numerically(df['เขต'].unique())
    
    options = [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    for zone in sorted_zones:
        options.append({'label': f"เขต {zone}", 'value': str(zone)})
    
    return options

def get_death_cert_province_options():
    if 'จังหวัด' not in df_death_cert.columns or len(df_death_cert) == 0:
        return [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    
    provinces = sorted(df_death_cert['จังหวัด'].dropna().unique())
    
    options = [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    for prov in provinces:
        options.append({'label': str(prov), 'value': str(prov)})
    
    return options

def get_death_cert_zone_options():
    if 'เขต' not in df_death_cert.columns or len(df_death_cert) == 0:
        return [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    
    sorted_zones = sort_zones_numerically(df_death_cert['เขต'].unique())
    
    options = [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    for zone in sorted_zones:
        options.append({'label': f"เขต {zone}", 'value': str(zone)})
    
    return options

# =============== สร้าง Layout ===============
logo_components = []
if LOGO_GD_BASE64:
    logo_components.append(html.Img(src=LOGO_GD_BASE64, style={'height': '50px', 'marginRight': '10px'}, className="d-inline"))
if LOGO_KK_BASE64:
    logo_components.append(html.Img(src=LOGO_KK_BASE64, style={'height': '50px'}, className="d-inline"))

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div(logo_components, style={'marginBottom': '10px', 'textAlign': 'right'})
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.H1("ระบบข้อมูลการจมน้ำและมรณบัตร ปี 2563-2568", 
                   className="text-center mb-4 mt-2",
                   style={'fontFamily': 'Sarabun, sans-serif', 'fontWeight': 'bold'})
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label="ข้อมูลการจมน้ำ", tab_id="drowning-tab",
                       label_style={'fontFamily': 'Sarabun', 'fontWeight': 'bold'}),
                dbc.Tab(label="ข้อมูลมรณบัตร", tab_id="death-cert-tab",
                       label_style={'fontFamily': 'Sarabun', 'fontWeight': 'bold'}),
            ], id="data-tabs", active_tab="drowning-tab", className="mb-3")
        ])
    ]),
    
    # Filters สำหรับข้อมูลการจมน้ำ
    html.Div(id='drowning-filters', children=[
        dbc.Row([
            dbc.Col([
                html.Label("จังหวัด", style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Dropdown(
                    id='province-dropdown',
                    options=[{'label': 'ทั้งหมด', 'value': 'ALL'}] + 
                            [{'label': str(i), 'value': str(i)} for i in sorted(df['จังหวัด'].dropna().unique())] 
                            if 'จังหวัด' in df.columns and len(df) > 0 else [{'label': 'ทั้งหมด', 'value': 'ALL'}],
                    value='ALL',
                    clearable=False,
                    style={'fontFamily': 'Sarabun, sans-serif'}
                )
            ], width=3),
            
            dbc.Col([
                html.Label("อำเภอ", style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Dropdown(
                    id='district-dropdown',
                    options=[{'label': 'ทั้งหมด', 'value': 'ALL'}],
                    value='ALL',
                    clearable=False,
                    style={'fontFamily': 'Sarabun, sans-serif'}
                )
            ], width=3),
            
            dbc.Col([
                html.Label("ตำบล", style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Dropdown(
                    id='subdistrict-dropdown',
                    options=[{'label': 'ทั้งหมด', 'value': 'ALL'}],
                    value='ALL',
                    clearable=False,
                    style={'fontFamily': 'Sarabun, sans-serif'}
                )
            ], width=3),
            
            dbc.Col([
                html.Label("เขต", style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Dropdown(
                    id='zone-dropdown',
                    options=get_zone_options(),
                    value='ALL',
                    clearable=False,
                    style={'fontFamily': 'Sarabun, sans-serif'}
                )
            ], width=3),
        ], className="mb-3 justify-content-center"),
    ]),
    
    # Filters สำหรับข้อมูลมรณบัตร
    html.Div(id='death-cert-filters', style={'display': 'none'}, children=[
        dbc.Row([
            dbc.Col([
                html.Label("จังหวัด", style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Dropdown(
                    id='dc-province-dropdown',
                    options=get_death_cert_province_options(),
                    value='ALL',
                    clearable=False,
                    style={'fontFamily': 'Sarabun, sans-serif'}
                )
            ], width=4),
            
            dbc.Col([
                html.Label("อำเภอ", style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Dropdown(
                    id='dc-district-dropdown',
                    options=[{'label': 'ทั้งหมด', 'value': 'ALL'}],
                    value='ALL',
                    clearable=False,
                    style={'fontFamily': 'Sarabun, sans-serif'}
                )
            ], width=4),
            
            dbc.Col([
                html.Label("เขต", style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Dropdown(
                    id='dc-zone-dropdown',
                    options=get_death_cert_zone_options(),
                    value='ALL',
                    clearable=False,
                    style={'fontFamily': 'Sarabun, sans-serif'}
                )
            ], width=4),
        ], className="mb-3 justify-content-center"),
    ]),
    
    # บรรทัดที่ 2: เดือน / ปี / อายุ / ค้นหา
    dbc.Row([
        dbc.Col([
            html.Label("เดือน", style={'fontFamily': 'Sarabun, sans-serif'}),
            dcc.Dropdown(
                id='month-dropdown',
                options=[{'label': 'ทั้งหมด', 'value': 'ALL'}] + 
                        [{'label': f'{i}', 'value': i} for i in range(1, 13)],
                value='ALL',
                clearable=False,
                style={'fontFamily': 'Sarabun, sans-serif'}
            )
        ], width=3),
        
        dbc.Col([
            html.Label("ปี", style={'fontFamily': 'Sarabun, sans-serif'}),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': 'ทั้งหมด', 'value': 'ALL'}] + 
                        [{'label': str(int(i)), 'value': int(i)} for i in sorted(df['ปี'].dropna().unique())] 
                        if 'ปี' in df.columns and len(df) > 0 else [{'label': 'ทั้งหมด', 'value': 'ALL'}],
                value='ALL',
                clearable=False,
                style={'fontFamily': 'Sarabun, sans-serif'}
            )
        ], width=3),
        
        dbc.Col([
            html.Label("อายุ", style={'fontFamily': 'Sarabun, sans-serif'}),
            dcc.Dropdown(
                id='age-dropdown',
                options=[
                    {'label': 'ทั้งหมด', 'value': 'ALL'},
                    {'label': 'อายุต่ำกว่า 15 ปี', 'value': '<15'},
                    {'label': 'ทุกกลุ่มอายุ (15+)', 'value': '15+'}
                ],
                value='ALL',
                clearable=False,
                style={'fontFamily': 'Sarabun, sans-serif'}
            )
        ], width=3),
        
        dbc.Col([
            html.Label("\u00A0", style={'fontFamily': 'Sarabun, sans-serif'}),
            dbc.Button("อัพเดท", id="search-button", color="primary", n_clicks=0,
                      style={'width': '100%', 'fontFamily': 'Sarabun, sans-serif'})
        ], width=3),
    ], className="mb-4 justify-content-center"),
    
    # แสดงสถิติ
    dbc.Row([
        dbc.Col([
            html.H4("สถิติข้อมูล", className="text-center mb-3",
                   style={'fontFamily': 'Sarabun, sans-serif'}),
            html.Div(id='statistics-output')
        ])
    ], className="mb-4"),
    
    # Pie Chart + Heatmap Map
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='status-pie-chart', style={'height': '350px'}),
            html.Div(id='status-details', className="mt-2")
        ], width=6),
        
        dbc.Col([
            html.Div(id='heatmap-options-drowning', children=[
                html.Label("แผนที่ Heatmap อัตรารายตำบล (%):", style={'fontFamily': 'Sarabun', 'fontWeight': 'bold'}),
                dcc.RadioItems(
                    id='map-type-radio',
                    options=[
                        {'label': ' อัตราเสียชีวิต', 'value': 'deceased_rate'},
                        {'label': ' อัตราบาดเจ็บ', 'value': 'injured_rate'},
                        {'label': ' อัตราไม่บาดเจ็บ', 'value': 'not_injured_rate'}
                    ],
                    value='deceased_rate',
                    inline=True,
                    style={'fontFamily': 'Sarabun', 'marginBottom': '10px'}
                ),
            ]),
            html.Div(id='heatmap-options-death', style={'display': 'none'}, children=[
                html.Label("แผนที่ Heatmap อัตราการเสียชีวิตรายอำเภอ (%):", 
                          style={'fontFamily': 'Sarabun', 'fontWeight': 'bold'}),
            ]),
            dcc.Graph(id='heatmap-map', style={'height': '450px'})
        ], width=6),
    ], className="mb-4"),
    
    # Content ข้อมูลการจมน้ำ
    html.Div(id='drowning-content', children=[
        dbc.Row([
            dbc.Col([
                html.H4("ร้อยละความถี่การเกิดเหตุและเสียชีวิตจากการจมน้ำรายปี", 
                       className="text-center mb-3",
                       style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Graph(id='frequency-histogram', style={'height': '500px'})
            ])
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                html.H4("แผนที่แสดงจำนวนการเกิดเหตุจมน้ำเสียชีวิตรายตำบล (2563-2568)", 
                       className="text-center mb-3",
                       style={'fontFamily': 'Sarabun, sans-serif'}),
                html.Iframe(id='choropleth-map', style={'width': '100%', 'height': '600px', 'border': '1px solid #ddd'})
            ])
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                html.H4("สถิติการจมน้ำ 30 จังหวัดแรก", className="text-center mb-3",
                       style={'fontFamily': 'Sarabun, sans-serif'}),
                dcc.Graph(id='bar-graph', style={'height': '500px'})
            ])
        ], className="mb-4"),
    ]),
    
    # Content ข้อมูลมรณบัตร
    html.Div(id='death-cert-content', style={'display': 'none'}, children=[
        dbc.Row([
            dbc.Col([
                html.H4("แผนที่แสดงข้อมูลมรณบัตรจากการจมน้ำรายอำเภอ (2563-2567)", 
                       className="text-center mb-3",
                       style={'fontFamily': 'Sarabun, sans-serif'}),
                html.Iframe(id='death-cert-map', style={'width': '100%', 'height': '600px', 'border': '1px solid #ddd'})
            ])
        ], className="mb-4"),
    ]),
    
    # แหล่งที่มา
    dbc.Row([
        dbc.Col([
            html.P("แหล่งที่มา: กรมควบคุมโรค กระทรวงสาธารณสุข", 
                   style={'fontFamily': 'Sarabun', 'fontSize': '11px', 'color': '#666', 'textAlign': 'left'})
        ])
    ], className="mt-4"),
    
], fluid=True, style={'fontFamily': 'Sarabun, sans-serif'})

# =============== Callbacks ===============

@app.callback(
    [Output('drowning-filters', 'style'),
     Output('death-cert-filters', 'style'),
     Output('drowning-content', 'style'),
     Output('death-cert-content', 'style'),
     Output('heatmap-options-drowning', 'style'),
     Output('heatmap-options-death', 'style')],
    Input('data-tabs', 'active_tab')
)
def toggle_tab_content(active_tab):
    if active_tab == "drowning-tab":
        return ({'display': 'block'}, {'display': 'none'}, {'display': 'block'}, {'display': 'none'},
                {'display': 'block'}, {'display': 'none'})
    else:
        return ({'display': 'none'}, {'display': 'block'}, {'display': 'none'}, {'display': 'block'},
                {'display': 'none'}, {'display': 'block'})

@app.callback(
    Output('district-dropdown', 'options'),
    Input('province-dropdown', 'value')
)
def update_district(province):
    if len(df) == 0 or 'อำเภอ' not in df.columns:
        return [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    
    if province == 'ALL':
        districts = df['อำเภอ'].dropna().unique()
    else:
        districts = df[df['จังหวัด'] == province]['อำเภอ'].dropna().unique()
    
    return [{'label': 'ทั้งหมด', 'value': 'ALL'}] + \
           [{'label': str(i), 'value': str(i)} for i in sorted(districts)]

@app.callback(
    Output('subdistrict-dropdown', 'options'),
    Input('district-dropdown', 'value'),
    State('province-dropdown', 'value')
)
def update_subdistrict(district, province):
    if len(df) == 0 or 'ตำบล' not in df.columns:
        return [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    
    filtered_df = df.copy()
    if province != 'ALL':
        filtered_df = filtered_df[filtered_df['จังหวัด'] == province]
    if district != 'ALL':
        filtered_df = filtered_df[filtered_df['อำเภอ'] == district]
    
    subdistricts = filtered_df['ตำบล'].dropna().unique()
    return [{'label': 'ทั้งหมด', 'value': 'ALL'}] + \
           [{'label': str(i), 'value': str(i)} for i in sorted(subdistricts)]

@app.callback(
    Output('dc-district-dropdown', 'options'),
    Input('dc-province-dropdown', 'value')
)
def update_dc_district(province):
    if len(df_death_cert) == 0 or 'อำเภอ' not in df_death_cert.columns:
        return [{'label': 'ทั้งหมด', 'value': 'ALL'}]
    
    if province == 'ALL':
        districts = df_death_cert['อำเภอ'].dropna().unique()
    else:
        districts = df_death_cert[df_death_cert['จังหวัด'] == province]['อำเภอ'].dropna().unique()
    
    return [{'label': 'ทั้งหมด', 'value': 'ALL'}] + \
           [{'label': str(i), 'value': str(i)} for i in sorted(districts)]

# =============== Main Dashboard Update Callback ===============
@app.callback(
    [Output('choropleth-map', 'srcDoc'),
     Output('bar-graph', 'figure'),
     Output('statistics-output', 'children'),
     Output('status-pie-chart', 'figure'),
     Output('status-details', 'children'),
     Output('frequency-histogram', 'figure'),
     Output('heatmap-map', 'figure'),
     Output('death-cert-map', 'srcDoc')],
    [Input('search-button', 'n_clicks'),
     Input('province-dropdown', 'value'),
     Input('district-dropdown', 'value'),
     Input('subdistrict-dropdown', 'value'),
     Input('zone-dropdown', 'value'),
     Input('dc-province-dropdown', 'value'),
     Input('dc-district-dropdown', 'value'),
     Input('dc-zone-dropdown', 'value'),
     Input('month-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('age-dropdown', 'value'),
     Input('map-type-radio', 'value'),
     Input('data-tabs', 'active_tab')]
)
def update_dashboard(n_clicks, province, district, subdistrict, zone, 
                     dc_province, dc_district, dc_zone,
                     month, year, age, map_type, active_tab):
    
    # กรองข้อมูลตาม Tab
    if active_tab == "death-cert-tab":
        base_df = df_death_cert.copy() if len(df_death_cert) > 0 else pd.DataFrame()
        filtered_df = base_df.copy()
        
        if len(filtered_df) > 0:
            if dc_province != 'ALL' and 'จังหวัด' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['จังหวัด'] == dc_province]
            if dc_district != 'ALL' and 'อำเภอ' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['อำเภอ'] == dc_district]
            if dc_zone != 'ALL' and 'เขต' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['เขต'] == str(dc_zone).strip()]
        
        map_type = 'deceased_rate'
    else:
        base_df = df.copy() if len(df) > 0 else pd.DataFrame()
        filtered_df = base_df.copy()
        
        if len(filtered_df) > 0:
            if province != 'ALL' and 'จังหวัด' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['จังหวัด'] == province]
            if district != 'ALL' and 'อำเภอ' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['อำเภอ'] == district]
            if subdistrict != 'ALL' and 'ตำบล' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['ตำบล'] == subdistrict]
            if zone != 'ALL' and 'เขต' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['เขต'] == str(zone).strip()]
    
    # กรองเพิ่มเติม
    if len(filtered_df) > 0:
        if month != 'ALL' and 'เดือน' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['เดือน'] == month]
        if year != 'ALL' and 'ปี' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['ปี'] == year]
        if age != 'ALL' and 'อายุ' in filtered_df.columns:
            if age == '<15':
                filtered_df = filtered_df[filtered_df['อายุ'] < 15]
            elif age == '15+':
                filtered_df = filtered_df[filtered_df['อายุ'] >= 15]
    
    # Handle Empty Data
    if len(filtered_df) == 0:
        empty_map = folium.Map(location=[13.7563, 100.5018], zoom_start=6)
        map_html = empty_map._repr_html_()
        
        fig = go.Figure()
        fig.add_annotation(text="ไม่มีข้อมูล", showarrow=False)
        
        return (map_html, fig, html.Div("ไม่มีข้อมูล", className="text-center text-danger"),
                fig, html.Div("ไม่มีข้อมูล"), fig, fig, map_html)
    
    # สร้าง Pie Chart ตาม Tab
    if active_tab == "death-cert-tab":
        death_rates = calculate_death_summary_rates(filtered_df)
        
        pie_labels = ['1 ครั้ง', '2 ครั้ง', '3 ครั้ง', '4 ครั้ง', '≥5 ครั้ง']
        pie_values = [
            death_rates['class_1']['count'],
            death_rates['class_2']['count'],
            death_rates['class_3']['count'],
            death_rates['class_4']['count'],
            death_rates['class_5']['count']
        ]
        pie_colors = ['#C8E6C9', '#4CAF50', '#FFEB3B', '#FFB6C1', '#E53935']
        
        pie_fig = go.Figure(data=[go.Pie(
            labels=pie_labels,
            values=pie_values,
            hole=0.4,
            marker=dict(colors=pie_colors),
            textinfo='percent',
            textposition='inside',
            textfont=dict(size=12, family='Sarabun'),
            hovertemplate="<b>%{label}</b><br>จำนวน: %{value:,} ราย<br>อัตรา: %{percent}<extra></extra>"
        )])
        
        pie_fig.update_layout(
            title=dict(text=f"อัตราการเสียชีวิตจากมรณบัตร (รวม {death_rates['total']:,} ราย)", 
                      x=0.5, font=dict(size=13, family='Sarabun')),
            font=dict(family='Sarabun'),
            showlegend=True,
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=-0.2, 
                xanchor="center", 
                x=0.5,
                font=dict(size=11)
            ),
            margin=dict(t=50, b=100, l=20, r=20)
        )
        
        status_details = dbc.Card([
            dbc.CardHeader(html.H6("รายละเอียดข้อมูล", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([html.Strong("อัตราการเสียชีวิต 1 ครั้ง", style={'color': '#4CAF50'})], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_1']['count']:,} ราย")], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_1']['rate']:.2f}%", className="badge bg-success")], width=4),
                ], className="mb-1 align-items-center", style={'fontSize': '12px'}),
                dbc.Row([
                    dbc.Col([html.Strong("อัตราการเสียชีวิต 2 ครั้ง", style={'color': '#388E3C'})], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_2']['count']:,} ราย")], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_2']['rate']:.2f}%", className="badge", style={'backgroundColor': '#4CAF50'})], width=4),
                ], className="mb-1 align-items-center", style={'fontSize': '12px'}),
                dbc.Row([
                    dbc.Col([html.Strong("อัตราการเสียชีวิต 3 ครั้ง", style={'color': '#FBC02D'})], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_3']['count']:,} ราย")], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_3']['rate']:.2f}%", className="badge", style={'backgroundColor': '#FFEB3B', 'color': '#000'})], width=4),
                ], className="mb-1 align-items-center", style={'fontSize': '12px'}),
                dbc.Row([
                    dbc.Col([html.Strong("อัตราการเสียชีวิต 4 ครั้ง", style={'color': '#FFB6C1'})], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_4']['count']:,} ราย")], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_4']['rate']:.2f}%", className="badge", style={'backgroundColor': '#FFB6C1', 'color': '#000'})], width=4),
                ], className="mb-1 align-items-center", style={'fontSize': '12px'}),
                dbc.Row([
                    dbc.Col([html.Strong("อัตราการเสียชีวิต ≥5 ครั้ง", style={'color': '#E53935'})], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_5']['count']:,} ราย")], width=4),
                    dbc.Col([html.Span(f"{death_rates['class_5']['rate']:.2f}%", className="badge bg-danger")], width=4),
                ], className="mb-1 align-items-center", style={'fontSize': '12px'}),
                html.Hr(className="my-2"),
                dbc.Row([
                    dbc.Col([html.Strong("รวมทั้งหมด")], width=4),
                    dbc.Col([html.Span(f"{death_rates['total']:,} ราย", className="fw-bold text-primary")], width=4),
                    dbc.Col([html.Span("100.00%", className="badge bg-primary")], width=4),
                ], className="align-items-center", style={'fontSize': '12px'}),
            ], style={'padding': '10px'})
        ])
        
    else:
        status_rates = calculate_status_rates(filtered_df)
        
        pie_labels = ['เสียชีวิต', 'บาดเจ็บ', 'ไม่บาดเจ็บ']
        pie_values = [
            status_rates['deceased']['count'],
            status_rates['injured']['count'],
            status_rates['not_injured']['count']
        ]
        pie_colors = ['#E74C3C', '#F39C12', '#27AE60']
        
        pie_fig = go.Figure(data=[go.Pie(
            labels=pie_labels,
            values=pie_values,
            hole=0.4,
            marker=dict(colors=pie_colors),
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=11, family='Sarabun'),
            hovertemplate="<b>%{label}</b><br>จำนวน: %{value:,} ราย<br>อัตรา: %{percent}<extra></extra>"
        )])
        
        pie_fig.update_layout(
            title=dict(text=f"สถานะการจมน้ำ (รวม {status_rates['total']:,} ราย)", 
                      x=0.5, font=dict(size=13, family='Sarabun')),
            font=dict(family='Sarabun'),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
            margin=dict(t=50, b=80)
        )
        
        status_details = dbc.Card([
            dbc.CardHeader(html.H6("รายละเอียดข้อมูล", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([html.Strong("อัตราการเสียชีวิต", style={'color': '#E74C3C'})], width=4),
                    dbc.Col([html.Span(f"{status_rates['deceased']['count']:,} ราย")], width=4),
                    dbc.Col([html.Span(f"{status_rates['deceased']['rate']:.2f}%", className="badge bg-danger")], width=4),
                ], className="mb-1 align-items-center", style={'fontSize': '12px'}),
                dbc.Row([
                    dbc.Col([html.Strong("อัตราการบาดเจ็บ", style={'color': '#F39C12'})], width=4),
                    dbc.Col([html.Span(f"{status_rates['injured']['count']:,} ราย")], width=4),
                    dbc.Col([html.Span(f"{status_rates['injured']['rate']:.2f}%", className="badge bg-warning")], width=4),
                ], className="mb-1 align-items-center", style={'fontSize': '12px'}),
                dbc.Row([
                    dbc.Col([html.Strong("อัตราการไม่บาดเจ็บ", style={'color': '#27AE60'})], width=4),
                    dbc.Col([html.Span(f"{status_rates['not_injured']['count']:,} ราย")], width=4),
                    dbc.Col([html.Span(f"{status_rates['not_injured']['rate']:.2f}%", className="badge bg-success")], width=4),
                ], className="mb-1 align-items-center", style={'fontSize': '12px'}),
                html.Hr(className="my-2"),
                dbc.Row([
                    dbc.Col([html.Strong("รวมทั้งหมด")], width=4),
                    dbc.Col([html.Span(f"{status_rates['total']:,} ราย", className="fw-bold text-primary")], width=4),
                    dbc.Col([html.Span("100.00%", className="badge bg-primary")], width=4),
                ], className="align-items-center", style={'fontSize': '12px'}),
            ], style={'padding': '10px'})
        ])
    
    # สร้าง Heatmap Map
    if active_tab == "death-cert-tab":
        heatmap_fig = create_shapefile_heatmap(filtered_df, map_type, data_type='death_cert')
    else:
        heatmap_fig = create_shapefile_heatmap(filtered_df, map_type, data_type='drowning')
    
    # สร้าง Histogram ความถี่
    freq_data = calculate_frequency_by_year(filtered_df)
    
    if freq_data and len(freq_data['years']) > 0:
        hist_fig = go.Figure()
        
        hist_fig.add_trace(go.Bar(
            name='ร้อยละการเกิดเหตุ',
            x=freq_data['years'],
            y=freq_data['incident_rate'],
            marker_color='#85C1E9',
            text=[f"{rate:.2f}%" for rate in freq_data['incident_rate']],
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate="<b>ปี %{x}</b><br>ร้อยละ: %{y:.2f}%<br>จำนวน: %{customdata:,} ราย<extra></extra>",
            customdata=freq_data['incident_count']
        ))
        
        hist_fig.add_trace(go.Bar(
            name='ร้อยละการเสียชีวิต',
            x=freq_data['years'],
            y=freq_data['death_rate'],
            marker_color='#F1948A',
            text=[f"{rate:.2f}%" for rate in freq_data['death_rate']],
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate="<b>ปี %{x}</b><br>ร้อยละ: %{y:.2f}%<br>จำนวน: %{customdata:,} ราย<extra></extra>",
            customdata=freq_data['death_count']
        ))
        
        max_rate = max(max(freq_data['incident_rate']) if freq_data['incident_rate'] else 0, 
                       max(freq_data['death_rate']) if freq_data['death_rate'] else 0)
        
        hist_fig.update_layout(
            title=dict(text='ร้อยละความถี่การเกิดเหตุและเสียชีวิตจากการจมน้ำรายปี', x=0.5, font=dict(size=14, family='Sarabun')),
            xaxis_title='ปี',
            yaxis_title='ร้อยละ (%)',
            yaxis=dict(ticksuffix='%', range=[0, max_rate * 1.3] if max_rate > 0 else [0, 100]),
            barmode='group',
            font=dict(family='Sarabun'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"รวมเกิดเหตุ: {freq_data['total_incident']:,} ราย | รวมเสียชีวิต: {freq_data['total_death']:,} ราย",
                xref="paper", yref="paper", x=0.5, y=-0.15, showarrow=False, font=dict(size=11), bgcolor="lightgray", borderpad=4
            )],
            margin=dict(b=100)
        )
    else:
        hist_fig = go.Figure()
        hist_fig.add_annotation(text="ไม่มีข้อมูลความถี่", showarrow=False)
    
    # สร้างแผนที่ Choropleth จาก Shapefile โดยตรง
    choropleth_html = create_choropleth_from_shapefile('drowning')
    death_cert_html = create_choropleth_from_shapefile('death_cert')
    
    # สร้างกราฟแท่ง
    if 'จังหวัด' in filtered_df.columns and len(filtered_df) > 0:
        if 'สรุป' in filtered_df.columns:
            province_summary = filtered_df.groupby('จังหวัด')['สรุป'].sum().reset_index()
            province_summary.columns = ['จังหวัด', 'จำนวนรวม']
        else:
            province_summary = filtered_df.groupby('จังหวัด').size().reset_index(name='จำนวนรวม')
        
        province_summary['กลุ่ม'] = province_summary['จำนวนรวม'].apply(
            lambda x: 'เสียชีวิต (=1)' if x == 1 else 'เสียชีวิต (>1)'
        )
        province_summary = province_summary.sort_values('จำนวนรวม', ascending=False).head(30)
        
        bar_fig = px.bar(
            province_summary,
            x='จังหวัด',
            y='จำนวนรวม',
            color='กลุ่ม',
            color_discrete_map={'เสียชีวิต (=1)': '#90EE90', 'เสียชีวิต (>1)': '#FF4444'},
            text='จำนวนรวม'
        )
        bar_fig.update_traces(textposition='outside')
        bar_fig.update_layout(
            xaxis_tickangle=-45,
            font_family="Sarabun",
            height=500,
            legend=dict(title='ระดับ', orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    else:
        bar_fig = go.Figure()
        bar_fig.add_annotation(text="ไม่มีข้อมูล", showarrow=False)
    
    # สร้างสถิติ
    age_under_15 = len(filtered_df[filtered_df['อายุ'] < 15]) if 'อายุ' in filtered_df.columns else 0
    age_15_plus = len(filtered_df[filtered_df['อายุ'] >= 15]) if 'อายุ' in filtered_df.columns else 0
    avg_age = filtered_df['อายุ'].mean() if 'อายุ' in filtered_df.columns and len(filtered_df) > 0 else 0
    
    if 'สรุป' in filtered_df.columns:
        range_low = len(filtered_df[filtered_df['สรุป'] == 1])
        range_high = len(filtered_df[filtered_df['สรุป'] > 1])
    else:
        if 'สถานะ' in filtered_df.columns:
            death_counts = filtered_df[filtered_df['สถานะ'] == 'เสียชีวิต'].groupby('จังหวัด').size()
            range_low = (death_counts == 1).sum()
            range_high = (death_counts > 1).sum()
        else:
            range_low = 0
            range_high = 0
    
    stats = dbc.Row([
        dbc.Col([dbc.Card([dbc.CardBody([
            html.H6("จำนวนเหตุการณ์", className="text-center", style={'fontSize': '12px'}),
            html.H3(f"{len(filtered_df):,}", className="text-center text-primary")
        ])])], width=2),
        dbc.Col([dbc.Card([dbc.CardBody([
            html.H6("อายุต่ำกว่า 15 ปี", className="text-center", style={'fontSize': '12px'}),
            html.H3(f"{age_under_15:,}", className="text-center text-info")
        ])])], width=2),
        dbc.Col([dbc.Card([dbc.CardBody([
            html.H6("อายุ 15+ ปี", className="text-center", style={'fontSize': '12px'}),
            html.H3(f"{age_15_plus:,}", className="text-center", style={'color': '#6f42c1'})
        ])])], width=2),
        dbc.Col([dbc.Card([dbc.CardBody([
            html.H6("เสียชีวิต (=1)", className="text-center", style={'fontSize': '12px'}),
            html.H3(f"{range_low:,}", className="text-center text-success")
        ])])], width=2),
        dbc.Col([dbc.Card([dbc.CardBody([
            html.H6("เสียชีวิต (>1)", className="text-center", style={'fontSize': '12px'}),
            html.H3(f"{range_high:,}", className="text-center text-danger")
        ])])], width=2),
        dbc.Col([dbc.Card([dbc.CardBody([
            html.H6("อายุเฉลี่ย", className="text-center", style={'fontSize': '12px'}),
            html.H3(f"{avg_age:.1f}" if avg_age > 0 else "N/A", className="text-center text-warning")
        ])])], width=2),
    ])
    
    return choropleth_html, bar_fig, stats, pie_fig, status_details, hist_fig, heatmap_fig, death_cert_html

# =============== รันแอพ ===============
if __name__ == '__main__':
    app.run(debug=True, port=8051)