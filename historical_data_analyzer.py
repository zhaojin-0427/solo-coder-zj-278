import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

from data_processor import classify_color, parse_hex_color, hex_to_lab, hex_to_hsl


REQUIRED_HISTORY_COLUMNS = [
    'project_name', 'project_type', 'completion_date',
    'color_name', 'color_hex', 'material', 'quantity_used',
    'effect_rating', 'customer_feedback'
]


SEASON_THEMES = {
    '春季': {
        'keywords': ['清新', '柔和', '明亮', '花朵', '嫩绿', '樱花'],
        'dominant_families': ['粉色系', '绿色系', '黄色系', '青色系'],
        'typical_colors': ['#FFB6C1', '#98FB98', '#FFFACD', '#87CEEB']
    },
    '夏季': {
        'keywords': ['清爽', '清凉', '明亮', '海洋', '阳光', '沙滩'],
        'dominant_families': ['蓝色系', '青色系', '白色', '黄色系'],
        'typical_colors': ['#00CED1', '#87CEFA', '#FFF8DC', '#FF6347']
    },
    '秋季': {
        'keywords': ['温暖', '浓郁', '大地', '丰收', '枫叶', '栗子'],
        'dominant_families': ['橙色系', '棕色', '黄色系', '红色系'],
        'typical_colors': ['#D2691E', '#CD853F', '#F4A460', '#8B4513']
    },
    '冬季': {
        'keywords': ['温暖', '深沉', '节日', '雪花', '圣诞', '浓郁'],
        'dominant_families': ['红色系', '灰色', '棕色', '紫色系'],
        'typical_colors': ['#DC143C', '#708090', '#8B0000', '#4B0082']
    },
    '节日庆典': {
        'keywords': ['喜庆', '华丽', '金色', '红色', '礼物', '派对'],
        'dominant_families': ['红色系', '金色', '紫色系', '黑色'],
        'typical_colors': ['#FFD700', '#C71585', '#4B0082', '#FF4500']
    }
}


STYLE_PROFILES = {
    '简约北欧': {
        'color_count_range': (2, 4),
        'preferred_families': ['中性色', '蓝色系', '灰色', '白色'],
        'material_preference': ['羊毛', '棉', '马海毛'],
        'harmony_target': 'monochromatic'
    },
    '复古森系': {
        'color_count_range': (3, 5),
        'preferred_families': ['绿色系', '棕色', '米色', '橙色系'],
        'material_preference': ['羊毛', '亚麻', '棉'],
        'harmony_target': 'analogous'
    },
    '波西米亚': {
        'color_count_range': (4, 6),
        'preferred_families': ['红色系', '橙色系', '紫色系', '黄色系'],
        'material_preference': ['羊毛', '棉', '腈纶'],
        'harmony_target': 'triadic'
    },
    '清新少女': {
        'color_count_range': (3, 5),
        'preferred_families': ['粉色系', '紫色系', '白色', '黄色系'],
        'material_preference': ['棉', '马海毛', '蚕丝'],
        'harmony_target': 'analogous'
    },
    '商务通勤': {
        'color_count_range': (2, 3),
        'preferred_families': ['灰色', '黑色', '棕色', '蓝色系'],
        'material_preference': ['羊毛', '蚕丝', '棉'],
        'harmony_target': 'monochromatic'
    }
}


def _calc_color_distance_cie2000(hex1: str, hex2: str) -> float:
    if not hex1 or not hex2:
        return float('inf')
    try:
        rgb1 = sRGBColor.new_from_rgb_hex(hex1)
        rgb2 = sRGBColor.new_from_rgb_hex(hex2)
        lab1 = convert_color(rgb1, LabColor)
        lab2 = convert_color(rgb2, LabColor)
        return delta_e_cie2000(lab1, lab2)
    except Exception:
        return float('inf')


def load_and_validate_history(file) -> Tuple[Optional[pd.DataFrame], List[str]]:
    if file is None:
        return None, ['未提供历史数据文件']

    try:
        df = pd.read_csv(file)
    except Exception as e:
        return None, [f'无法读取CSV文件: {str(e)}']

    warnings = []
    missing = [c for c in REQUIRED_HISTORY_COLUMNS if c not in df.columns]
    if missing:
        warnings.append(f'缺少推荐列: {", ".join(missing)}')

    if 'project_name' not in df.columns:
        return None, ['缺少必需列: project_name']

    if 'color_hex' in df.columns:
        df['color_hex'] = df['color_hex'].apply(parse_hex_color)

    if 'color_hex' in df.columns and 'color_name' in df.columns:
        df['color_family'] = df.apply(
            lambda row: classify_color(row.get('color_hex'), row.get('color_name')),
            axis=1
        )

    if 'material' not in df.columns:
        df['material'] = '未知'
        warnings.append('缺少 material 列，已填充为"未知"')
    df['material'] = df['material'].fillna('未知').astype(str)

    if 'quantity_used' in df.columns:
        df['quantity_used'] = pd.to_numeric(df['quantity_used'], errors='coerce').fillna(0)

    if 'effect_rating' in df.columns:
        df['effect_rating'] = pd.to_numeric(df['effect_rating'], errors='coerce')
        df['effect_rating'] = df['effect_rating'].clip(0, 5).fillna(3)
    else:
        df['effect_rating'] = 3.0
        warnings.append('缺少 effect_rating 列，默认评分为3.0')

    if 'completion_date' in df.columns:
        df['completion_date'] = pd.to_datetime(df['completion_date'], errors='coerce')
    else:
        df['completion_date'] = pd.NaT

    if 'customer_feedback' not in df.columns:
        df['customer_feedback'] = ''

    return df, warnings


def build_experience_library(history_df: pd.DataFrame) -> Dict[str, Any]:
    if history_df is None or len(history_df) == 0:
        return {
            'total_projects': 0,
            'color_material_stats': pd.DataFrame(),
            'successful_combinations': [],
            'season_patterns': {},
            'style_patterns': {},
            'material_success_rates': pd.DataFrame()
        }

    project_groups = history_df.groupby('project_name')

    total_projects = history_df['project_name'].nunique()

    cm_stats = history_df.groupby(['color_family', 'material']).agg(
        use_count=('project_name', 'nunique'),
        total_quantity=('quantity_used', 'sum'),
        avg_rating=('effect_rating', 'mean'),
        max_rating=('effect_rating', 'max')
    ).reset_index()
    cm_stats = cm_stats.sort_values(['avg_rating', 'use_count'], ascending=False)

    successful = []
    for pname, group in project_groups:
        avg_rating = group['effect_rating'].mean()
        if avg_rating >= 4.0:
            colors = []
            materials = []
            for _, row in group.iterrows():
                colors.append({
                    'color_name': row.get('color_name', ''),
                    'color_hex': row.get('color_hex', ''),
                    'color_family': row.get('color_family', '')
                })
                materials.append(row.get('material', ''))
            successful.append({
                'project_name': pname,
                'project_type': group['project_type'].iloc[0] if 'project_type' in group.columns else '',
                'avg_rating': round(avg_rating, 2),
                'colors': colors,
                'materials': list(set(materials)),
                'completion_date': group['completion_date'].iloc[0],
                'feedback': group['customer_feedback'].iloc[0] if 'customer_feedback' in group.columns else ''
            })
    successful = sorted(successful, key=lambda x: x['avg_rating'], reverse=True)

    season_patterns = {}
    if 'completion_date' in history_df.columns:
        def _infer_season(date_val):
            if pd.isna(date_val):
                return None
            month = date_val.month
            if month in [3, 4, 5]:
                return '春季'
            elif month in [6, 7, 8]:
                return '夏季'
            elif month in [9, 10, 11]:
                return '秋季'
            else:
                return '冬季'

        history_df = history_df.copy()
        history_df['season'] = history_df['completion_date'].apply(_infer_season)

        for season in ['春季', '夏季', '秋季', '冬季']:
            season_data = history_df[history_df['season'] == season]
            if len(season_data) > 0:
                top_colors = season_data.groupby('color_family').agg(
                    count=('project_name', 'nunique'),
                    avg_rating=('effect_rating', 'mean')
                ).reset_index().sort_values('count', ascending=False).head(5)
                season_patterns[season] = {
                    'project_count': season_data['project_name'].nunique(),
                    'top_color_families': top_colors.to_dict('records'),
                    'avg_rating': round(season_data['effect_rating'].mean(), 2)
                }

    material_stats = history_df.groupby('material').agg(
        project_count=('project_name', 'nunique'),
        avg_rating=('effect_rating', 'mean'),
        total_usage=('quantity_used', 'sum')
    ).reset_index()
    material_stats['success_rate'] = (material_stats['avg_rating'] / 5.0 * 100).round(1)
    material_stats = material_stats.sort_values('success_rate', ascending=False)

    return {
        'total_projects': total_projects,
        'color_material_stats': cm_stats,
        'successful_combinations': successful,
        'season_patterns': season_patterns,
        'style_patterns': {},
        'material_success_rates': material_stats
    }


def calculate_series_history_similarity(
    series_palette: List[Dict[str, Any]],
    experience_library: Dict[str, Any],
    target_season: str = None
) -> Dict[str, Any]:
    successful = experience_library.get('successful_combinations', [])
    if not successful or not series_palette:
        return {
            'best_match': None,
            'best_similarity': 0,
            'all_matches': [],
            'season_match_score': 0
        }

    series_hexes = [c.get('color_hex') for c in series_palette if c.get('color_hex')]
    series_families = set(c.get('color_family', '') for c in series_palette)

    all_matches = []
    for proj in successful:
        proj_hexes = [c.get('color_hex') for c in proj.get('colors', []) if c.get('color_hex')]
        proj_families = set(c.get('color_family', '') for c in proj.get('colors', []))

        if not proj_hexes or not series_hexes:
            continue

        distances = []
        for sh in series_hexes:
            min_d = min(_calc_color_distance_cie2000(sh, ph) for ph in proj_hexes)
            distances.append(min_d)

        avg_distance = np.mean(distances) if distances else 100
        color_similarity = max(0, 100 - avg_distance * 1.5)

        family_overlap = len(series_families & proj_families) / max(1, len(series_families | proj_families))
        family_score = family_overlap * 100

        total_similarity = color_similarity * 0.6 + family_score * 0.4

        all_matches.append({
            'project_name': proj['project_name'],
            'project_type': proj.get('project_type', ''),
            'similarity': round(total_similarity, 1),
            'color_similarity': round(color_similarity, 1),
            'family_similarity': round(family_score, 1),
            'avg_rating': proj.get('avg_rating', 0),
            'colors': proj.get('colors', []),
            'materials': proj.get('materials', []),
            'feedback': proj.get('feedback', '')
        })

    all_matches = sorted(all_matches, key=lambda x: x['similarity'], reverse=True)
    best_match = all_matches[0] if all_matches else None

    season_score = 0
    if target_season and target_season in SEASON_THEMES:
        season_families = set(SEASON_THEMES[target_season]['dominant_families'])
        overlap = len(series_families & season_families) / max(1, len(season_families))
        season_score = round(overlap * 100, 1)

    return {
        'best_match': best_match,
        'best_similarity': best_match['similarity'] if best_match else 0,
        'all_matches': all_matches[:10],
        'season_match_score': season_score
    }


def analyze_color_material_track_record(
    color_name: str,
    material: str,
    experience_library: Dict[str, Any]
) -> Dict[str, Any]:
    cm_stats = experience_library.get('color_material_stats', pd.DataFrame())
    if cm_stats is None or len(cm_stats) == 0:
        return {
            'used_before': False,
            'use_count': 0,
            'avg_rating': 0,
            'confidence': 'low'
        }

    color_family = classify_color(None, color_name)
    match = cm_stats[
        (cm_stats['color_family'] == color_family) &
        (cm_stats['material'].str.contains(material, case=False, na=False))
    ]

    if len(match) == 0:
        family_match = cm_stats[cm_stats['color_family'] == color_family]
        if len(family_match) > 0:
            return {
                'used_before': False,
                'use_count': 0,
                'avg_rating': round(family_match['avg_rating'].mean(), 2),
                'confidence': 'medium',
                'note': '该材质组合暂无历史记录，但同色系其他材质表现良好'
            }
        return {
            'used_before': False,
            'use_count': 0,
            'avg_rating': 0,
            'confidence': 'low',
            'note': '该组合完全无历史数据'
        }

    row = match.iloc[0]
    use_count = int(row.get('use_count', 0))
    avg_rating = round(float(row.get('avg_rating', 0)), 2)

    confidence = 'high' if use_count >= 3 and avg_rating >= 4.0 else (
        'medium' if use_count >= 2 else 'low'
    )

    return {
        'used_before': True,
        'use_count': use_count,
        'avg_rating': avg_rating,
        'confidence': confidence,
        'total_quantity': float(row.get('total_quantity', 0))
    }
