import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from multi_project_analyzer import (
    ProjectRequirement,
    PRIORITY_WEIGHTS,
    calculate_color_reuse_efficiency
)
from color_theory import calculate_color_distance
from data_processor import analyze_long_unused


STRATEGY_NAMES = {
    'inventory_first': '优先消耗库存',
    'min_cost': '最少补货成本',
    'color_harmony': '综合色彩协调度最高'
}


def _compute_color_harmony_score(
    selected_colors: List[Dict[str, Any]],
    primary_hex: Optional[str] = None
) -> float:
    if len(selected_colors) < 2:
        return 100.0

    hex_colors = []
    for c in selected_colors:
        h = c.get('color_hex')
        if h:
            hex_colors.append(h)

    if not hex_colors:
        return 50.0

    if primary_hex and primary_hex not in hex_colors:
        hex_colors.insert(0, primary_hex)

    if len(hex_colors) < 2:
        return 70.0

    distances = []
    for i, h1 in enumerate(hex_colors):
        for h2 in hex_colors[i + 1:]:
            d = calculate_color_distance(h1, h2)
            distances.append(d)

    if not distances:
        return 50.0

    avg_dist = np.mean(distances)
    if avg_dist < 5:
        harmony = 40.0
    elif avg_dist < 15:
        harmony = 70.0 + (avg_dist - 5) * 3
    elif avg_dist < 40:
        harmony = 100.0
    elif avg_dist < 70:
        harmony = 100.0 - (avg_dist - 40) * 1.5
    else:
        harmony = 55.0 - (avg_dist - 70) * 0.5

    return max(0.0, min(100.0, harmony))


def _compute_long_unused_score(
    selected_colors: List[Dict[str, Any]],
    inventory_df: pd.DataFrame,
    days_threshold: int = 180
) -> float:
    today = datetime.now()
    cutoff = today - timedelta(days=days_threshold)

    total_score = 0.0
    max_possible = 0.0

    for c in selected_colors:
        color_name = c.get('color_name')
        allocated = c.get('allocated_quantity', 0)
        if allocated <= 0:
            continue

        matching = inventory_df[inventory_df['color_name'] == color_name]
        if len(matching) == 0:
            continue

        last_used = matching.iloc[0].get('last_used_date')
        qty = matching.iloc[0].get('quantity', 0)

        max_possible += qty

        if pd.isna(last_used):
            days_unused = 999
        else:
            days_unused = (today - last_used).days

        if days_unused >= days_threshold:
            bonus = min(1.0, days_unused / (days_threshold * 2))
            total_score += min(allocated, qty) * bonus
        elif days_unused >= days_threshold * 0.5:
            bonus = 0.3 * (days_unused / days_threshold)
            total_score += min(allocated, qty) * bonus

    return (total_score / max_possible * 100) if max_possible > 0 else 0.0


def allocate_colors_to_project(
    project: ProjectRequirement,
    feasibility: Dict[str, Any],
    inventory_df: pd.DataFrame,
    strategy: str,
    remaining_inventory: Dict[str, float],
    days_threshold: int = 180
) -> Dict[str, Any]:
    candidates = feasibility.get('candidate_colors', pd.DataFrame())
    req_detail = feasibility.get('requirement_detail', {})
    per_color_qtys = req_detail.get('per_color_quantities', [])
    color_count = req_detail.get('color_count', 3)

    if len(candidates) == 0:
        return {
            'project_id': project.project_id,
            'allocated_colors': [],
            'unmet_requirements': per_color_qtys,
            'allocation_score': 0.0
        }

    scored = candidates.copy()

    scored['match_score'] = scored.get('color_match_score', 50.0)

    today = datetime.now()
    cutoff = today - timedelta(days=days_threshold)

    def _unused_bonus(row):
        lud = row.get('last_used_date')
        if pd.isna(lud):
            return 100.0
        days = (today - lud).days
        if days >= days_threshold:
            return min(100.0, 50.0 + days / (days_threshold * 2) * 50)
        elif days >= days_threshold * 0.5:
            return 30.0 * (days / days_threshold)
        return 0.0

    scored['unused_bonus'] = scored.apply(_unused_bonus, axis=1)

    scored['remaining_qty'] = scored['color_name'].apply(
        lambda n: remaining_inventory.get(n, 0)
    )

    scored['cost_efficiency'] = 100.0 - (
        (scored['price'] - scored['price'].min()) /
        max(0.01, scored['price'].max() - scored['price'].min()) * 100
    ) if len(scored) > 1 else 50.0

    priority_w = PRIORITY_WEIGHTS.get(project.delivery_priority, 0.5)

    if strategy == 'inventory_first':
        w_unused = 0.45
        w_remaining = 0.35
        w_match = 0.15
        w_cost = 0.05
    elif strategy == 'min_cost':
        w_cost = 0.45
        w_match = 0.20
        w_remaining = 0.20
        w_unused = 0.15
    else:
        w_match = 0.45
        w_unused = 0.20
        w_remaining = 0.20
        w_cost = 0.15

    scored['final_score'] = (
        scored['unused_bonus'] * w_unused +
        (scored['remaining_qty'] / max(1, scored['remaining_qty'].max()) * 100) * w_remaining +
        scored['match_score'] * w_match +
        scored['cost_efficiency'] * w_cost
    ) * (0.5 + priority_w * 0.5)

    scored = scored.sort_values('final_score', ascending=False)

    allocated_colors = []
    total_allocated_cost = 0.0
    total_replenish_cost = 0.0
    total_replenish_qty = 0.0

    selected_so_far = []

    for idx, needed in enumerate(per_color_qtys[:color_count]):
        if idx < len(scored):
            row = scored.iloc[idx]
            color_name = row['color_name']
            avail = remaining_inventory.get(color_name, 0)

            harmony_bonus = 0.0
            if strategy == 'color_harmony' and selected_so_far:
                temp_selected = selected_so_far + [{
                    'color_name': color_name,
                    'color_hex': row.get('color_hex')
                }]
                harmony_bonus = _compute_color_harmony_score(
                    temp_selected, project.primary_color_hex
                ) / 100 * 20

            final_score_adj = row['final_score'] + harmony_bonus

            allocated = min(avail, needed)
            replenish = max(0, needed - allocated)

            remaining_inventory[color_name] = max(0, avail - allocated)

            alloc_info = {
                'color_name': color_name,
                'color_hex': row.get('color_hex', ''),
                'color_family': row.get('color_family', ''),
                'material': row.get('material', ''),
                'thickness': row.get('thickness', ''),
                'price': row.get('price', 0),
                'allocated_quantity': round(allocated, 1),
                'replenish_quantity': round(replenish, 1),
                'total_needed': round(needed, 1),
                'allocation_score': round(final_score_adj, 1),
                'unused_bonus': round(row['unused_bonus'], 1),
                'color_match_score': round(row.get('color_match_score', 50), 1)
            }

            selected_so_far.append({
                'color_name': color_name,
                'color_hex': row.get('color_hex')
            })

            allocated_colors.append(alloc_info)
            total_allocated_cost += allocated * row.get('price', 0)
            total_replenish_cost += replenish * row.get('price', 0)
            total_replenish_qty += replenish

    harmony_score = _compute_color_harmony_score(
        [{'color_hex': a['color_hex']} for a in allocated_colors if a['color_hex']],
        project.primary_color_hex
    )
    unused_score = _compute_long_unused_score(
        allocated_colors, inventory_df, days_threshold
    )

    return {
        'project_id': project.project_id,
        'project_type': project.project_type,
        'priority': project.delivery_priority,
        'allocated_colors': allocated_colors,
        'harmony_score': round(harmony_score, 1),
        'long_unused_consumption_score': round(unused_score, 1),
        'total_allocated_cost': round(total_allocated_cost, 2),
        'total_replenish_cost': round(total_replenish_cost, 2),
        'total_replenish_quantity': round(total_replenish_qty, 1)
    }


def compute_optimal_allocation(
    projects: List[ProjectRequirement],
    analysis_result: Dict[str, Any],
    inventory_df: pd.DataFrame,
    strategy: str = 'balanced',
    days_threshold: int = 180
) -> Dict[str, Any]:
    feasibilities = analysis_result.get('feasibilities', {})

    sorted_projects = sorted(
        projects,
        key=lambda p: (
            -PRIORITY_WEIGHTS.get(p.delivery_priority, 0.5),
            -feasibilities.get(p.project_id, {}).get('feasibility_score', 0)
        )
    )

    remaining_inventory = {}
    for _, row in inventory_df.iterrows():
        remaining_inventory[row['color_name']] = row.get('quantity', 0)

    allocations = {}
    all_replenish_rows = []
    total_alloc_cost = 0.0
    total_replenish_cost = 0.0
    total_replenish_qty = 0.0

    for project in sorted_projects:
        pid = project.project_id
        feasibility = feasibilities.get(pid, {})

        alloc = allocate_colors_to_project(
            project, feasibility, inventory_df, strategy,
            remaining_inventory, days_threshold
        )
        allocations[pid] = alloc

        total_alloc_cost += alloc['total_allocated_cost']
        total_replenish_cost += alloc['total_replenish_cost']
        total_replenish_qty += alloc['total_replenish_quantity']

        for ac in alloc['allocated_colors']:
            if ac['replenish_quantity'] > 0:
                all_replenish_rows.append({
                    'project_id': pid,
                    'project_type': project.project_type,
                    'priority': project.delivery_priority,
                    'priority_weight': PRIORITY_WEIGHTS.get(project.delivery_priority, 0.5),
                    'color_name': ac['color_name'],
                    'color_family': ac['color_family'],
                    'color_hex': ac['color_hex'],
                    'material': ac['material'],
                    'thickness': ac['thickness'],
                    'shortage': ac['replenish_quantity'],
                    'unit_price': ac['price'],
                    'color_match_score': ac['color_match_score'],
                    'estimated_cost': round(ac['replenish_quantity'] * ac['price'], 2)
                })

    replenishment_df = pd.DataFrame(all_replenish_rows) if all_replenish_rows else pd.DataFrame()

    if len(replenishment_df) > 0:
        replenishment_df = _apply_comprehensive_scoring(
            replenishment_df, strategy, inventory_df, days_threshold
        )

    inventory_before = inventory_df.set_index('color_name')['quantity'].to_dict()
    inventory_after = {k: remaining_inventory.get(k, 0) for k in inventory_before}

    avg_harmony = np.mean([
        a.get('harmony_score', 0) for a in allocations.values()
    ]) if allocations else 0.0
    avg_unused = np.mean([
        a.get('long_unused_consumption_score', 0) for a in allocations.values()
    ]) if allocations else 0.0

    reuse_info = calculate_color_reuse_efficiency(projects, feasibilities)

    summary = {
        'strategy': STRATEGY_NAMES.get(strategy, strategy),
        'strategy_code': strategy,
        'total_projects': len(projects),
        'total_allocation_cost': round(total_alloc_cost, 2),
        'total_replenish_cost': round(total_replenish_cost, 2),
        'total_replenish_qty': round(total_replenish_qty, 1),
        'average_harmony_score': round(avg_harmony, 1),
        'average_long_unused_score': round(avg_unused, 1),
        'color_reuse_score': reuse_info.get('reuse_score', 0),
        'inventory_before': inventory_before,
        'inventory_after': inventory_after
    }

    return {
        'allocations': allocations,
        'replenishment': replenishment_df,
        'remaining_inventory': remaining_inventory,
        'summary': summary,
        'reuse_info': reuse_info
    }


def _apply_comprehensive_scoring(
    replenishment_df: pd.DataFrame,
    strategy: str,
    inventory_df: pd.DataFrame,
    days_threshold: int
) -> pd.DataFrame:
    df = replenishment_df.copy()

    today = datetime.now()
    cutoff = today - timedelta(days=days_threshold)

    color_info = inventory_df.set_index('color_name')

    def _get_unused_days(color_name):
        if color_name not in color_info.index:
            return 999
        lud = color_info.loc[color_name, 'last_used_date']
        if pd.isna(lud):
            return 999
        return (today - lud).days

    df['unused_days'] = df['color_name'].apply(_get_unused_days)

    df['redundancy_bonus'] = df['unused_days'].apply(
        lambda d: min(100.0, d / (days_threshold * 2) * 100) if d >= days_threshold * 0.5 else 0.0
    )

    max_shortage = df['shortage'].max() if len(df) > 0 else 1
    df['urgency_score'] = (df['shortage'] / max(1, max_shortage) * 100).clip(0, 100)

    df['composite_score'] = (
        df['priority_weight'] * 100 * 0.35 +
        df['color_match_score'] * 0.25 +
        df['urgency_score'] * 0.25 +
        df['redundancy_bonus'] * 0.15
    )

    if strategy == 'inventory_first':
        df['composite_score'] = (
            df['redundancy_bonus'] * 0.40 +
            df['priority_weight'] * 100 * 0.30 +
            df['urgency_score'] * 0.20 +
            df['color_match_score'] * 0.10
        )
    elif strategy == 'min_cost':
        max_price = df['unit_price'].max() if len(df) > 0 else 1
        df['cost_score'] = 100 - (df['unit_price'] / max(1, max_price) * 100)
        df['composite_score'] = (
            df['cost_score'] * 0.40 +
            df['priority_weight'] * 100 * 0.30 +
            df['urgency_score'] * 0.20 +
            df['color_match_score'] * 0.10
        )
    elif strategy == 'color_harmony':
        df['composite_score'] = (
            df['color_match_score'] * 0.40 +
            df['priority_weight'] * 100 * 0.30 +
            df['urgency_score'] * 0.20 +
            df['redundancy_bonus'] * 0.10
        )

    df = df.sort_values('composite_score', ascending=False).reset_index(drop=True)

    return df


def compare_strategies(
    projects: List[ProjectRequirement],
    analysis_result: Dict[str, Any],
    inventory_df: pd.DataFrame,
    days_threshold: int = 180
) -> Dict[str, Any]:
    strategies = ['inventory_first', 'min_cost', 'color_harmony']
    results = {}

    for s in strategies:
        results[s] = compute_optimal_allocation(
            projects, analysis_result, inventory_df, s, days_threshold
        )

    comparison = []
    for s in strategies:
        summary = results[s].get('summary', {})
        comparison.append({
            'strategy_code': s,
            'strategy_name': STRATEGY_NAMES.get(s, s),
            'total_replenish_cost': summary.get('total_replenish_cost', 0),
            'total_replenish_qty': summary.get('total_replenish_qty', 0),
            'average_harmony_score': summary.get('average_harmony_score', 0),
            'average_long_unused_score': summary.get('average_long_unused_score', 0),
            'color_reuse_score': summary.get('color_reuse_score', 0)
        })

    return {
        'strategy_results': results,
        'comparison': pd.DataFrame(comparison)
    }
