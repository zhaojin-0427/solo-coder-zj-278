import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

from visualizations import (
    COLOR_FAMILY_HEX,
    get_family_color,
    plot_color_swatch,
    _get_text_color
)


def plot_project_feasibility_radar(
    feasibilities: Dict[str, Dict[str, Any]]
) -> go.Figure:
    if not feasibilities:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text='暂无项目数据', font=dict(size=16, family='Microsoft YaHei')),
            height=400
        )
        return fig

    categories = [
        '数量可完成度',
        '颜色丰富度',
        '预算充足度',
        '优先级评分',
        '综合可完成度'
    ]

    fig = go.Figure()

    fallback_colors = ['#3498DB', '#E74C3C', '#27AE60', '#F39C12', '#8E44AD',
                       '#1ABC9C', '#E67E22', '#9B59B6', '#34495E', '#16A085']
    try:
        colors = list(px.colors.qualitative.Set3)
    except Exception:
        colors = fallback_colors

    def _hex_to_rgba(hex_color, alpha=0.2):
        try:
            h = hex_color.lstrip('#')
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return f'rgba({r},{g},{b},{alpha})'
        except Exception:
            return f'rgba(52,152,219,{alpha})'

    for i, (pid, f) in enumerate(feasibilities.items()):
        qty_feas = float(f.get('quantity_feasibility', 0) or 0) * 100
        color_feas = float(f.get('color_feasibility', 0) or 0) * 100
        budget_feas = 100.0 if f.get('budget_ok', True) else 40.0
        priority_feas = float(f.get('priority_weight', 0.5) or 0.5) * 100
        overall = float(f.get('feasibility_score', 0) or 0)

        values = [qty_feas, color_feas, budget_feas, priority_feas, overall]
        values = [float(v) for v in values]
        values_closed = values + values[:1]

        cat_ext = categories + categories[:1]

        label = f"{pid} ({f.get('project_type', '')})"
        color = colors[i % len(colors)]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=cat_ext,
            fill='toself',
            name=label,
            fillcolor=_hex_to_rgba(color, 0.2),
            line=dict(color=color, width=2),
            marker=dict(size=6, color=color),
            hovertemplate='%{theta}: %{r:.1f}<extra></extra>'
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(family='Microsoft YaHei', size=10)
            ),
            angularaxis=dict(
                tickfont=dict(family='Microsoft YaHei', size=12)
            )
        ),
        title=dict(
            text='各项目可完成度雷达图对比',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        legend=dict(
            font=dict(family='Microsoft YaHei', size=11),
            orientation='h',
            y=-0.15
        ),
        height=500,
        margin=dict(l=40, r=40, t=80, b=100)
    )
    return fig


def plot_inventory_change_comparison(
    inventory_before: Dict[str, float],
    inventory_after: Dict[str, float],
    top_n: int = 15
) -> go.Figure:
    if not inventory_before:
        return go.Figure()

    items = []
    for name in inventory_before:
        before = inventory_before.get(name, 0)
        after = inventory_after.get(name, before)
        change = after - before
        if before > 0 or after > 0:
            items.append({
                'color_name': name,
                'before': before,
                'after': after,
                'change': change,
                'change_pct': (change / before * 100) if before > 0 else (100 if after > 0 else 0)
            })

    df = pd.DataFrame(items)
    if len(df) == 0:
        return go.Figure()

    df = df.sort_values('change', ascending=True).head(top_n)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df['color_name'],
        x=df['before'],
        name='分配前库存',
        orientation='h',
        marker_color='#3498DB',
        hovertemplate='%{y}<br>分配前: %{x}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        y=df['color_name'],
        x=df['after'],
        name='分配后库存',
        orientation='h',
        marker_color='#E74C3C',
        hovertemplate='%{y}<br>分配后: %{x}<extra></extra>'
    ))

    fig.update_layout(
        barmode='group',
        title=dict(
            text=f'库存消耗前后对比 (Top {len(df)})',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='库存数量', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(text='颜色名称', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        legend=dict(
            font=dict(family='Microsoft YaHei'),
            orientation='h',
            y=-0.15
        ),
        height=max(400, 35 * len(df) + 150),
        margin=dict(l=100, r=40, t=60, b=100)
    )
    return fig


def plot_budget_allocation(
    allocations: Dict[str, Dict[str, Any]]
) -> go.Figure:
    if not allocations:
        return go.Figure()

    labels = []
    alloc_costs = []
    replenish_costs = []

    for pid, alloc in allocations.items():
        ptype = alloc.get('project_type', '')
        labels.append(f"{pid}\n({ptype})")
        alloc_costs.append(alloc.get('total_allocated_cost', 0))
        replenish_costs.append(alloc.get('total_replenish_cost', 0))

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=alloc_costs,
        name='库存消耗成本',
        marker_color='#27AE60',
        hovertemplate='%{x}<br>库存消耗: ¥%{y:.2f}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        x=labels,
        y=replenish_costs,
        name='补货成本',
        marker_color='#E67E22',
        hovertemplate='%{x}<br>补货: ¥%{y:.2f}<extra></extra>'
    ))

    fig.update_layout(
        barmode='stack',
        title=dict(
            text='各项目预算占用分布',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='项目', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(text='金额 (¥)', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei'),
            tickprefix='¥'
        ),
        legend=dict(
            font=dict(family='Microsoft YaHei'),
            orientation='h',
            y=-0.2
        ),
        height=450,
        margin=dict(l=60, r=40, t=60, b=120)
    )
    return fig


def plot_strategy_comparison_bar(comparison_df: pd.DataFrame) -> go.Figure:
    if comparison_df is None or len(comparison_df) == 0:
        return go.Figure()

    df = comparison_df.copy()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['strategy_name'],
        y=df['total_replenish_cost'],
        name='补货总成本 (¥)',
        marker_color='#E74C3C',
        yaxis='y',
        hovertemplate='%{x}<br>补货成本: ¥%{y:.2f}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        x=df['strategy_name'],
        y=df['average_harmony_score'],
        name='平均色彩协调度',
        marker_color='#3498DB',
        yaxis='y2',
        hovertemplate='%{x}<br>协调度: %{y:.1f}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=df['strategy_name'],
        y=df['average_long_unused_score'],
        name='长期未用消耗分',
        mode='lines+markers',
        marker=dict(color='#27AE60', size=12),
        line=dict(color='#27AE60', width=3),
        yaxis='y3',
        hovertemplate='%{x}<br>消耗分: %{y:.1f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text='三种策略关键指标对比',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='策略', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(text='补货成本 (¥)', font=dict(color='#E74C3C', family='Microsoft YaHei')),
            tickfont=dict(color='#E74C3C', family='Microsoft YaHei'),
            side='left',
            tickprefix='¥'
        ),
        yaxis2=dict(
            title=dict(text='色彩协调度', font=dict(color='#3498DB', family='Microsoft YaHei')),
            tickfont=dict(color='#3498DB', family='Microsoft YaHei'),
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        yaxis3=dict(
            title=dict(text='库存消耗分', font=dict(color='#27AE60', family='Microsoft YaHei')),
            tickfont=dict(color='#27AE60'),
            overlaying='y',
            side='right',
            position=0.95,
            range=[0, 100],
            showgrid=False
        ),
        legend=dict(
            font=dict(family='Microsoft YaHei'),
            orientation='h',
            y=-0.2
        ),
        height=500,
        margin=dict(l=80, r=120, t=60, b=120)
    )
    return fig


def plot_conflict_heatmap(
    conflicts: List[Dict[str, Any]],
    project_ids: List[str]
) -> go.Figure:
    if not project_ids or len(project_ids) < 2:
        return go.Figure()

    n = len(project_ids)
    matrix = np.zeros((n, n))
    text_matrix = [[''] * n for _ in range(n)]

    proj_idx = {pid: i for i, pid in enumerate(project_ids)}

    severity_score = {'高': 3, '中': 2, '低': 1}

    for c in conflicts:
        i = proj_idx.get(c.get('project_1', ''))
        j = proj_idx.get(c.get('project_2', ''))
        if i is not None and j is not None:
            score = severity_score.get(c.get('severity', '低'), 1)
            matrix[i][j] = score
            matrix[j][i] = score
            text = f"{c.get('conflict_color', '')}\n短缺: {c.get('shortage', 0)}"
            text_matrix[i][j] = text
            text_matrix[j][i] = text

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=project_ids,
        y=project_ids,
        text=text_matrix,
        texttemplate='%{text}',
        colorscale=[
            [0, '#E8F8F5'],
            [0.33, '#F39C12'],
            [0.66, '#E67E22'],
            [1, '#E74C3C']
        ],
        showscale=True,
        colorbar=dict(
            title=dict(text='冲突严重度', font=dict(family='Microsoft YaHei')),
            tickvals=[0, 1, 2, 3],
            ticktext=['无', '低', '中', '高'],
            tickfont=dict(family='Microsoft YaHei')
        ),
        hovertemplate='项目1: %{y}<br>项目2: %{x}<br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text='项目间线材冲突热力图',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='项目', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(text='项目', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        height=500,
        margin=dict(l=80, r=40, t=60, b=80)
    )
    return fig


def plot_replenishment_priority(
    replenishment_df: pd.DataFrame,
    top_n: int = 15
) -> go.Figure:
    if replenishment_df is None or len(replenishment_df) == 0:
        return go.Figure()

    df = replenishment_df.copy().head(top_n)

    fig = go.Figure()

    color_map = {
        '最高': '#E74C3C',
        '高': '#E67E22',
        '中': '#F39C12',
        '低': '#3498DB',
        '最低': '#95A5A6'
    }

    bar_colors = df['priority'].map(color_map).fillna('#3498DB').tolist()

    fig.add_trace(go.Bar(
        x=df['shortage'],
        y=[f"{r['color_name']} ({r['project_id']})" for _, r in df.iterrows()],
        orientation='h',
        marker_color=bar_colors,
        text=[f"¥{r['estimated_cost']:.1f}" for _, r in df.iterrows()],
        textposition='outside',
        hovertemplate=(
            '颜色: %{y}<br>'
            '补货数量: %{x}<br>'
            '项目: %{customdata[0]}<br>'
            '优先级: %{customdata[1]}<br>'
            '匹配度: %{customdata[2]:.1f}<extra></extra>'
        ),
        customdata=df[['project_type', 'priority', 'color_match_score']].values
    ))

    fig.update_layout(
        title=dict(
            text=f'补货优先级排序 (Top {len(df)})',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='补货数量', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(text='颜色 (项目)', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        height=max(400, 35 * len(df) + 100),
        margin=dict(l=150, r=80, t=60, b=60)
    )
    return fig


def plot_long_unused_consumption_gauge(
    consumption_potential: Dict[str, Any]
) -> go.Figure:
    ratio = consumption_potential.get('consumption_ratio', 0)

    fig = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=ratio,
        domain={'x': [0, 1], 'y': [0, 1]},
        title=dict(
            text='长期未使用线材消耗比例',
            font=dict(size=16, family='Microsoft YaHei')
        ),
        delta={'reference': 50, 'valueformat': '.1f', 'suffix': '%'},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickcolor': 'darkgray',
                'tickformat': '.0f',
                'ticksuffix': '%'
            },
            'bar': {'color': '#27AE60'},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': 'gray',
            'steps': [
                {'range': [0, 30], 'color': '#FFEBE6'},
                {'range': [30, 60], 'color': '#FFF4E6'},
                {'range': [60, 100], 'color': '#E8F8F5'}
            ],
            'threshold': {
                'line': {'color': '#E74C3C', 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        },
        number={'suffix': '%', 'font': {'size': 36, 'family': 'Microsoft YaHei'}}
    ))

    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    return fig


def plot_color_reuse_sunburst(
    reuse_info: Dict[str, Any]
) -> go.Figure:
    usage_counts = reuse_info.get('color_usage_counts', [])
    if not usage_counts:
        return go.Figure()

    fig = go.Figure()

    ids = []
    labels = []
    parents = []
    values = []
    colors = []

    root_id = 'root'
    ids.append(root_id)
    labels.append('颜色复用总览')
    parents.append('')
    values.append(sum(u.get('project_count', 1) for u in usage_counts))
    colors.append('#FAFAFA')

    project_counts = sorted(set(u.get('project_count', 1) for u in usage_counts), reverse=True)

    for pc in project_counts:
        pc_id = f'pc_{pc}'
        ids.append(pc_id)
        label = f'复用于{pc}个项目' if pc > 1 else '仅用于1个项目'
        labels.append(label)
        parents.append(root_id)
        pc_items = [u for u in usage_counts if u.get('project_count', 1) == pc]
        values.append(sum(u.get('total_quantity', 1) for u in pc_items))
        colors.append(get_family_color('中性色'))

        for u in pc_items:
            uid = f"color_{u.get('color_name', '')}_{pc}"
            ids.append(uid)
            labels.append(f"{u.get('color_name', '')}\n({u.get('total_quantity', 0)})")
            parents.append(pc_id)
            values.append(u.get('total_quantity', 1))
            fam = u.get('color_family', '未分类')
            colors.append(COLOR_FAMILY_HEX.get(fam, '#BDC3C7'))

    fig.add_trace(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors),
        branchvalues='total',
        hovertemplate='%{label}<br>值: %{value}<extra></extra>',
        textfont=dict(family='Microsoft YaHei', size=11)
    ))

    fig.update_layout(
        title=dict(
            text='颜色跨项目复用分布',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        height=500,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    return fig


def plot_project_color_allocation(
    allocation: Dict[str, Any],
    title: str = '项目颜色分配'
) -> go.Figure:
    allocated_colors = allocation.get('allocated_colors', [])
    if not allocated_colors:
        return go.Figure()

    hex_colors = []
    labels = []

    for ac in allocated_colors:
        h = ac.get('color_hex', '')
        if h:
            hex_colors.append(h)
            alloc = ac.get('allocated_quantity', 0)
            replenish = ac.get('replenish_quantity', 0)
            label_parts = [ac.get('color_name', '')]
            if alloc > 0:
                label_parts.append(f"库存:{alloc}")
            if replenish > 0:
                label_parts.append(f"补货:{replenish}")
            labels.append('\n'.join(label_parts))

    return plot_color_swatch(hex_colors, labels=labels, title=title)
