import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import webcolors
from colormath.color_objects import sRGBColor, LabColor, HSLColor
from colormath.color_conversions import convert_color

COLOR_FAMILIES = {
    '红色系': [(0, 15), (345, 360)],
    '橙色系': [(15, 45)],
    '黄色系': [(45, 75)],
    '绿色系': [(75, 165)],
    '青色系': [(165, 195)],
    '蓝色系': [(195, 255)],
    '紫色系': [(255, 285)],
    '粉色系': [(285, 345)],
    '中性色': ['white', 'gray', 'black', 'beige', 'cream', 'ivory', 'taupe', 'brown']
}

NEUTRAL_NAMES = {
    'white': '白色', 'black': '黑色', 'gray': '灰色', 'grey': '灰色',
    'beige': '米色', 'cream': '奶油色', 'ivory': '象牙色', 'taupe': '灰褐色',
    'brown': '棕色', 'tan': '棕褐色', 'khaki': '卡其色', 'navy': '藏青色',
    'charcoal': '炭灰色', 'silver': '银色', 'gold': '金色'
}


def parse_hex_color(color_str):
    if pd.isna(color_str) or not color_str:
        return None
    color_str = str(color_str).strip().lower()
    if color_str.startswith('#'):
        return color_str
    try:
        rgb = webcolors.name_to_rgb(color_str)
        return webcolors.rgb_to_hex(rgb)
    except ValueError:
        pass
    if len(color_str) == 6 and all(c in '0123456789abcdef' for c in color_str):
        return '#' + color_str
    return None


def hex_to_hsl(hex_color):
    if not hex_color:
        return None
    try:
        rgb = sRGBColor.new_from_rgb_hex(hex_color)
        hsl = convert_color(rgb, HSLColor)
        return (hsl.hsl_h, hsl.hsl_s, hsl.hsl_l)
    except Exception:
        return None


def hex_to_lab(hex_color):
    if not hex_color:
        return None
    try:
        rgb = sRGBColor.new_from_rgb_hex(hex_color)
        lab = convert_color(rgb, LabColor)
        return (lab.lab_l, lab.lab_a, lab.lab_b)
    except Exception:
        return None


def classify_color(hex_color, color_name=None):
    if not hex_color:
        return '未分类'

    if color_name:
        name_lower = str(color_name).strip().lower()
        for key, cn_name in NEUTRAL_NAMES.items():
            if key in name_lower:
                return cn_name if cn_name in ['白色', '黑色', '灰色', '米色', '棕色'] else '中性色'

    hsl = hex_to_hsl(hex_color)
    if not hsl:
        return '未分类'

    h, s, l = hsl

    if s < 0.1 or l < 0.08 or l > 0.92:
        if l < 0.08:
            return '黑色'
        elif l > 0.92:
            return '白色'
        else:
            return '灰色'

    for family, ranges in COLOR_FAMILIES.items():
        if family == '中性色':
            continue
        for h_range in ranges:
            if h_range[0] <= h < h_range[1]:
                return family

    return '未分类'


def load_and_process_data(file):
    try:
        df = pd.read_csv(file)
    except Exception:
        raise ValueError("无法读取CSV文件，请检查文件格式")

    required_cols = ['color_name', 'quantity']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必需列: {', '.join(missing)}。需要列: color_name, quantity, color_hex, material, thickness, last_used_date")

    if 'color_hex' not in df.columns:
        df['color_hex'] = None

    df['color_hex'] = df['color_hex'].apply(parse_hex_color)

    df['color_family'] = df.apply(
        lambda row: classify_color(row['color_hex'], row.get('color_name')),
        axis=1
    )

    if 'material' not in df.columns:
        df['material'] = '未知'
    df['material'] = df['material'].fillna('未知').astype(str)

    if 'thickness' not in df.columns:
        df['thickness'] = '未知'
    df['thickness'] = df['thickness'].fillna('未知').astype(str)

    if 'quantity' in df.columns:
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)

    if 'last_used_date' in df.columns:
        df['last_used_date'] = pd.to_datetime(df['last_used_date'], errors='coerce')
    else:
        df['last_used_date'] = pd.NaT

    if 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    else:
        df['price'] = 0

    df['hsl'] = df['color_hex'].apply(hex_to_hsl)
    df['lab'] = df['color_hex'].apply(hex_to_lab)

    return df


def analyze_inventory(df):
    stats = {}

    stats['total_quantity'] = df['quantity'].sum()
    stats['total_value'] = (df['quantity'] * df['price']).sum()
    stats['total_colors'] = df['color_name'].nunique()
    stats['total_materials'] = df['material'].nunique()

    color_dist = df.groupby('color_family').agg(
        quantity=('quantity', 'sum'),
        count=('color_name', 'nunique')
    ).reset_index()
    color_dist = color_dist.sort_values('quantity', ascending=False)
    stats['color_distribution'] = color_dist

    material_dist = df.groupby('material').agg(
        quantity=('quantity', 'sum'),
        value=('price', lambda x: (df.loc[x.index, 'quantity'] * df.loc[x.index, 'price']).sum())
    ).reset_index()
    material_dist = material_dist.sort_values('quantity', ascending=False)
    stats['material_distribution'] = material_dist

    thickness_dist = df.groupby('thickness').agg(
        quantity=('quantity', 'sum'),
        count=('color_name', 'nunique')
    ).reset_index()
    thickness_dist = thickness_dist.sort_values('quantity', ascending=False)
    stats['thickness_distribution'] = thickness_dist

    material_thickness = df.groupby(['material', 'thickness']).agg(
        quantity=('quantity', 'sum')
    ).reset_index()
    stats['material_thickness'] = material_thickness

    stats['by_family_material'] = df.groupby(['color_family', 'material']).agg(
        quantity=('quantity', 'sum')
    ).reset_index()

    return stats


def identify_redundant_shortage(df, stats):
    color_dist = stats['color_distribution'].copy()
    total_qty = color_dist['quantity'].sum()

    if total_qty > 0:
        color_dist['percentage'] = color_dist['quantity'] / total_qty * 100
    else:
        color_dist['percentage'] = 0

    avg_percentage = color_dist['percentage'].mean() if len(color_dist) > 0 else 0

    redundant = color_dist[color_dist['percentage'] > avg_percentage * 1.5].copy()
    redundant['status'] = '过剩'
    redundant['suggestion'] = redundant['color_family'].apply(
        lambda x: f'{x}占比过高，建议优先使用或搭配其他色系消耗'
    )

    shortage = color_dist[(color_dist['percentage'] < avg_percentage * 0.5) & (color_dist['quantity'] > 0)].copy()
    shortage['status'] = '不足'
    shortage['suggestion'] = shortage['color_family'].apply(
        lambda x: f'{x}库存偏少，可适当补充或作为点缀色使用'
    )

    zero_stock = color_dist[color_dist['quantity'] == 0].copy()
    if len(zero_stock) > 0:
        zero_stock['status'] = '缺货'
        zero_stock['suggestion'] = zero_stock['color_family'].apply(lambda x: f'{x}完全缺货，建议补充')

    result = pd.concat([redundant, shortage, zero_stock], ignore_index=True)
    return result


def analyze_long_unused(df, days_threshold=180):
    today = datetime.now()
    cutoff = today - timedelta(days=days_threshold)

    df_copy = df.copy()
    df_copy['days_unused'] = df_copy['last_used_date'].apply(
        lambda x: (today - x).days if pd.notna(x) else None
    )

    long_unused = df_copy[
        (df_copy['last_used_date'] < cutoff) |
        (df_copy['last_used_date'].isna())
    ].copy()

    long_unused['unused_category'] = long_unused['last_used_date'].apply(
        lambda x: '从未使用' if pd.isna(x) else
        ('超过一年未使用' if (today - x).days > 365 else '超过半年未使用')
    )

    long_unused = long_unused.sort_values('quantity', ascending=False)
    return long_unused
