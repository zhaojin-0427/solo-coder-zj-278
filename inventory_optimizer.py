import pandas as pd
import numpy as np
from datetime import datetime
from data_processor import identify_redundant_shortage, analyze_long_unused, analyze_inventory
from color_theory import get_consumption_suggestions, generate_color_schemes, recommend_project_patterns


def generate_inventory_report(df):
    stats = analyze_inventory(df)
    redundant_shortage = identify_redundant_shortage(df, stats)
    long_unused = analyze_long_unused(df, days_threshold=180)

    report = {}
    report['overview'] = {
        'total_quantity': stats['total_quantity'],
        'total_value': stats['total_value'],
        'total_colors': stats['total_colors'],
        'total_materials': stats['total_materials'],
        'color_families_count': len(stats['color_distribution'])
    }

    report['redundant_shortage'] = redundant_shortage
    report['long_unused'] = long_unused
    report['stats'] = stats

    if len(long_unused) > 0:
        locked_value = (long_unused['quantity'] * long_unused['price']).sum()
        locked_qty = long_unused['quantity'].sum()
        report['overview']['long_unused_count'] = len(long_unused)
        report['overview']['long_unused_quantity'] = locked_qty
        report['overview']['long_unused_value'] = locked_value
    else:
        report['overview']['long_unused_count'] = 0
        report['overview']['long_unused_quantity'] = 0
        report['overview']['long_unused_value'] = 0

    return report


def generate_optimization_actions(report):
    actions = []
    rs = report.get('redundant_shortage', pd.DataFrame())

    if len(rs) > 0:
        redundant = rs[rs['status'] == '过剩']
        for _, row in redundant.iterrows():
            actions.append({
                'priority': '高',
                'type': '消库',
                'target': row['color_family'],
                'detail': row['suggestion'],
                'quantity': row['quantity']
            })

        shortage = rs[rs['status'] == '不足']
        for _, row in shortage.iterrows():
            actions.append({
                'priority': '中',
                'type': '补货建议',
                'target': row['color_family'],
                'detail': row['suggestion'],
                'quantity': row['quantity']
            })

        zero = rs[rs['status'] == '缺货']
        for _, row in zero.iterrows():
            actions.append({
                'priority': '低',
                'type': '可选补充',
                'target': row['color_family'],
                'detail': row['suggestion'],
                'quantity': 0
            })

    long_unused = report.get('long_unused', pd.DataFrame())
    if len(long_unused) > 0:
        for _, row in long_unused.head(5).iterrows():
            suggestions = get_consumption_suggestions(
                row.get('color_family', ''),
                row.get('material', ''),
                row.get('quantity', 0)
            )
            actions.append({
                'priority': '高' if row.get('quantity', 0) >= 5 else '中',
                'type': '长期未用',
                'target': f"{row.get('color_name', '未知')} ({row.get('color_family', '')})",
                'detail': '; '.join(suggestions[:2]),
                'quantity': row.get('quantity', 0)
            })

    if len(actions) == 0:
        actions.append({
            'priority': '低',
            'type': '状态良好',
            'target': '全部库存',
            'detail': '库存分布均衡，无需特别优化',
            'quantity': 0
        })

    return sorted(actions, key=lambda x: {'高': 0, '中': 1, '低': 2}.get(x['priority'], 3))


def build_consumption_plan(long_unused_df, inventory_df, top_n=5):
    if long_unused_df is None or len(long_unused_df) == 0:
        return []

    plans = []
    top_items = long_unused_df.head(top_n)

    for _, row in top_items.iterrows():
        color_family = row.get('color_family', '')
        material = row.get('material', '')
        quantity = row.get('quantity', 0)
        color_name = row.get('color_name', '未知')

        suggestions = get_consumption_suggestions(color_family, material, quantity)

        schemes = {}
        if row.get('color_hex'):
            schemes = generate_color_schemes(row, inventory_df)

        projects = recommend_project_patterns(
            schemes.get('complementary', {}).get('inventory_matches', [row])
        ) if schemes else []

        plans.append({
            'color_name': color_name,
            'color_family': color_family,
            'color_hex': row.get('color_hex'),
            'material': material,
            'quantity': quantity,
            'unused_category': row.get('unused_category', ''),
            'suggestions': suggestions,
            'schemes': schemes,
            'recommended_projects': projects[:3]
        })

    return plans


def inventory_health_score(report):
    score = 100
    overview = report.get('overview', {})

    total_qty = overview.get('total_quantity', 0)
    if total_qty == 0:
        return 0

    locked_qty = overview.get('long_unused_quantity', 0)
    locked_ratio = locked_qty / total_qty if total_qty > 0 else 0
    if locked_ratio > 0.5:
        score -= 30
    elif locked_ratio > 0.3:
        score -= 20
    elif locked_ratio > 0.1:
        score -= 10

    rs = report.get('redundant_shortage', pd.DataFrame())
    if len(rs) > 0:
        redundant = rs[rs['status'] == '过剩']
        shortage = rs[rs['status'] == '不足']
        total_pct = rs['percentage'].sum() if 'percentage' in rs.columns else 0

        if len(redundant) > 3:
            score -= 15
        elif len(redundant) > 1:
            score -= 8

        if len(shortage) > 3:
            score -= 10
        elif len(shortage) > 1:
            score -= 5

    families = overview.get('color_families_count', 0)
    if families < 3:
        score -= 10
    elif families < 5:
        score -= 5

    return max(0, min(100, int(score)))


def get_health_label(score):
    if score >= 85:
        return ('优秀', '#27AE60')
    elif score >= 70:
        return ('良好', '#2ECC71')
    elif score >= 50:
        return ('一般', '#F39C12')
    elif score >= 30:
        return ('较差', '#E67E22')
    else:
        return ('急需优化', '#E74C3C')


def get_material_recommendations(df, target_project=None):
    project_requirements = {
        '围巾': {'materials': ['羊毛', '马海毛', '腈纶'], 'thickness': ['中粗', '粗']},
        '毛衣': {'materials': ['羊毛', '棉', '混纺'], 'thickness': ['中粗', '中']},
        '玩偶': {'materials': ['腈纶', '棉'], 'thickness': ['中', '细']},
        '毯子': {'materials': ['腈纶', '羊毛', '棉'], 'thickness': ['粗', '中粗', '中']},
        '小件装饰': {'materials': ['棉', '腈纶', '蚕丝'], 'thickness': ['细', '中细', '中']}
    }

    if target_project and target_project in project_requirements:
        req = project_requirements[target_project]
        recommended_materials = df[
            df['material'].str.contains('|'.join(req['materials']), case=False, na=False) &
            df['thickness'].str.contains('|'.join(req['thickness']), case=False, na=False)
        ].copy()
    else:
        recommended_materials = df.copy()

    return recommended_materials.sort_values('quantity', ascending=False)
