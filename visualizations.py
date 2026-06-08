import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from PIL import Image
import io


COLOR_FAMILY_HEX = {
    '红色系': '#E74C3C',
    '橙色系': '#E67E22',
    '黄色系': '#F1C40F',
    '绿色系': '#27AE60',
    '青色系': '#1ABC9C',
    '蓝色系': '#3498DB',
    '紫色系': '#8E44AD',
    '粉色系': '#E91E63',
    '白色': '#ECF0F1',
    '黑色': '#2C3E50',
    '灰色': '#95A5A6',
    '米色': '#D4B896',
    '棕色': '#A0522D',
    '中性色': '#7F8C8D',
    '未分类': '#BDC3C7'
}


def get_family_color(family_name):
    return COLOR_FAMILY_HEX.get(family_name, '#BDC3C7')


def plot_color_distribution_pie(color_dist):
    if color_dist is None or len(color_dist) == 0:
        return go.Figure()

    labels = color_dist['color_family'].tolist()
    values = color_dist['quantity'].tolist()
    colors = [get_family_color(l) for l in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color='#ffffff', width=2)),
        textinfo='label+percent',
        textfont=dict(size=13, family='Microsoft YaHei'),
        hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>'
    )])

    fig.update_layout(
        title=dict(
            text='色系库存分布',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        legend=dict(
            font=dict(family='Microsoft YaHei', size=12),
            orientation='h',
            y=-0.1
        ),
        height=450,
        margin=dict(l=20, r=20, t=60, b=80)
    )
    return fig


def plot_inventory_stack_bar(material_thickness_data):
    if material_thickness_data is None or len(material_thickness_data) == 0:
        return go.Figure()

    pivot_df = material_thickness_data.pivot(
        index='material',
        columns='thickness',
        values='quantity'
    ).fillna(0)

    fig = go.Figure()

    for thickness in pivot_df.columns:
        fig.add_trace(go.Bar(
            name=str(thickness),
            x=pivot_df.index.tolist(),
            y=pivot_df[thickness].tolist(),
            hovertemplate='材质: %{x}<br>粗细: %{legendgroup}<br>数量: %{y}<extra></extra>'
        ))

    fig.update_layout(
        barmode='stack',
        title=dict(
            text='各材质×粗细库存堆积分布',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(
                text='材质',
                font=dict(family='Microsoft YaHei')
            ),
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(
                text='库存数量',
                font=dict(family='Microsoft YaHei')
            ),
            tickfont=dict(family='Microsoft YaHei')
        ),
        legend=dict(
            title='粗细规格',
            font=dict(family='Microsoft YaHei'),
            orientation='h',
            y=-0.25
        ),
        height=500,
        margin=dict(l=40, r=20, t=60, b=120)
    )
    return fig


def plot_material_comparison(material_dist):
    if material_dist is None or len(material_dist) == 0:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=material_dist['material'],
        y=material_dist['quantity'],
        name='数量',
        marker_color='#3498DB',
        yaxis='y',
        hovertemplate='材质: %{x}<br>数量: %{y}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=material_dist['material'],
        y=material_dist['value'],
        name='总价值',
        mode='lines+markers',
        marker=dict(color='#E74C3C', size=10),
        line=dict(color='#E74C3C', width=3),
        yaxis='y2',
        hovertemplate='材质: %{x}<br>价值: %{y:.2f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text='各材质数量与价值对比',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(
                text='材质',
                font=dict(family='Microsoft YaHei')
            ),
            tickfont=dict(family='Microsoft YaHei')
        ),
        yaxis=dict(
            title=dict(
                text='数量',
                font=dict(color='#3498DB', family='Microsoft YaHei')
            ),
            tickfont=dict(color='#3498DB'),
            side='left'
        ),
        yaxis2=dict(
            title=dict(
                text='总价值',
                font=dict(color='#E74C3C', family='Microsoft YaHei')
            ),
            tickfont=dict(color='#E74C3C'),
            overlaying='y',
            side='right'
        ),
        legend=dict(font=dict(family='Microsoft YaHei'), x=0.85, y=0.95),
        height=450,
        margin=dict(l=60, r=60, t=60, b=80)
    )
    return fig


def plot_family_by_material(by_family_material):
    if by_family_material is None or len(by_family_material) == 0:
        return go.Figure()

    pivot = by_family_material.pivot(
        index='color_family',
        columns='material',
        values='quantity'
    ).fillna(0)

    fig = go.Figure()
    for mat in pivot.columns:
        fig.add_trace(go.Bar(
            name=str(mat),
            x=pivot.index.tolist(),
            y=pivot[mat].tolist(),
            hovertemplate='色系: %{x}<br>材质: %{legendgroup}<br>数量: %{y}<extra></extra>'
        ))

    fig.update_layout(
        barmode='group',
        title=dict(
            text='各色系×材质对比分布',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(
                text='色系',
                font=dict(family='Microsoft YaHei')
            ),
            tickfont=dict(family='Microsoft YaHei'),
            tickangle=45
        ),
        yaxis=dict(
            title=dict(
                text='库存数量',
                font=dict(family='Microsoft YaHei')
            ),
            tickfont=dict(family='Microsoft YaHei')
        ),
        legend=dict(
            title='材质',
            font=dict(family='Microsoft YaHei'),
            orientation='h',
            y=-0.3
        ),
        height=500,
        margin=dict(l=40, r=20, t=60, b=150)
    )
    return fig


def plot_redundant_shortage(analysis_result):
    if analysis_result is None or len(analysis_result) == 0:
        return go.Figure()

    status_colors = {
        '过剩': '#E74C3C',
        '不足': '#F39C12',
        '缺货': '#95A5A6'
    }

    fig = go.Figure()
    for status, group in analysis_result.groupby('status'):
        fig.add_trace(go.Bar(
            name=status,
            x=group['color_family'],
            y=group['percentage'],
            marker_color=status_colors.get(status, '#3498DB'),
            hovertemplate='色系: %{x}<br>占比: %{y:.2f}%<br>状态: ' + status + '<extra></extra>'
        ))

    fig.update_layout(
        title=dict(
            text='过剩/不足色系分析',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(
                text='色系',
                font=dict(family='Microsoft YaHei')
            ),
            tickfont=dict(family='Microsoft YaHei'),
            tickangle=45
        ),
        yaxis=dict(
            title=dict(
                text='占比 (%)',
                font=dict(family='Microsoft YaHei')
            ),
            tickfont=dict(family='Microsoft YaHei')
        ),
        legend=dict(font=dict(family='Microsoft YaHei')),
        height=400,
        margin=dict(l=40, r=20, t=60, b=120)
    )
    return fig


def plot_color_swatch(hex_colors, labels=None, title='颜色搭配预览'):
    if not hex_colors or len(hex_colors) == 0:
        return None

    n = len(hex_colors)
    fig = go.Figure()

    for i, color in enumerate(hex_colors):
        label = labels[i] if labels and i < len(labels) else color
        fig.add_shape(
            type='rect',
            x0=i / n, y0=0,
            x1=(i + 1) / n, y1=1,
            xref='paper', yref='paper',
            fillcolor=color,
            line=dict(color='white', width=3)
        )
        fig.add_annotation(
            x=(i + 0.5) / n,
            y=0.5,
            xref='paper',
            yref='paper',
            text=label,
            showarrow=False,
            font=dict(
                family='Microsoft YaHei',
                size=12,
                color=_get_text_color(color)
            )
        )

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=16, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=180,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    return fig


def _get_text_color(bg_hex):
    try:
        bg_hex = bg_hex.lstrip('#')
        r = int(bg_hex[0:2], 16)
        g = int(bg_hex[2:4], 16)
        b = int(bg_hex[4:6], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return '#000000' if brightness > 128 else '#FFFFFF'
    except Exception:
        return '#FFFFFF'


def plot_project_match_radar(schemes):
    if not schemes:
        return go.Figure()

    categories = []
    values = []

    scheme_scores = {
        'complementary': 4,
        'split_complementary': 5,
        'triadic': 5,
        'analogous': 4,
        'monochromatic': 3
    }

    name_map = {
        'complementary': '互补色',
        'split_complementary': '分裂互补',
        'triadic': '三角色',
        'analogous': '邻近色',
        'monochromatic': '同色系'
    }

    for key, score in scheme_scores.items():
        if key in schemes:
            matches = schemes[key].get('inventory_matches', [])
            n = len(matches)
            categories.append(name_map.get(key, key))
            values.append(min(score + n, 10))

    fig = go.Figure(data=go.Scatterpolar(
        r=values + values[:1],
        theta=categories + categories[:1],
        fill='toself',
        fillcolor='rgba(52, 152, 219, 0.3)',
        line=dict(color='#3498DB', width=3),
        marker=dict(size=8, color='#3498DB'),
        hovertemplate='%{theta}: %{r:.1f}<extra></extra>'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickfont=dict(family='Microsoft YaHei')
            ),
            angularaxis=dict(
                tickfont=dict(family='Microsoft YaHei', size=12)
            )
        ),
        title=dict(
            text='编织项目匹配度分析',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        height=450,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig


def plot_inventory_treemap(df):
    if df is None or len(df) == 0:
        return go.Figure()

    df_plot = df.copy()
    df_plot['color_hex_display'] = df_plot['color_hex'].fillna('#BDC3C7')

    ids = []
    labels = []
    parents = []
    values = []
    colors = []
    hover_texts = []

    root_id = 'root'
    ids.append(root_id)
    labels.append('全部库存')
    parents.append('')
    values.append(int(df_plot['quantity'].sum()))
    colors.append('#FAFAFA')
    hover_texts.append(f'全部库存<br>总数量: {df_plot["quantity"].sum()}')

    for mat in df_plot['material'].unique():
        mat_df = df_plot[df_plot['material'] == mat]
        mat_id = f'mat_{mat}'
        ids.append(mat_id)
        labels.append(str(mat))
        parents.append(root_id)
        values.append(int(mat_df['quantity'].sum()))
        colors.append('#F5F5F5')
        hover_texts.append(f'材质: {mat}<br>数量: {mat_df["quantity"].sum()}')

        for fam in mat_df['color_family'].unique():
            fam_df = mat_df[mat_df['color_family'] == fam]
            fam_id = f'fam_{mat}_{fam}'
            ids.append(fam_id)
            labels.append(str(fam))
            parents.append(mat_id)
            values.append(int(fam_df['quantity'].sum()))
            colors.append(get_family_color(fam))
            hover_texts.append(f'色系: {fam}<br>数量: {fam_df["quantity"].sum()}')

            for _, row in fam_df.iterrows():
                cid = f'color_{mat}_{fam}_{row["color_name"]}'
                ids.append(cid)
                labels.append(f'{row["color_name"]}<br>{row["quantity"]}')
                parents.append(fam_id)
                values.append(int(row['quantity']))
                colors.append(row['color_hex_display'])
                hover_texts.append(
                    f'颜色: {row["color_name"]}<br>'
                    f'色系: {row["color_family"]}<br>'
                    f'材质: {row["material"]}<br>'
                    f'粗细: {row.get("thickness", "-")}<br>'
                    f'数量: {row["quantity"]}<br>'
                    f'色号: {row.get("color_hex", "-")}'
                )

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors),
        hovertext=hover_texts,
        hoverinfo='text',
        texttemplate='%{label}',
        textfont=dict(family='Microsoft YaHei', size=12)
    ))

    fig.update_layout(
        title=dict(
            text='库存层级结构图',
            font=dict(size=18, family='Microsoft YaHei'),
            x=0.5
        ),
        height=550,
        margin=dict(l=10, r=10, t=60, b=30)
    )
    fig.update_traces(
        textfont=dict(family='Microsoft YaHei', size=12),
        hoverlabel=dict(font=dict(family='Microsoft YaHei'))
    )
    return fig


def simulate_knit_pattern(hex_colors, pattern_type='stripes', width=400, height=300):
    if not hex_colors or len(hex_colors) == 0:
        return None

    img = Image.new('RGB', (width, height))
    pixels = img.load()

    n_colors = len(hex_colors)
    rgb_colors = []
    for h in hex_colors:
        h = h.lstrip('#')
        rgb_colors.append((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)))

    if pattern_type == 'stripes':
        stripe_height = height // (n_colors * 2)
        for y in range(height):
            color_idx = (y // stripe_height) % n_colors
            for x in range(width):
                noise = _knit_noise(x, y)
                r, g, b = rgb_colors[color_idx]
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )
    elif pattern_type == 'checker':
        cell_size = 40
        for y in range(height):
            for x in range(width):
                cell_x = x // cell_size
                cell_y = y // cell_size
                color_idx = (cell_x + cell_y) % n_colors
                noise = _knit_noise(x, y)
                r, g, b = rgb_colors[color_idx]
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )
    elif pattern_type == 'gradient':
        for y in range(height):
            ratio = y / height
            idx = ratio * (n_colors - 1)
            i = int(idx)
            t = idx - i
            i = min(i, n_colors - 2)
            for x in range(width):
                r = int(rgb_colors[i][0] * (1 - t) + rgb_colors[i + 1][0] * t)
                g = int(rgb_colors[i][1] * (1 - t) + rgb_colors[i + 1][1] * t)
                b = int(rgb_colors[i][2] * (1 - t) + rgb_colors[i + 1][2] * t)
                noise = _knit_noise(x, y)
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )
    elif pattern_type == 'fairisle':
        for y in range(height):
            row_pattern = y % 8
            for x in range(width):
                col_pattern = x % 8
                if (row_pattern + col_pattern) % 3 == 0 and abs(row_pattern - col_pattern) < 3:
                    color_idx = 1 % n_colors
                elif row_pattern in [0, 4] and col_pattern in [0, 4]:
                    color_idx = 2 % n_colors
                else:
                    color_idx = 0
                noise = _knit_noise(x, y)
                r, g, b = rgb_colors[color_idx]
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )
    else:
        cell_size = 80
        for y in range(height):
            for x in range(width):
                cell_x = x // cell_size
                cell_y = y // cell_size
                color_idx = (cell_x * 2 + cell_y) % n_colors
                noise = _knit_noise(x, y)
                r, g, b = rgb_colors[color_idx]
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def _knit_noise(x, y):
    import math
    noise = math.sin(x * 0.3 + y * 0.2) * 4 + math.cos(x * 0.15 - y * 0.25) * 3
    return int(noise)


def plot_pre_post_replenishment_preview(
    before_colors: List[Dict[str, Any]],
    after_colors: List[Dict[str, Any]],
    project_type: str = '',
    pattern_type: str = 'stripes'
) -> go.Figure:
    if not before_colors and not after_colors:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text='暂无配色数据', font=dict(size=16, family='Microsoft YaHei')),
            height=280
        )
        return fig

    fig = go.Figure()

    valid_before = [c for c in before_colors if c.get('color_hex')]
    valid_after = [c for c in after_colors if c.get('color_hex')]

    before_hex = [c['color_hex'] for c in valid_before]
    after_hex = [c['color_hex'] for c in valid_after]

    n_before = max(1, len(before_hex))
    n_after = max(1, len(after_hex))
    total = n_before + n_after + 1

    for i, h in enumerate(before_hex):
        x0 = i / total
        x1 = (i + 1) / total
        fig.add_shape(
            type='rect',
            x0=x0, y0=0.55,
            x1=x1, y1=1,
            xref='paper', yref='paper',
            fillcolor=h,
            line=dict(color='white', width=3)
        )
        if i < len(valid_before):
            c = valid_before[i]
            label = c.get('color_name', h)
            alloc = c.get('allocated_quantity', 0)
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=0.775,
                xref='paper', yref='paper',
                text=f"{label}<br>{alloc}",
                showarrow=False,
                font=dict(
                    family='Microsoft YaHei',
                    size=10,
                    color=_get_text_color(h)
                )
            )

    fig.add_shape(
        type='rect',
        x0=n_before / total, y0=0,
        x1=(n_before + 1) / total, y1=1,
        xref='paper', yref='paper',
        fillcolor='#F5F5F5',
        line=dict(color='#DDD', width=1)
    )
    fig.add_annotation(
        x=(n_before + 0.5) / total,
        y=0.5,
        xref='paper', yref='paper',
        text='→补货→',
        showarrow=False,
        font=dict(
            family='Microsoft YaHei',
            size=14,
            color='#666'
        ),
        textangle=-90
    )

    for i, h in enumerate(after_hex):
        x0 = (n_before + 1 + i) / total
        x1 = (n_before + 2 + i) / total
        fig.add_shape(
            type='rect',
            x0=x0, y0=0.55,
            x1=x1, y1=1,
            xref='paper', yref='paper',
            fillcolor=h,
            line=dict(color='white', width=3)
        )
        if i < len(valid_after):
            c = valid_after[i]
            label = c.get('color_name', h)
            total_q = c.get('allocated_quantity', 0) + c.get('replenish_quantity', 0)
            replenish = c.get('replenish_quantity', 0)
            suffix = f"+{replenish}" if replenish > 0 else ""
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=0.775,
                xref='paper', yref='paper',
                text=f"{label}<br>{total_q}{suffix}",
                showarrow=False,
                font=dict(
                    family='Microsoft YaHei',
                    size=10,
                    color=_get_text_color(h)
                )
            )

    fig.add_annotation(
        x=n_before / (2 * total),
        y=0.275,
        xref='paper', yref='paper',
        text='补货前配色',
        showarrow=False,
        font=dict(family='Microsoft YaHei', size=13, color='#333')
    )
    fig.add_annotation(
        x=(n_before + 1 + n_after / 2) / total,
        y=0.275,
        xref='paper', yref='paper',
        text='补货后配色',
        showarrow=False,
        font=dict(family='Microsoft YaHei', size=13, color='#333')
    )
    fig.add_annotation(
        x=n_before / (2 * total),
        y=0.05,
        xref='paper', yref='paper',
        text=f'（仅库存可分配部分）',
        showarrow=False,
        font=dict(family='Microsoft YaHei', size=10, color='#888')
    )
    fig.add_annotation(
        x=(n_before + 1 + n_after / 2) / total,
        y=0.05,
        xref='paper', yref='paper',
        text=f'（含建议补货部分）',
        showarrow=False,
        font=dict(family='Microsoft YaHei', size=10, color='#888')
    )

    title_text = f'{project_type} - 补货前后成品配色对比' if project_type else '补货前后成品配色对比'
    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=16, family='Microsoft YaHei'),
            x=0.5
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 1]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 1]),
        height=280,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    return fig


def plot_multi_project_metrics_summary(
    summary_data: Dict[str, Any]
) -> go.Figure:
    metrics = [
        ('项目数量', summary_data.get('project_count', 0), '#3498DB'),
        ('平均可完成度', summary_data.get('average_feasibility', 0), '#27AE60'),
        ('冲突数', summary_data.get('conflict_count', 0), '#E74C3C'),
        ('颜色复用分', summary_data.get('reuse_score', 0), '#8E44AD'),
        ('补货总量', summary_data.get('total_shortage_quantity', 0), '#E67E22'),
        ('补货总成本', summary_data.get('total_shortage_cost', 0), '#F39C12')
    ]

    fig = go.Figure()

    for i, (name, value, color) in enumerate(metrics):
        is_cost = '成本' in name
        display_val = f"¥{value:.1f}" if is_cost else (f"{value:.1f}" if isinstance(value, float) else str(value))

        fig.add_trace(go.Indicator(
            mode='number',
            value=float(value) if isinstance(value, (int, float)) else 0,
            title=dict(text=name, font=dict(size=14, family='Microsoft YaHei')),
            number=dict(
                font=dict(size=28, family='Microsoft YaHei', color=color),
                prefix='¥' if is_cost else '',
                valueformat='.1f'
            ),
            domain={'row': 0, 'column': i}
        ))

    fig.update_layout(
        grid={'rows': 1, 'columns': len(metrics), 'pattern': 'independent'},
        height=200,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    return fig
