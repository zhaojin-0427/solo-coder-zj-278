import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from data_processor import classify_color, hex_to_lab, hex_to_hsl
from color_theory import (
    calculate_color_distance,
    generate_color_schemes,
    get_analogous,
    get_monochromatic
)


PROJECT_YARN_REQUIREMENTS = {
    '围巾': {
        '小号': {'base_qty': 3, 'per_color': 1.5},
        '中号': {'base_qty': 5, 'per_color': 2},
        '大号': {'base_qty': 8, 'per_color': 3}
    },
    '毛衣': {
        '儿童': {'base_qty': 8, 'per_color': 3},
        '女士': {'base_qty': 12, 'per_color': 4},
        '男士': {'base_qty': 15, 'per_color': 5}
    },
    '毯子': {
        '婴儿': {'base_qty': 10, 'per_color': 3},
        '沙发': {'base_qty': 20, 'per_color': 5},
        '大床': {'base_qty': 35, 'per_color': 8}
    },
    '玩偶': {
        '小': {'base_qty': 2, 'per_color': 1},
        '中': {'base_qty': 4, 'per_color': 2},
        '大': {'base_qty': 7, 'per_color': 3}
    },
    '帽子': {
        '儿童': {'base_qty': 2, 'per_color': 1},
        '成人': {'base_qty': 3, 'per_color': 1.5}
    },
    '手套': {
        '儿童': {'base_qty': 2, 'per_color': 1},
        '成人': {'base_qty': 3, 'per_color': 1.5}
    },
    '包包': {
        '小': {'base_qty': 3, 'per_color': 1.5},
        '中': {'base_qty': 5, 'per_color': 2},
        '大': {'base_qty': 8, 'per_color': 3}
    },
    '家居装饰': {
        '杯垫套装': {'base_qty': 3, 'per_color': 1},
        '抱枕': {'base_qty': 6, 'per_color': 2},
        '挂毯': {'base_qty': 12, 'per_color': 4}
    }
}


PROJECT_SIZE_OPTIONS = {
    '围巾': ['小号', '中号', '大号'],
    '毛衣': ['儿童', '女士', '男士'],
    '毯子': ['婴儿', '沙发', '大床'],
    '玩偶': ['小', '中', '大'],
    '帽子': ['儿童', '成人'],
    '手套': ['儿童', '成人'],
    '包包': ['小', '中', '大'],
    '家居装饰': ['杯垫套装', '抱枕', '挂毯']
}


PRIORITY_WEIGHTS = {
    '最高': 1.0,
    '高': 0.8,
    '中': 0.5,
    '低': 0.3,
    '最低': 0.1
}


class ProjectRequirement:
    def __init__(
        self,
        project_id: str,
        project_type: str,
        target_size: str,
        primary_color_preference: Optional[str] = None,
        primary_color_hex: Optional[str] = None,
        material_restrictions: Optional[List[str]] = None,
        budget_limit: Optional[float] = None,
        delivery_priority: str = '中',
        color_count: int = 3
    ):
        self.project_id = project_id
        self.project_type = project_type
        self.target_size = target_size
        self.primary_color_preference = primary_color_preference
        self.primary_color_hex = primary_color_hex
        self.material_restrictions = material_restrictions or []
        self.budget_limit = budget_limit
        self.delivery_priority = delivery_priority
        self.color_count = color_count
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'project_id': self.project_id,
            'project_type': self.project_type,
            'target_size': self.target_size,
            'primary_color_preference': self.primary_color_preference,
            'primary_color_hex': self.primary_color_hex,
            'material_restrictions': self.material_restrictions,
            'budget_limit': self.budget_limit,
            'delivery_priority': self.delivery_priority,
            'color_count': self.color_count
        }


def estimate_yarn_requirement(project: ProjectRequirement) -> Dict[str, Any]:
    proj_type = project.project_type
    size = project.target_size

    if proj_type not in PROJECT_YARN_REQUIREMENTS:
        proj_type = '围巾'

    req_table = PROJECT_YARN_REQUIREMENTS[proj_type]
    if size not in req_table:
        size = list(req_table.keys())[0]

    req = req_table[size]
    base_qty = req['base_qty']
    per_color = req['per_color']
    color_count = max(2, min(6, project.color_count))

    total_qty = base_qty + per_color * (color_count - 1)

    return {
        'total_yarn_needed': total_qty,
        'color_count': color_count,
        'primary_ratio': 0.5,
        'secondary_ratio': 0.35,
        'accent_ratio': 0.15,
        'per_color_quantities': _distribute_quantities(total_qty, color_count)
    }


def _distribute_quantities(total: float, n_colors: int) -> List[float]:
    if n_colors == 1:
        return [total]
    if n_colors == 2:
        return [total * 0.6, total * 0.4]

    ratios = [0.45, 0.3, 0.15]
    remaining = total - sum(r * total for r in ratios)
    if n_colors > 3:
        extra = [remaining / (n_colors - 3)] * (n_colors - 3)
        ratios.extend([e / total for e in extra])
        ratios = [r / sum(ratios) for r in ratios]

    return [r * total for r in ratios[:n_colors]]


def find_candidate_colors(
    project: ProjectRequirement,
    inventory_df: pd.DataFrame
) -> pd.DataFrame:
    candidates = inventory_df.copy()

    if project.material_restrictions:
        pattern = '|'.join(project.material_restrictions)
        candidates = candidates[
            candidates['material'].str.contains(pattern, case=False, na=False)
        ]

    if project.primary_color_preference:
        pref_family = classify_color(
            project.primary_color_hex,
            project.primary_color_preference
        )
        same_family = candidates[candidates['color_family'] == pref_family].copy()
        others = candidates[candidates['color_family'] != pref_family].copy()

        if project.primary_color_hex:
            same_family['color_match_score'] = same_family['color_hex'].apply(
                lambda h: 100 - min(100, calculate_color_distance(
                    project.primary_color_hex, h
                ))
            )
            same_family = same_family.sort_values(
                'color_match_score', ascending=False
            )
            others['color_match_score'] = 0
            candidates = pd.concat([same_family, others], ignore_index=True)
        else:
            candidates = pd.concat([same_family, others], ignore_index=True)

    if 'color_match_score' not in candidates.columns:
        candidates['color_match_score'] = 50.0

    return candidates


def calculate_project_feasibility(
    project: ProjectRequirement,
    inventory_df: pd.DataFrame
) -> Dict[str, Any]:
    requirement = estimate_yarn_requirement(project)
    candidates = find_candidate_colors(project, inventory_df)

    total_needed = requirement['total_yarn_needed']
    total_available = candidates['quantity'].sum() if len(candidates) > 0 else 0

    color_need = requirement['color_count']
    color_avail = len(candidates[candidates['quantity'] > 0]) if len(candidates) > 0 else 0

    quantity_feasibility = min(1.0, total_available / total_needed) if total_needed > 0 else 0
    color_feasibility = min(1.0, color_avail / color_need) if color_need > 0 else 0

    budget_ok = True
    if project.budget_limit:
        avg_price = candidates['price'].mean() if len(candidates) > 0 else 20
        est_cost = avg_price * total_needed
        budget_ok = est_cost <= project.budget_limit

    feasibility_score = (quantity_feasibility * 0.6 + color_feasibility * 0.4) * 100

    status = '可完全完成'
    if feasibility_score >= 90:
        status = '可完全完成'
    elif feasibility_score >= 60:
        status = '部分完成需补货'
    elif feasibility_score >= 30:
        status = '大量补货可完成'
    else:
        status = '难以完成'

    return {
        'project_id': project.project_id,
        'project_type': project.project_type,
        'target_size': project.target_size,
        'delivery_priority': project.delivery_priority,
        'priority_weight': PRIORITY_WEIGHTS.get(project.delivery_priority, 0.5),
        'total_yarn_needed': total_needed,
        'total_yarn_available': total_available,
        'colors_needed': color_need,
        'colors_available': color_avail,
        'quantity_feasibility': quantity_feasibility,
        'color_feasibility': color_feasibility,
        'feasibility_score': round(feasibility_score, 1),
        'status': status,
        'budget_limit': project.budget_limit,
        'budget_ok': budget_ok,
        'estimated_cost': round(
            (candidates['price'].mean() if len(candidates) > 0 else 20) * total_needed, 2
        ),
        'requirement_detail': requirement,
        'candidate_colors': candidates
    }


def detect_color_conflicts(
    projects: List[ProjectRequirement],
    feasibilities: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    conflicts = []
    project_ids = [p.project_id for p in projects]

    for i, pid1 in enumerate(project_ids):
        for pid2 in project_ids[i + 1:]:
            f1 = feasibilities.get(pid1, {})
            f2 = feasibilities.get(pid2, {})

            cand1 = f1.get('candidate_colors', pd.DataFrame())
            cand2 = f2.get('candidate_colors', pd.DataFrame())

            if len(cand1) == 0 or len(cand2) == 0:
                continue

            shared = set(cand1['color_name'].values) & set(cand2['color_name'].values)

            for color_name in shared:
                q1 = cand1[cand1['color_name'] == color_name]['quantity'].sum()
                q2 = cand2[cand2['color_name'] == color_name]['quantity'].sum()
                actual_q = min(q1, q2)

                req_detail1 = f1.get('requirement_detail', {})
                req_detail2 = f2.get('requirement_detail', {})

                per_color1 = max(req_detail1.get('per_color_quantities', [1]))
                per_color2 = max(req_detail2.get('per_color_quantities', [1]))

                demand = per_color1 + per_color2

                if actual_q < demand * 0.8:
                    conflicts.append({
                        'type': '线材短缺冲突',
                        'project_1': pid1,
                        'project_2': pid2,
                        'conflict_color': color_name,
                        'shared_quantity': actual_q,
                        'combined_demand': round(demand, 1),
                        'shortage': round(max(0, demand - actual_q), 1),
                        'severity': '高' if actual_q < demand * 0.3 else (
                            '中' if actual_q < demand * 0.6 else '低'
                        )
                    })

    return conflicts


def calculate_color_reuse_efficiency(
    projects: List[ProjectRequirement],
    feasibilities: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    all_candidates = []
    for pid, f in feasibilities.items():
        cands = f.get('candidate_colors', pd.DataFrame())
        if len(cands) > 0:
            cands = cands.copy()
            cands['project_id'] = pid
            all_candidates.append(cands)

    if not all_candidates:
        return {'reuse_score': 0, 'reusable_colors': [], 'details': {}}

    combined = pd.concat(all_candidates, ignore_index=True)

    color_usage_count = combined.groupby('color_name').agg(
        project_count=('project_id', 'nunique'),
        total_quantity=('quantity', 'first'),
        color_hex=('color_hex', 'first'),
        color_family=('color_family', 'first')
    ).reset_index()

    reusable = color_usage_count[color_usage_count['project_count'] >= 2].copy()
    reusable = reusable.sort_values('project_count', ascending=False)

    total_colors = len(color_usage_count)
    reusable_count = len(reusable)

    reuse_score = (reusable_count / total_colors * 100) if total_colors > 0 else 0
    weighted_score = reuse_score * (
        reusable['project_count'].mean() if reusable_count > 0 else 1
    ) / 3

    return {
        'reuse_score': round(min(100, weighted_score), 1),
        'total_unique_colors': total_colors,
        'reusable_color_count': reusable_count,
        'reusable_colors': reusable.to_dict('records'),
        'color_usage_counts': color_usage_count.to_dict('records')
    }


def generate_shortage_list(
    projects: List[ProjectRequirement],
    feasibilities: Dict[str, Dict[str, Any]],
    strategy: str = 'balanced'
) -> pd.DataFrame:
    all_shortages = []

    for project in projects:
        pid = project.project_id
        f = feasibilities.get(pid, {})
        if not f:
            continue

        req = f.get('requirement_detail', {})
        per_color_qtys = req.get('per_color_quantities', [])
        candidates = f.get('candidate_colors', pd.DataFrame())

        if len(candidates) == 0:
            continue

        sorted_cands = candidates.copy()
        if 'color_match_score' in sorted_cands.columns:
            sorted_cands = sorted_cands.sort_values(
                'color_match_score', ascending=False
            )

        for i, needed_qty in enumerate(per_color_qtys):
            if i < len(sorted_cands):
                row = sorted_cands.iloc[i]
                available = row['quantity']
                shortage = max(0, needed_qty - available)

                if shortage > 0:
                    all_shortages.append({
                        'project_id': pid,
                        'project_type': project.project_type,
                        'color_name': row['color_name'],
                        'color_family': row.get('color_family', ''),
                        'color_hex': row.get('color_hex', ''),
                        'material': row.get('material', ''),
                        'thickness': row.get('thickness', ''),
                        'needed': round(needed_qty, 1),
                        'available': round(available, 1),
                        'shortage': round(shortage, 1),
                        'unit_price': row.get('price', 0),
                        'priority': project.delivery_priority,
                        'priority_weight': PRIORITY_WEIGHTS.get(
                            project.delivery_priority, 0.5
                        )
                    })

    if not all_shortages:
        return pd.DataFrame(columns=[
            'project_id', 'project_type', 'color_name', 'color_family',
            'color_hex', 'material', 'thickness', 'needed', 'available',
            'shortage', 'unit_price', 'priority', 'priority_weight',
            'estimated_cost'
        ])

    df = pd.DataFrame(all_shortages)
    df['estimated_cost'] = (df['shortage'] * df['unit_price']).round(2)
    df = df.sort_values(
        ['priority_weight', 'shortage'],
        ascending=[False, False]
    ).reset_index(drop=True)

    return df


def aggregate_project_analysis(
    projects: List[ProjectRequirement],
    inventory_df: pd.DataFrame
) -> Dict[str, Any]:
    feasibilities = {}
    for p in projects:
        feasibilities[p.project_id] = calculate_project_feasibility(p, inventory_df)

    conflicts = detect_color_conflicts(projects, feasibilities)
    reuse_efficiency = calculate_color_reuse_efficiency(projects, feasibilities)
    shortage_list = generate_shortage_list(projects, feasibilities)

    total_feasibility = np.mean([
        f['feasibility_score'] for f in feasibilities.values()
    ]) if feasibilities else 0

    priority_weighted_score = sum(
        f['feasibility_score'] * f['priority_weight']
        for f in feasibilities.values()
    ) / sum(
        f['priority_weight'] for f in feasibilities.values()
    ) if feasibilities else 0

    total_shortage_cost = shortage_list['estimated_cost'].sum() if len(shortage_list) > 0 else 0
    total_shortage_qty = shortage_list['shortage'].sum() if len(shortage_list) > 0 else 0

    return {
        'projects': [p.to_dict() for p in projects],
        'feasibilities': feasibilities,
        'conflicts': conflicts,
        'reuse_efficiency': reuse_efficiency,
        'shortage_list': shortage_list,
        'summary': {
            'project_count': len(projects),
            'average_feasibility': round(total_feasibility, 1),
            'priority_weighted_feasibility': round(priority_weighted_score, 1),
            'conflict_count': len(conflicts),
            'high_severity_conflicts': len([c for c in conflicts if c['severity'] == '高']),
            'reuse_score': reuse_efficiency['reuse_score'],
            'total_shortage_quantity': round(total_shortage_qty, 1),
            'total_shortage_cost': round(total_shortage_cost, 2)
        }
    }


def calculate_long_unused_consumption_potential(
    inventory_df: pd.DataFrame,
    projects: List[ProjectRequirement],
    feasibilities: Dict[str, Dict[str, Any]],
    days_threshold: int = 180
) -> Dict[str, Any]:
    from data_processor import analyze_long_unused

    long_unused = analyze_long_unused(inventory_df, days_threshold=days_threshold)

    if len(long_unused) == 0:
        return {
            'total_long_unused': 0,
            'consumable_count': 0,
            'consumable_quantity': 0,
            'consumption_ratio': 0,
            'consumable_items': [],
            'locked_value_saved': 0
        }

    all_candidate_names = set()
    for pid, f in feasibilities.items():
        cands = f.get('candidate_colors', pd.DataFrame())
        if len(cands) > 0:
            all_candidate_names.update(cands['color_name'].values)

    consumable = long_unused[
        long_unused['color_name'].isin(all_candidate_names)
    ].copy()

    total_qty = long_unused['quantity'].sum()
    consumable_qty = consumable['quantity'].sum() if len(consumable) > 0 else 0
    ratio = (consumable_qty / total_qty * 100) if total_qty > 0 else 0

    locked_value = (consumable['quantity'] * consumable['price']).sum() if len(consumable) > 0 else 0

    return {
        'total_long_unused': len(long_unused),
        'total_long_unused_quantity': total_qty,
        'consumable_count': len(consumable),
        'consumable_quantity': round(consumable_qty, 1),
        'consumption_ratio': round(ratio, 1),
        'locked_value_saved': round(locked_value, 2),
        'consumable_items': consumable.to_dict('records') if len(consumable) > 0 else []
    }


def export_report_csv(
    analysis_result: Dict[str, Any],
    allocation_result: Dict[str, Any],
    output_path: Optional[str] = None
) -> str:
    rows = []

    feasibilities = analysis_result.get('feasibilities', {})
    allocation = allocation_result.get('allocations', {})
    replenishment = allocation_result.get('replenishment', pd.DataFrame())

    for pid, f in feasibilities.items():
        proj_alloc = allocation.get(pid, {})
        alloc_colors = proj_alloc.get('allocated_colors', [])

        for ac in alloc_colors:
            rows.append({
                '报告类型': '项目分配',
                '项目ID': pid,
                '项目类型': f.get('project_type', ''),
                '优先级': f.get('delivery_priority', ''),
                '可完成度': f.get('feasibility_score', ''),
                '颜色名称': ac.get('color_name', ''),
                '色系': ac.get('color_family', ''),
                '材质': ac.get('material', ''),
                '分配数量': ac.get('allocated_quantity', 0),
                '补货数量': ac.get('replenish_quantity', 0),
                '单位成本': ac.get('price', 0),
                '分配成本': round(
                    ac.get('allocated_quantity', 0) * ac.get('price', 0), 2
                ),
                '补货成本': round(
                    ac.get('replenish_quantity', 0) * ac.get('price', 0), 2
                )
            })

    if len(replenishment) > 0:
        for _, row in replenishment.iterrows():
            rows.append({
                '报告类型': '补货建议',
                '项目ID': row.get('project_id', ''),
                '项目类型': row.get('project_type', ''),
                '优先级': row.get('priority', ''),
                '可完成度': '',
                '颜色名称': row.get('color_name', ''),
                '色系': row.get('color_family', ''),
                '材质': row.get('material', ''),
                '分配数量': '',
                '补货数量': row.get('shortage', ''),
                '单位成本': row.get('unit_price', ''),
                '分配成本': '',
                '补货成本': row.get('estimated_cost', '')
            })

    summary = analysis_result.get('summary', {})
    strategy_summary = allocation_result.get('summary', {})
    rows.append({
        '报告类型': '摘要',
        '项目ID': '合计',
        '项目类型': f"共{summary.get('project_count', 0)}个项目",
        '优先级': '',
        '可完成度': summary.get('priority_weighted_feasibility', ''),
        '颜色名称': '',
        '色系': '',
        '材质': '',
        '分配数量': summary.get('total_shortage_quantity', ''),
        '补货数量': strategy_summary.get('total_replenish_qty', ''),
        '单位成本': '',
        '分配成本': strategy_summary.get('total_allocation_cost', ''),
        '补货成本': strategy_summary.get('total_replenish_cost', '')
    })

    df = pd.DataFrame(rows)

    if output_path:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        return output_path
    else:
        return df.to_csv(index=False, encoding='utf-8-sig')
