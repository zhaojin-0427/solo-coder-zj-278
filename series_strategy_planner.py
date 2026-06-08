import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from copy import deepcopy

from multi_project_analyzer import (
    ProjectRequirement,
    PROJECT_YARN_REQUIREMENTS,
    PROJECT_SIZE_OPTIONS,
    PRIORITY_WEIGHTS,
    estimate_yarn_requirement,
    find_candidate_colors,
    calculate_project_feasibility
)
from multi_project_strategy import (
    _compute_color_harmony_score,
    _compute_long_unused_score,
    STRATEGY_NAMES
)
from color_theory import (
    calculate_color_distance,
    get_complementary,
    get_analogous,
    get_triadic,
    get_split_complementary,
    get_monochromatic
)
from data_processor import classify_color, analyze_long_unused
from historical_data_analyzer import (
    SEASON_THEMES,
    STYLE_PROFILES,
    analyze_color_material_track_record,
    calculate_series_history_similarity
)


SERIES_STRATEGY_NAMES = {
    'safest_delivery': '最稳妥交付',
    'min_replenish_cost': '最低补货成本',
    'visual_unity': '视觉统一性最高'
}


class SeriesProject:
    def __init__(
        self,
        series_project_id: str,
        project_type: str,
        target_size: str,
        delivery_order: int = 1,
        color_count: int = 3,
        material_restrictions: Optional[List[str]] = None,
        primary_color_preference: Optional[str] = None,
        primary_color_hex: Optional[str] = None,
        role_in_series: str = '核心'
    ):
        self.series_project_id = series_project_id
        self.project_type = project_type
        self.target_size = target_size
        self.delivery_order = delivery_order
        self.color_count = color_count
        self.material_restrictions = material_restrictions or []
        self.primary_color_preference = primary_color_preference
        self.primary_color_hex = primary_color_hex
        self.role_in_series = role_in_series

    def to_dict(self) -> Dict[str, Any]:
        return {
            'series_project_id': self.series_project_id,
            'project_type': self.project_type,
            'target_size': self.target_size,
            'delivery_order': self.delivery_order,
            'color_count': self.color_count,
            'material_restrictions': self.material_restrictions,
            'primary_color_preference': self.primary_color_preference,
            'primary_color_hex': self.primary_color_hex,
            'role_in_series': self.role_in_series
        }


class SeriesConfig:
    def __init__(
        self,
        series_name: str,
        target_style: str,
        season_theme: str,
        budget_min: float,
        budget_max: float,
        material_taboos: Optional[List[str]] = None,
        reuse_rate_target: float = 0.6,
        series_projects: Optional[List[SeriesProject]] = None
    ):
        self.series_name = series_name
        self.target_style = target_style
        self.season_theme = season_theme
        self.budget_min = budget_min
        self.budget_max = budget_max
        self.material_taboos = material_taboos or []
        self.reuse_rate_target = reuse_rate_target
        self.series_projects = series_projects or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'series_name': self.series_name,
            'target_style': self.target_style,
            'season_theme': self.season_theme,
            'budget_min': self.budget_min,
            'budget_max': self.budget_max,
            'material_taboos': self.material_taboos,
            'reuse_rate_target': self.reuse_rate_target,
            'series_projects': [p.to_dict() for p in self.series_projects]
        }


def generate_series_base_palette(
    series_config: SeriesConfig,
    inventory_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    style = series_config.target_style
    season = series_config.season_theme
    style_profile = STYLE_PROFILES.get(style, STYLE_PROFILES['简约北欧'])
    season_theme = SEASON_THEMES.get(season, SEASON_THEMES['春季'])

    min_colors, max_colors = style_profile['color_count_range']
    target_count = min(max_colors, max(min_colors, 5))

    preferred_families = style_profile['preferred_families']
    season_families = season_theme['dominant_families']
    combined_families = list(dict.fromkeys(preferred_families + season_families))

    candidates = inventory_df.copy()

    if series_config.material_taboos:
        taboo_pattern = '|'.join(series_config.material_taboos)
        candidates = candidates[
            ~candidates['material'].str.contains(taboo_pattern, case=False, na=False)
        ]

    family_candidates = candidates[
        candidates['color_family'].isin(combined_families)
    ].copy()

    if len(family_candidates) == 0:
        family_candidates = candidates.copy()

    family_candidates['style_match'] = family_candidates['color_family'].apply(
        lambda f: 1.0 if f in preferred_families else (0.6 if f in season_families else 0.2)
    )
    family_candidates['inventory_bonus'] = family_candidates['quantity'].apply(
        lambda q: min(1.0, q / 10.0)
    )

    today = datetime.now()
    family_candidates['days_unused'] = family_candidates['last_used_date'].apply(
        lambda x: (today - x).days if pd.notna(x) else 999
    )
    family_candidates['unused_bonus'] = family_candidates['days_unused'].apply(
        lambda d: min(1.0, d / 365.0) if d >= 180 else 0.0
    )

    family_candidates['composite_score'] = (
        family_candidates['style_match'] * 0.4 +
        family_candidates['inventory_bonus'] * 0.35 +
        family_candidates['unused_bonus'] * 0.25
    )

    family_candidates = family_candidates.sort_values('composite_score', ascending=False)

    selected = []
    used_families = set()
    used_hexes = set()

    for _, row in family_candidates.iterrows():
        if len(selected) >= target_count:
            break

        hex_val = row.get('color_hex', '')
        family = row.get('color_family', '')

        if not hex_val or hex_val in used_hexes:
            continue

        if family in used_families and len(selected) >= min_colors:
            continue

        if selected:
            min_dist = min(
                calculate_color_distance(hex_val, s['color_hex'])
                for s in selected if s.get('color_hex')
            )
            if min_dist < 8:
                continue

        selected.append({
            'color_name': row['color_name'],
            'color_hex': hex_val,
            'color_family': family,
            'material': row.get('material', ''),
            'quantity': row.get('quantity', 0),
            'price': row.get('price', 0),
            'thickness': row.get('thickness', ''),
            'composite_score': round(row['composite_score'], 3),
            'style_match': round(row['style_match'], 2),
            'role': '核心色' if len(selected) == 0 else ('主色' if len(selected) <= 2 else '点缀色')
        })
        used_families.add(family)
        used_hexes.add(hex_val)

    harmony = _compute_color_harmony_score(
        [{'color_hex': s['color_hex']} for s in selected if s.get('color_hex')]
    )
    for s in selected:
        s['harmony_contribution'] = round(harmony / max(1, len(selected)), 1)

    return selected


def generate_alternative_palettes(
    base_palette: List[Dict[str, Any]],
    inventory_df: pd.DataFrame,
    series_config: SeriesConfig,
    num_alternatives: int = 3
) -> List[Dict[str, Any]]:
    if not base_palette:
        return []

    alternatives = []
    base_hexes = [c['color_hex'] for c in base_palette if c.get('color_hex')]

    for alt_idx in range(num_alternatives):
        alt_palette = []
        used_hexes = set(base_hexes)

        for i, base_color in enumerate(base_palette):
            base_hex = base_color.get('color_hex', '')
            if not base_hex:
                continue

            if alt_idx == 0:
                new_hex = get_complementary(base_hex)
            elif alt_idx == 1:
                analogs = get_analogous(base_hex, num_colors=3, angle_spread=20)
                new_hex = analogs[-1] if len(analogs) > 1 else base_hex
            else:
                triads = get_triadic(base_hex)
                new_hex = triads[-1] if len(triads) > 1 else base_hex

            if not new_hex or new_hex in used_hexes:
                alt_palette.append(base_color)
                continue

            valid_inventory = inventory_df[
                (inventory_df['color_hex'].notna()) &
                (~inventory_df['color_hex'].isin(list(used_hexes)))
            ].copy()

            if len(valid_inventory) == 0:
                alt_palette.append(base_color)
                continue

            valid_inventory['distance'] = valid_inventory['color_hex'].apply(
                lambda h: calculate_color_distance(new_hex, h)
            )
            closest = valid_inventory.sort_values('distance').head(1)

            if len(closest) > 0 and closest.iloc[0]['distance'] < 40:
                row = closest.iloc[0]
                alt_palette.append({
                    'color_name': row['color_name'],
                    'color_hex': row['color_hex'],
                    'color_family': row.get('color_family', ''),
                    'material': row.get('material', ''),
                    'quantity': row.get('quantity', 0),
                    'price': row.get('price', 0),
                    'thickness': row.get('thickness', ''),
                    'role': base_color.get('role', '点缀色'),
                    'variation_type': {0: '互补色替代', 1: '邻近色变体', 2: '三角色变体'}.get(alt_idx, '变体')
                })
                used_hexes.add(row['color_hex'])
            else:
                alt_palette.append(base_color)

        alt_harmony = _compute_color_harmony_score(
            [{'color_hex': c['color_hex']} for c in alt_palette if c.get('color_hex')]
        )
        alternatives.append({
            'palette_id': f'alt_{alt_idx + 1}',
            'name': {0: '互补色方案', 1: '邻近色方案', 2: '三角色方案'}.get(alt_idx, f'备选方案{alt_idx + 1}'),
            'colors': alt_palette,
            'harmony_score': round(alt_harmony, 1),
            'difference_from_base': round(
                sum(1 for a, b in zip(alt_palette, base_palette) if a.get('color_hex') != b.get('color_hex'))
                / max(1, len(base_palette)) * 100, 1
            )
        })

    return alternatives


def generate_shared_yarn_scheme(
    series_config: SeriesConfig,
    base_palette: List[Dict[str, Any]],
    inventory_df: pd.DataFrame
) -> Dict[str, Any]:
    if not base_palette or not series_config.series_projects:
        return {'shared_colors': [], 'per_project_allocation': {}}

    shared_colors = []
    total_qty_per_color = {}

    for color in base_palette:
        cname = color['color_name']
        inv_qty = color.get('quantity', 0)
        role = color.get('role', '点缀色')

        if role == '核心色':
            share_pct = 0.9
        elif role == '主色':
            share_pct = 0.7
        else:
            share_pct = 0.4

        shared_qty = round(inv_qty * share_pct, 1)
        if shared_qty > 0:
            shared_colors.append({
                **color,
                'shared_quantity': shared_qty,
                'reserved_for_series': True
            })
            total_qty_per_color[cname] = shared_qty

    per_project = {}
    n_projects = len(series_config.series_projects)

    sorted_projects = sorted(
        series_config.series_projects,
        key=lambda p: p.delivery_order
    )

    for i, proj in enumerate(sorted_projects):
        pid = proj.series_project_id
        color_count = proj.color_count
        requirement = estimate_yarn_requirement(ProjectRequirement(
            project_id=pid,
            project_type=proj.project_type,
            target_size=proj.target_size,
            color_count=color_count
        ))
        per_color_qtys = requirement.get('per_color_quantities', [])

        project_alloc = []
        for j, sc in enumerate(shared_colors):
            if j >= color_count:
                break
            needed = per_color_qtys[j] if j < len(per_color_qtys) else per_color_qtys[-1]
            available = total_qty_per_color.get(sc['color_name'], 0)
            alloc = min(needed * 0.7, available / max(1, n_projects - i))
            alloc = round(alloc, 1)

            if alloc > 0:
                total_qty_per_color[sc['color_name']] -= alloc
                project_alloc.append({
                    'color_name': sc['color_name'],
                    'color_hex': sc.get('color_hex', ''),
                    'color_family': sc.get('color_family', ''),
                    'material': sc.get('material', ''),
                    'allocated_from_shared': alloc,
                    'still_needed': round(max(0, needed - alloc), 1),
                    'role': sc.get('role', '')
                })

        per_project[pid] = project_alloc

    reuse_rate = 0
    if shared_colors:
        total_shared = sum(sc['shared_quantity'] for sc in shared_colors)
        total_allocated = sum(
            pa['allocated_from_shared']
            for alloc_list in per_project.values()
            for pa in alloc_list
        )
        reuse_rate = round(total_allocated / max(0.01, total_shared) * 100, 1)

    return {
        'shared_colors': shared_colors,
        'per_project_allocation': per_project,
        'cross_project_reuse_rate': reuse_rate,
        'reuse_target_met': reuse_rate >= series_config.reuse_rate_target * 100
    }


def _score_project_allocation(
    project: SeriesProject,
    selected_colors: List[Dict[str, Any]],
    strategy: str,
    series_config: SeriesConfig,
    inventory_df: pd.DataFrame,
    days_threshold: int = 180
) -> float:
    if not selected_colors:
        return 0.0

    scores = {}

    harmony = _compute_color_harmony_score(
        [{'color_hex': c.get('color_hex')} for c in selected_colors if c.get('color_hex')]
    )
    scores['harmony'] = harmony

    unused_score = _compute_long_unused_score(selected_colors, inventory_df, days_threshold)
    scores['unused_consumption'] = unused_score

    replenish_cost = sum(
        max(0, c.get('total_needed', 0) - c.get('available_qty', c.get('quantity', 0))) * c.get('price', 0)
        for c in selected_colors
    )
    total_cost = sum(c.get('total_needed', 0) * c.get('price', 0) for c in selected_colors)
    cost_efficiency = 100 - (replenish_cost / max(0.01, total_cost) * 100) if total_cost > 0 else 0
    scores['cost_efficiency'] = max(0, cost_efficiency)

    delivery_confidence = 100.0
    for c in selected_colors:
        needed = c.get('total_needed', 0)
        available = c.get('available_qty', c.get('quantity', 0))
        if available < needed * 0.8:
            delivery_confidence *= 0.7
    scores['delivery_confidence'] = delivery_confidence

    if strategy == 'safest_delivery':
        weights = {'delivery_confidence': 0.45, 'unused_consumption': 0.25, 'harmony': 0.20, 'cost_efficiency': 0.10}
    elif strategy == 'min_replenish_cost':
        weights = {'cost_efficiency': 0.45, 'unused_consumption': 0.25, 'delivery_confidence': 0.20, 'harmony': 0.10}
    else:
        weights = {'harmony': 0.45, 'delivery_confidence': 0.25, 'cost_efficiency': 0.15, 'unused_consumption': 0.15}

    final_score = sum(scores[k] * w for k, w in weights.items())
    return round(final_score, 1)


def plan_single_project(
    project: SeriesProject,
    base_palette: List[Dict[str, Any]],
    shared_scheme: Dict[str, Any],
    inventory_df: pd.DataFrame,
    strategy: str,
    series_config: SeriesConfig,
    days_threshold: int = 180,
    experience_library: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    pid = project.series_project_id
    color_count = project.color_count

    temp_proj = ProjectRequirement(
        project_id=pid,
        project_type=project.project_type,
        target_size=project.target_size,
        color_count=color_count,
        material_restrictions=project.material_restrictions,
        primary_color_preference=project.primary_color_preference,
        primary_color_hex=project.primary_color_hex,
        delivery_priority={1: '最高', 2: '高', 3: '中', 4: '低', 5: '最低'}.get(project.delivery_order, '中')
    )
    feasibility = calculate_project_feasibility(temp_proj, inventory_df)
    requirement = feasibility.get('requirement_detail', {})
    per_color_qtys = requirement.get('per_color_quantities', [])

    shared_alloc = shared_scheme.get('per_project_allocation', {}).get(pid, [])
    shared_color_names = {sa['color_name']: sa for sa in shared_alloc}

    candidates = []
    for bc in base_palette:
        cname = bc['color_name']
        shared_info = shared_color_names.get(cname, {})
        shared_qty = shared_info.get('allocated_from_shared', 0)
        available = bc.get('quantity', 0)

        history_record = {}
        if experience_library:
            history_record = analyze_color_material_track_record(
                cname, bc.get('material', ''), experience_library
            )

        candidates.append({
            **bc,
            'available_qty': available,
            'shared_allocated': shared_qty,
            'total_available_for_project': available + shared_qty,
            'history_confidence': history_record.get('confidence', 'low'),
            'history_rating': history_record.get('avg_rating', 0)
        })

    if project.material_restrictions:
        mat_pattern = '|'.join(project.material_restrictions)
        candidates = [
            c for c in candidates
            if mat_pattern.lower() in str(c.get('material', '')).lower() or not c.get('material')
        ]

    for i, c in enumerate(candidates):
        needed = per_color_qtys[min(i, len(per_color_qtys) - 1)] if per_color_qtys else 2
        c['total_needed'] = needed
        c['replenish_qty'] = max(0, needed - c.get('total_available_for_project', 0))
        c['replenish_cost'] = round(c['replenish_qty'] * c.get('price', 0), 2)

    candidates = sorted(
        candidates,
        key=lambda c: (
            -c.get('composite_score', 0),
            -c.get('quantity', 0)
        )
    )[:color_count]

    final_score = _score_project_allocation(
        project, candidates, strategy, series_config, inventory_df, days_threshold
    )

    harmony_score = _compute_color_harmony_score(
        [{'color_hex': c.get('color_hex')} for c in candidates if c.get('color_hex')],
        project.primary_color_hex
    )

    total_replenish = sum(c.get('replenish_qty', 0) for c in candidates)
    total_replenish_cost = sum(c.get('replenish_cost', 0) for c in candidates)
    total_allocated_cost = sum(
        min(c.get('total_available_for_project', 0), c.get('total_needed', 0)) * c.get('price', 0)
        for c in candidates
    )

    return {
        'series_project_id': pid,
        'project_type': project.project_type,
        'target_size': project.target_size,
        'delivery_order': project.delivery_order,
        'role_in_series': project.role_in_series,
        'selected_colors': candidates,
        'per_color_requirements': per_color_qtys,
        'feasibility_score': feasibility.get('feasibility_score', 0),
        'allocation_score': final_score,
        'harmony_score': round(harmony_score, 1),
        'total_replenish_qty': round(total_replenish, 1),
        'total_replenish_cost': round(total_replenish_cost, 2),
        'total_allocated_cost': round(total_allocated_cost, 2),
        'from_shared_pool': sum(sa.get('allocated_from_shared', 0) for sa in shared_alloc)
    }


def plan_series_projects(
    series_config: SeriesConfig,
    base_palette: List[Dict[str, Any]],
    shared_scheme: Dict[str, Any],
    inventory_df: pd.DataFrame,
    strategy: str,
    days_threshold: int = 180,
    experience_library: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    results = {}
    sorted_projects = sorted(
        series_config.series_projects,
        key=lambda p: p.delivery_order
    )

    for project in sorted_projects:
        result = plan_single_project(
            project, base_palette, shared_scheme,
            inventory_df, strategy, series_config,
            days_threshold, experience_library
        )
        results[project.series_project_id] = result

    return results


def calculate_inventory_changes(
    series_plans: Dict[str, Dict[str, Any]],
    inventory_df: pd.DataFrame
) -> Dict[str, Any]:
    before = inventory_df.set_index('color_name')['quantity'].to_dict()
    after = dict(before)

    for pid, plan in series_plans.items():
        for color in plan.get('selected_colors', []):
            cname = color['color_name']
            used = min(color.get('total_available_for_project', 0), color.get('total_needed', 0))
            after[cname] = max(0, after.get(cname, 0) - used)

    changes = []
    total_used_value = 0
    total_remaining_value = 0

    for cname in before:
        qty_before = before[cname]
        qty_after = after.get(cname, 0)
        qty_used = qty_before - qty_after
        price_row = inventory_df[inventory_df['color_name'] == cname]
        price = price_row['price'].iloc[0] if len(price_row) > 0 else 0

        changes.append({
            'color_name': cname,
            'quantity_before': qty_before,
            'quantity_after': round(qty_after, 1),
            'quantity_used': round(qty_used, 1),
            'value_used': round(qty_used * price, 2),
            'value_remaining': round(qty_after * price, 2)
        })
        total_used_value += qty_used * price
        total_remaining_value += qty_after * price

    return {
        'before': before,
        'after': after,
        'changes': changes,
        'total_used_value': round(total_used_value, 2),
        'total_remaining_value': round(total_remaining_value, 2),
        'consumption_ratio': round(
            total_used_value / max(0.01, total_used_value + total_remaining_value) * 100, 1
        )
    }


def calculate_replenishment_priority(
    series_plans: Dict[str, Dict[str, Any]],
    strategy: str,
    inventory_df: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    for pid, plan in series_plans.items():
        for color in plan.get('selected_colors', []):
            rep_qty = color.get('replenish_qty', 0)
            if rep_qty > 0:
                price = color.get('price', 0)
                delivery_weight = {
                    1: 1.0, 2: 0.85, 3: 0.65, 4: 0.45, 5: 0.25
                }.get(plan.get('delivery_order', 3), 0.5)

                if strategy == 'safest_delivery':
                    priority_score = delivery_weight * 100 * 0.5 + color.get('composite_score', 0) * 50
                elif strategy == 'min_replenish_cost':
                    priority_score = (1 - price / max(0.01, 100)) * 50 + delivery_weight * 50
                else:
                    priority_score = color.get('composite_score', 0) * 50 + delivery_weight * 50

                rows.append({
                    'series_project_id': pid,
                    'project_type': plan.get('project_type', ''),
                    'delivery_order': plan.get('delivery_order', 3),
                    'color_name': color['color_name'],
                    'color_hex': color.get('color_hex', ''),
                    'color_family': color.get('color_family', ''),
                    'material': color.get('material', ''),
                    'replenish_qty': round(rep_qty, 1),
                    'unit_price': price,
                    'estimated_cost': round(rep_qty * price, 2),
                    'composite_score': round(priority_score, 1)
                })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values('composite_score', ascending=False).reset_index(drop=True)
    df['priority_rank'] = df.index + 1
    return df


def calculate_long_unused_contribution(
    series_plans: Dict[str, Dict[str, Any]],
    inventory_df: pd.DataFrame,
    days_threshold: int = 180
) -> Dict[str, Any]:
    long_unused = analyze_long_unused(inventory_df, days_threshold=days_threshold)
    if len(long_unused) == 0:
        return {
            'total_long_unused_colors': 0,
            'consumed_long_unused_colors': 0,
            'consumed_quantity': 0,
            'value_freed': 0,
            'contribution_ratio': 0
        }

    total_colors = len(long_unused)
    total_qty = long_unused['quantity'].sum()
    total_value = (long_unused['quantity'] * long_unused['price']).sum()

    consumed_names = set()
    consumed_qty = 0
    consumed_value = 0

    for pid, plan in series_plans.items():
        for color in plan.get('selected_colors', []):
            cname = color['color_name']
            lu_match = long_unused[long_unused['color_name'] == cname]
            if len(lu_match) > 0:
                lu_qty = lu_match['quantity'].iloc[0]
                lu_price = lu_match['price'].iloc[0]
                used = min(color.get('total_available_for_project', 0), color.get('total_needed', 0), lu_qty)
                if used > 0:
                    consumed_names.add(cname)
                    consumed_qty += used
                    consumed_value += used * lu_price

    return {
        'total_long_unused_colors': total_colors,
        'total_long_unused_quantity': round(total_qty, 1),
        'total_long_unused_value': round(total_value, 2),
        'consumed_long_unused_colors': len(consumed_names),
        'consumed_quantity': round(consumed_qty, 1),
        'value_freed': round(consumed_value, 2),
        'contribution_ratio': round(consumed_value / max(0.01, total_value) * 100, 1)
    }


def compute_series_visual_unity(
    series_plans: Dict[str, Dict[str, Any]],
    base_palette: List[Dict[str, Any]]
) -> Dict[str, Any]:
    if not series_plans:
        return {'unity_score': 0, 'shared_color_ratio': 0, 'harmony_consistency': 0}

    all_color_sets = []
    harmony_scores = []
    for pid, plan in series_plans.items():
        colors = plan.get('selected_colors', [])
        hexes = [c.get('color_hex') for c in colors if c.get('color_hex')]
        all_color_sets.append(set(hexes))
        harmony_scores.append(plan.get('harmony_score', 0))

    if len(all_color_sets) < 2:
        return {
            'unity_score': harmony_scores[0] if harmony_scores else 0,
            'shared_color_ratio': 100,
            'harmony_consistency': 100
        }

    common_colors = set.intersection(*all_color_sets) if all_color_sets else set()
    all_unique = set.union(*all_color_sets) if all_color_sets else set()
    shared_ratio = len(common_colors) / max(1, len(all_unique)) * 100

    harmony_std = np.std(harmony_scores) if harmony_scores else 0
    harmony_consistency = max(0, 100 - harmony_std * 5)

    base_hexes = set(c.get('color_hex') for c in base_palette if c.get('color_hex'))
    base_adherence = sum(
        len(cs & base_hexes) / max(1, len(cs)) for cs in all_color_sets
    ) / len(all_color_sets) * 100

    unity_score = round(shared_ratio * 0.4 + harmony_consistency * 0.3 + base_adherence * 0.3, 1)

    return {
        'unity_score': unity_score,
        'shared_color_ratio': round(shared_ratio, 1),
        'harmony_consistency': round(harmony_consistency, 1),
        'base_palette_adherence': round(base_adherence, 1)
    }


def run_series_strategy(
    series_config: SeriesConfig,
    inventory_df: pd.DataFrame,
    strategy: str,
    days_threshold: int = 180,
    experience_library: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    base_palette = generate_series_base_palette(series_config, inventory_df)
    alternative_palettes = generate_alternative_palettes(base_palette, inventory_df, series_config)
    shared_scheme = generate_shared_yarn_scheme(series_config, base_palette, inventory_df)
    series_plans = plan_series_projects(
        series_config, base_palette, shared_scheme,
        inventory_df, strategy, days_threshold, experience_library
    )
    inventory_changes = calculate_inventory_changes(series_plans, inventory_df)
    replenishment = calculate_replenishment_priority(series_plans, strategy, inventory_df)
    long_unused_contribution = calculate_long_unused_contribution(
        series_plans, inventory_df, days_threshold
    )
    visual_unity = compute_series_visual_unity(series_plans, base_palette)

    history_similarity = calculate_series_history_similarity(
        base_palette, experience_library or {}, series_config.season_theme
    )

    total_replenish_cost = sum(p.get('total_replenish_cost', 0) for p in series_plans.values())
    total_allocated_cost = sum(p.get('total_allocated_cost', 0) for p in series_plans.values())
    total_budget = total_replenish_cost + total_allocated_cost
    budget_within_range = (
        series_config.budget_min <= total_budget <= series_config.budget_max
        if series_config.budget_max > 0 else True
    )

    summary = {
        'strategy': SERIES_STRATEGY_NAMES.get(strategy, strategy),
        'strategy_code': strategy,
        'series_name': series_config.series_name,
        'project_count': len(series_config.series_projects),
        'base_palette_size': len(base_palette),
        'total_replenish_cost': round(total_replenish_cost, 2),
        'total_allocated_cost': round(total_allocated_cost, 2),
        'total_budget': round(total_budget, 2),
        'budget_min': series_config.budget_min,
        'budget_max': series_config.budget_max,
        'budget_within_range': budget_within_range,
        'cross_project_reuse_rate': shared_scheme.get('cross_project_reuse_rate', 0),
        'reuse_target': series_config.reuse_rate_target * 100,
        'visual_unity_score': visual_unity.get('unity_score', 0),
        'history_similarity': history_similarity.get('best_similarity', 0),
        'season_match_score': history_similarity.get('season_match_score', 0),
        'long_unused_contribution': long_unused_contribution.get('contribution_ratio', 0)
    }

    return {
        'config': series_config.to_dict(),
        'base_palette': base_palette,
        'alternative_palettes': alternative_palettes,
        'shared_yarn_scheme': shared_scheme,
        'series_plans': series_plans,
        'inventory_changes': inventory_changes,
        'replenishment': replenishment,
        'long_unused_contribution': long_unused_contribution,
        'visual_unity': visual_unity,
        'history_similarity': history_similarity,
        'summary': summary
    }


def compare_series_strategies(
    series_config: SeriesConfig,
    inventory_df: pd.DataFrame,
    days_threshold: int = 180,
    experience_library: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    strategies = ['safest_delivery', 'min_replenish_cost', 'visual_unity']
    results = {}

    for s in strategies:
        results[s] = run_series_strategy(
            series_config, inventory_df, s, days_threshold, experience_library
        )

    comparison = []
    for s in strategies:
        summary = results[s].get('summary', {})
        comparison.append({
            'strategy_code': s,
            'strategy_name': SERIES_STRATEGY_NAMES.get(s, s),
            'total_replenish_cost': summary.get('total_replenish_cost', 0),
            'total_budget': summary.get('total_budget', 0),
            'visual_unity_score': summary.get('visual_unity_score', 0),
            'cross_project_reuse_rate': summary.get('cross_project_reuse_rate', 0),
            'history_similarity': summary.get('history_similarity', 0),
            'long_unused_contribution': summary.get('long_unused_contribution', 0),
            'budget_within_range': summary.get('budget_within_range', False)
        })

    return {
        'strategy_results': results,
        'comparison': pd.DataFrame(comparison)
    }


def export_series_report_csv(
    strategy_result: Dict[str, Any],
    experience_library: Optional[Dict[str, Any]] = None
) -> str:
    rows = []

    summary = strategy_result.get('summary', {})
    config = strategy_result.get('config', {})
    rows.append({
        '报告类型': '系列摘要',
        '系列名称': summary.get('series_name', ''),
        '项目类型': f"共{summary.get('project_count', 0)}个项目",
        '策略': summary.get('strategy', ''),
        '目标风格': config.get('target_style', ''),
        '季节主题': config.get('season_theme', ''),
        '颜色名称': '',
        '色系': '',
        '材质': '',
        '库存分配': '',
        '需补货': '',
        '单位成本': '',
        '分配成本': summary.get('total_allocated_cost', ''),
        '补货成本': summary.get('total_replenish_cost', ''),
        '备注': f"视觉统一性: {summary.get('visual_unity_score', '')} | 复用率: {summary.get('cross_project_reuse_rate', '')}%"
    })

    base_palette = strategy_result.get('base_palette', [])
    for color in base_palette:
        rows.append({
            '报告类型': '系列基础色板',
            '系列名称': summary.get('series_name', ''),
            '项目类型': '',
            '策略': '',
            '目标风格': '',
            '季节主题': '',
            '颜色名称': color.get('color_name', ''),
            '色系': color.get('color_family', ''),
            '材质': color.get('material', ''),
            '库存分配': color.get('quantity', ''),
            '需补货': '',
            '单位成本': color.get('price', ''),
            '分配成本': '',
            '补货成本': '',
            '备注': f"角色: {color.get('role', '')} | 综合分: {color.get('composite_score', '')}"
        })

    series_plans = strategy_result.get('series_plans', {})
    for pid, plan in series_plans.items():
        for color in plan.get('selected_colors', []):
            rows.append({
                '报告类型': '项目配方',
                '系列名称': summary.get('series_name', ''),
                '项目类型': f"{plan.get('project_type', '')} ({plan.get('target_size', '')})",
                '策略': summary.get('strategy', ''),
                '目标风格': '',
                '季节主题': '',
                '颜色名称': color.get('color_name', ''),
                '色系': color.get('color_family', ''),
                '材质': color.get('material', ''),
                '库存分配': round(min(color.get('total_available_for_project', 0), color.get('total_needed', 0)), 1),
                '需补货': color.get('replenish_qty', 0),
                '单位成本': color.get('price', 0),
                '分配成本': round(
                    min(color.get('total_available_for_project', 0), color.get('total_needed', 0)) * color.get('price', 0), 2
                ),
                '补货成本': color.get('replenish_cost', 0),
                '备注': f"交付顺序: {plan.get('delivery_order', '')} | 协调度: {plan.get('harmony_score', '')}"
            })

    replenishment = strategy_result.get('replenishment', pd.DataFrame())
    if len(replenishment) > 0:
        for _, row in replenishment.iterrows():
            rows.append({
                '报告类型': '补货建议',
                '系列名称': summary.get('series_name', ''),
                '项目类型': f"{row.get('project_type', '')}",
                '策略': summary.get('strategy', ''),
                '目标风格': '',
                '季节主题': '',
                '颜色名称': row.get('color_name', ''),
                '色系': row.get('color_family', ''),
                '材质': row.get('material', ''),
                '库存分配': '',
                '需补货': row.get('replenish_qty', ''),
                '单位成本': row.get('unit_price', ''),
                '分配成本': '',
                '补货成本': row.get('estimated_cost', ''),
                '备注': f"优先级分: {row.get('composite_score', '')} | 排名: {row.get('priority_rank', '')}"
            })

    inv_changes = strategy_result.get('inventory_changes', {})
    for change in inv_changes.get('changes', []):
        if change.get('quantity_used', 0) > 0:
            rows.append({
                '报告类型': '库存变化',
                '系列名称': summary.get('series_name', ''),
                '项目类型': '',
                '策略': '',
                '目标风格': '',
                '季节主题': '',
                '颜色名称': change.get('color_name', ''),
                '色系': '',
                '材质': '',
                '库存分配': change.get('quantity_before', ''),
                '需补货': change.get('quantity_after', ''),
                '单位成本': '',
                '分配成本': change.get('value_used', ''),
                '补货成本': '',
                '备注': f"消耗: {change.get('quantity_used', '')}"
            })

    history_sim = strategy_result.get('history_similarity', {})
    best_match = history_sim.get('best_match')
    if best_match:
        rows.append({
            '报告类型': '历史案例匹配',
            '系列名称': summary.get('series_name', ''),
            '项目类型': best_match.get('project_type', ''),
            '策略': '',
            '目标风格': '',
            '季节主题': '',
            '颜色名称': best_match.get('project_name', ''),
            '色系': '',
            '材质': ', '.join(best_match.get('materials', [])),
            '库存分配': '',
            '需补货': '',
            '单位成本': '',
            '分配成本': '',
            '补货成本': '',
            '备注': (
                f"相似度: {best_match.get('similarity', '')} | "
                f"历史评分: {best_match.get('avg_rating', '')} | "
                f"反馈: {best_match.get('feedback', '')}"
            )
        })

    df = pd.DataFrame(rows)
    return df.to_csv(index=False, encoding='utf-8-sig')
