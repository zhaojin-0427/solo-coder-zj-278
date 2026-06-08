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


def plot_series_color_consistency(
    series_plans: Dict[str, Dict[str, Any]],
    base_palette: List[Dict[str, Any]]
) -> go.Figure:
    if not series_plans:
        fig = go.Figure()
        fig.update_layout(title=dict(text='暂无项目数据', font=dict(size=16, family='Microsoft YaHei')))
        return fig

    fig = go.Figure()

    base_hexes = [c.get('color_hex') for c in base_palette if c.get('color_hex')]
    base_labels = [f"{c.get('color_name', '')}\n{c.get('role', '')}" for c in base_palette]

    for i, (pid, plan) in enumerate(series_plans.items()):
        colors = plan.get('selected_colors', [])
        hexes = []
        labels = []

        for c in colors:
            h = c.get('color_hex', '')
            if h:
                hexes.append(h)
                label = c.get('color_name', '')
                alloc = c.get('total_available_for_project', 0)
                need = c.get('total_needed', 0)
                rep = c.get('replenish_qty', 0)
                labels.append(f"{label}\n分配:{alloc:.0f} | 需:{need:.0f}")

        if not hexes:
            continue

        for j, (h, lbl) in enumerate(zip(hexes, labels)):
            in_base = h in base_hexes
            fig.add_trace(go.Scatter(
                x=[j],
                y=[i],
                mode='markers',
                marker=dict(
                    size=40,
                    color=h,
                    line=dict(
                        color='#2ECC71' if in_base else '#E74C3C',
                        width=3 if in_base else 2
                    )
                ),
                text=lbl,
                hoverinfo='text',
                name=f"{pid} - {plan.get('project_type', '')}",
                showlegend=(j == 0)
            ))

    y_labels = [
        f"{pid} - {plan.get('project_type', '')}"
        for pid, plan in series_plans.items()
    ]

    fig.update_layout(
        title=dict(
            text='系列色彩一致性矩阵 (绿框=沿用基础色板, 红框=项目独立选色)',
            font=dict(size=16, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='颜色位置', font=dict(family='Microsoft YaHei')),
            tickmode='linear',
            tick0=0,
            dtick=1,
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(text='系列项目', font=dict(family='Microsoft YaHei')),
            tickvals=list(range(len(y_labels))),
            ticktext=y_labels,
            tickfont=dict(family='Microsoft YaHei')
        ),
        height=max(350, 120 * len(series_plans)),
        margin=dict(l=180, r=40, t=80, b=60),
        showlegend=True,
        legend=dict(font=dict(family='Microsoft YaHei'))
    )
    return fig


def plot_series_inventory_change(
    inventory_changes: Dict[str, Any],
    top_n: int = 15
) -> go.Figure:
    changes = inventory_changes.get('changes', [])
    if not changes:
        return go.Figure()

    df = pd.DataFrame(changes)
    df = df[df['quantity_used'] > 0].copy()
    if len(df) == 0:
        fig = go.Figure()
        fig.update_layout(title=dict(text='无库存消耗', font=dict(size=16, family='Microsoft YaHei')))
        return fig

    df = df.sort_values('quantity_used', ascending=False).head(top_n)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df['color_name'],
        x=df['quantity_before'],
        name='规划前库存',
        orientation='h',
        marker_color='#3498DB',
        hovertemplate='%{y}<br>规划前: %{x}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        y=df['color_name'],
        x=df['quantity_after'],
        name='规划后库存',
        orientation='h',
        marker_color='#E74C3C',
        hovertemplate='%{y}<br>规划后: %{x}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        y=df['color_name'],
        x=df['quantity_used'],
        mode='markers',
        name='消耗量',
        marker=dict(color='#27AE60', size=12, symbol='diamond'),
        xaxis='x2',
        hovertemplate='%{y}<br>消耗: %{x}<extra></extra>'
    ))

    fig.update_layout(
        barmode='group',
        title=dict(
            text=f'系列整体库存消耗前后对比 (Top {len(df)})',
            font=dict(size=16, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='库存数量', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        xaxis2=dict(
            title=dict(text='消耗量', font=dict(color='#27AE60', family='Microsoft YaHei')),
            overlaying='x',
            side='top',
            tickfont=dict(color='#27AE60', family='Microsoft YaHei')
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
        margin=dict(l=120, r=40, t=80, b=120)
    )
    return fig


def plot_series_budget_allocation(
    series_plans: Dict[str, Dict[str, Any]],
    summary: Dict[str, Any]
) -> go.Figure:
    if not series_plans:
        return go.Figure()

    labels = []
    alloc_costs = []
    replenish_costs = []

    for pid, plan in series_plans.items():
        ptype = plan.get('project_type', '')
        size = plan.get('target_size', '')
        labels.append(f"{pid}\n{ptype} {size}")
        alloc_costs.append(plan.get('total_allocated_cost', 0))
        replenish_costs.append(plan.get('total_replenish_cost', 0))

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

    budget_min = summary.get('budget_min', 0)
    budget_max = summary.get('budget_max', 0)
    if budget_max > 0:
        total_per_project = [a + r for a, r in zip(alloc_costs, replenish_costs)]
        fig.add_hline(
            y=budget_max,
            line_dash="dash",
            line_color="#E74C3C",
            annotation_text=f"预算上限: ¥{budget_max:.0f}",
            annotation_position="top right"
        )
        if budget_min > 0:
            fig.add_hline(
                y=budget_min,
                line_dash="dash",
                line_color="#3498DB",
                annotation_text=f"预算下限: ¥{budget_min:.0f}",
                annotation_position="bottom right"
            )

    fig.update_layout(
        barmode='stack',
        title=dict(
            text='各项目资金占用分布',
            font=dict(size=16, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='系列项目', font=dict(family='Microsoft YaHei')),
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
            y=-0.25
        ),
        height=450,
        margin=dict(l=80, r=40, t=80, b=140)
    )
    return fig


def plot_series_strategy_comparison(comparison_df: pd.DataFrame) -> go.Figure:
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
        y=df['visual_unity_score'],
        name='视觉统一性评分',
        marker_color='#3498DB',
        yaxis='y2',
        hovertemplate='%{x}<br>统一性: %{y:.1f}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=df['strategy_name'],
        y=df['long_unused_contribution'],
        name='滞销线材消耗贡献(%)',
        mode='lines+markers',
        marker=dict(color='#27AE60', size=12),
        line=dict(color='#27AE60', width=3),
        yaxis='y3',
        hovertemplate='%{x}<br>消耗贡献: %{y:.1f}%<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=df['strategy_name'],
        y=df['cross_project_reuse_rate'],
        name='跨项目复用率(%)',
        mode='lines+markers',
        marker=dict(color='#8E44AD', size=12, symbol='square'),
        line=dict(color='#8E44AD', width=3, dash='dash'),
        yaxis='y4',
        hovertemplate='%{x}<br>复用率: %{y:.1f}%<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text='三套策略核心指标对比',
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
            title=dict(text='视觉统一性', font=dict(color='#3498DB', family='Microsoft YaHei')),
            tickfont=dict(color='#3498DB', family='Microsoft YaHei'),
            overlaying='y',
            side='right',
            range=[0, 100],
            position=0.85
        ),
        yaxis3=dict(
            title=dict(text='滞销消耗(%)', font=dict(color='#27AE60', family='Microsoft YaHei')),
            tickfont=dict(color='#27AE60'),
            overlaying='y',
            side='right',
            position=0.92,
            range=[0, 100],
            showgrid=False
        ),
        yaxis4=dict(
            title=dict(text='复用率(%)', font=dict(color='#8E44AD', family='Microsoft YaHei')),
            tickfont=dict(color='#8E44AD'),
            overlaying='y',
            side='right',
            position=1.0,
            range=[0, 100],
            showgrid=False
        ),
        legend=dict(
            font=dict(family='Microsoft YaHei'),
            orientation='h',
            y=-0.25
        ),
        height=550,
        margin=dict(l=80, r=180, t=80, b=140)
    )
    return fig


def plot_series_replenishment_priority(
    replenishment_df: pd.DataFrame,
    top_n: int = 15
) -> go.Figure:
    if replenishment_df is None or len(replenishment_df) == 0:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text='🎉 无需补货！现有库存充足', font=dict(size=16, family='Microsoft YaHei'))
        )
        return fig

    df = replenishment_df.copy().head(top_n)

    bar_colors = []
    for _, row in df.iterrows():
        order = row.get('delivery_order', 3)
        if order <= 1:
            bar_colors.append('#E74C3C')
        elif order <= 2:
            bar_colors.append('#E67E22')
        elif order <= 3:
            bar_colors.append('#F39C12')
        else:
            bar_colors.append('#3498DB')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['replenish_qty'],
        y=[f"{r['color_name']} ({r['series_project_id']})" for _, r in df.iterrows()],
        orientation='h',
        marker_color=bar_colors,
        text=[f"¥{r['estimated_cost']:.0f}" for _, r in df.iterrows()],
        textposition='outside',
        hovertemplate=(
            '颜色: %{y}<br>'
            '补货数量: %{x}<br>'
            '项目类型: %{customdata[0]}<br>'
            '交付顺序: 第%{customdata[1]}批<br>'
            '优先级分: %{customdata[2]:.1f}<extra></extra>'
        ),
        customdata=df[['project_type', 'delivery_order', 'composite_score']].values
    ))

    fig.update_layout(
        title=dict(
            text=f'系列补货优先级排序 (Top {len(df)})',
            font=dict(size=16, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='补货数量', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(text='颜色 (所属项目)', font=dict(family='Microsoft YaHei')),
            tickfont=dict(family='Microsoft YaHei')
        ),
        height=max(400, 35 * len(df) + 100),
        margin=dict(l=180, r=100, t=60, b=60)
    )
    return fig


def plot_long_unused_contribution_gauge(
    contribution: Dict[str, Any]
) -> go.Figure:
    ratio = contribution.get('contribution_ratio', 0)

    fig = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=ratio,
        domain={'x': [0, 1], 'y': [0, 1]},
        title=dict(
            text='长期滞销线材消耗贡献',
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
            'bar': {'color': '#8E44AD'},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': 'gray',
            'steps': [
                {'range': [0, 20], 'color': '#FFEBE6'},
                {'range': [20, 50], 'color': '#FFF4E6'},
                {'range': [50, 80], 'color': '#E8F8F5'},
                {'range': [80, 100], 'color': '#D5F5E3'}
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


def plot_history_similarity_radar(
    history_similarity: Dict[str, Any],
    visual_unity: Dict[str, Any],
    summary: Dict[str, Any]
) -> go.Figure:
    categories = [
        '历史案例相似度',
        '季节主题匹配度',
        '视觉统一性',
        '色彩协调度',
        '跨项目复用率',
        '滞销消耗贡献'
    ]

    values = [
        history_similarity.get('best_similarity', 0),
        summary.get('season_match_score', 0),
        visual_unity.get('unity_score', 0),
        visual_unity.get('harmony_consistency', 0),
        summary.get('cross_project_reuse_rate', 0),
        summary.get('long_unused_contribution', 0)
    ]

    values = [float(v) for v in values]
    values_closed = values + values[:1]
    cat_ext = categories + categories[:1]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=cat_ext,
        fill='toself',
        name='当前系列',
        fillcolor='rgba(52, 152, 219, 0.2)',
        line=dict(color='#3498DB', width=2),
        marker=dict(size=6, color='#3498DB'),
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
            text='系列综合评估雷达图',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        height=500,
        margin=dict(l=40, r=40, t=80, b=40)
    )
    return fig


def plot_series_metrics_summary(summary: Dict[str, Any]) -> go.Figure:
    metrics = [
        ('项目数量', summary.get('project_count', 0), '#3498DB', '个'),
        ('色板颜色数', summary.get('base_palette_size', 0), '#27AE60', '色'),
        ('补货成本', summary.get('total_replenish_cost', 0), '#E74C3C', '¥'),
        ('复用率', summary.get('cross_project_reuse_rate', 0), '#8E44AD', '%'),
        ('视觉统一性', summary.get('visual_unity_score', 0), '#F39C12', '分'),
        ('滞销贡献', summary.get('long_unused_contribution', 0), '#1ABC9C', '%')
    ]

    fig = go.Figure()

    for i, (name, value, color, suffix) in enumerate(metrics):
        fig.add_annotation(
            x=i * 0.16 + 0.08,
            y=0.5,
            text=f"<b style='font-size:28px;color:{color};'>{value:.1f}{suffix}</b><br><span style='font-size:13px;color:#666;'>{name}</span>",
            showarrow=False,
            xref='paper',
            yref='paper',
            xanchor='center',
            yanchor='middle',
            align='center',
            bgcolor='#FAFAFA',
            bordercolor='#DEB887',
            borderwidth=1,
            borderpad=12,
            width=110
        )

    fig.update_layout(
        title=dict(
            text=f"{summary.get('series_name', '')} - {summary.get('strategy', '')}",
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        height=200,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(visible=False, range=[0, 1])
    )
    return fig


def plot_shared_yarn_sunburst(shared_scheme: Dict[str, Any]) -> go.Figure:
    shared_colors = shared_scheme.get('shared_colors', [])
    if not shared_colors:
        return go.Figure()

    per_project = shared_scheme.get('per_project_allocation', {})

    ids = []
    labels = []
    parents = []
    values = []
    colors_list = []

    root_id = 'root'
    ids.append(root_id)
    labels.append(f"共享线材池\n复用率: {shared_scheme.get('cross_project_reuse_rate', 0)}%")
    parents.append('')
    values.append(sum(sc.get('shared_quantity', 0) for sc in shared_colors))
    colors_list.append('#FAFAFA')

    for sc in shared_colors:
        cid = f"color_{sc['color_name']}"
        ids.append(cid)
        labels.append(f"{sc['color_name']}\n共享: {sc.get('shared_quantity', 0)}")
        parents.append(root_id)
        values.append(sc.get('shared_quantity', 0))
        fam = sc.get('color_family', '未分类')
        colors_list.append(COLOR_FAMILY_HEX.get(fam, '#BDC3C7'))

        for pid, alloc_list in per_project.items():
            for alloc in alloc_list:
                if alloc.get('color_name') == sc['color_name']:
                    aid = f"alloc_{pid}_{sc['color_name']}"
                    ids.append(aid)
                    labels.append(f"{pid}\n分配: {alloc.get('allocated_from_shared', 0)}")
                    parents.append(cid)
                    values.append(alloc.get('allocated_from_shared', 0))
                    colors_list.append(COLOR_FAMILY_HEX.get(fam, '#BDC3C7'))

    fig = go.Figure()
    fig.add_trace(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors_list),
        branchvalues='total',
        hovertemplate='%{label}<br>值: %{value}<extra></extra>',
        textfont=dict(family='Microsoft YaHei', size=11)
    ))

    fig.update_layout(
        title=dict(
            text='跨项目共享线材分配',
            font=dict(size=16, family='Microsoft YaHei'),
            x=0.5
        ),
        height=500,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    return fig
