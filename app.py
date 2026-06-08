import streamlit as st
import pandas as pd
import io
from datetime import datetime

from data_processor import load_and_process_data
from visualizations import (
    plot_color_distribution_pie,
    plot_inventory_stack_bar,
    plot_material_comparison,
    plot_family_by_material,
    plot_redundant_shortage,
    plot_color_swatch,
    plot_project_match_radar,
    plot_inventory_treemap,
    simulate_knit_pattern
)
from color_theory import generate_color_schemes, recommend_project_patterns
from inventory_optimizer import (
    generate_inventory_report,
    generate_optimization_actions,
    build_consumption_plan,
    inventory_health_score,
    get_health_label,
    get_material_recommendations
)


st.set_page_config(
    page_title="手工编织线材颜色搭配与库存优化分析台",
    page_icon="🧶",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #8B4513;
        text-align: center;
        padding: 1rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #FFF8DC 0%, #FFE4C4 100%);
        border-radius: 10px;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #5D4037;
        padding: 0.5rem 0;
        border-bottom: 2px solid #DEB887;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #FFFAF0 0%, #FFEFD5 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #DEB887;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #8B4513;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #8B7355;
    }
    .action-high {
        background-color: #FFEBE6;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #E74C3C;
        margin-bottom: 0.5rem;
    }
    .action-medium {
        background-color: #FFF4E6;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #F39C12;
        margin-bottom: 0.5rem;
    }
    .action-low {
        background-color: #E8F8F5;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #27AE60;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


def render_health_gauge(score):
    label, color = get_health_label(score)
    st.markdown(f"""
    <div style="text-align: center;">
        <div style="font-size: 3rem; font-weight: bold; color: {color};">{score}</div>
        <div style="font-size: 1.2rem; color: {color}; font-weight: bold;">{label}</div>
        <div style="width: 100%; height: 12px; background: #eee; border-radius: 6px; margin-top: 10px;">
            <div style="width: {score}%; height: 100%; background: {color}; border-radius: 6px; transition: width 0.5s;"></div>
        </div>
        <div style="font-size: 0.8rem; color: #888; margin-top: 5px;">库存健康度评分</div>
    </div>
    """, unsafe_allow_html=True)


def sidebar_section():
    with st.sidebar:
        st.markdown("## 🧶 数据上传")
        uploaded_file = st.file_uploader(
            "上传线材库存 CSV 文件",
            type=['csv'],
            help="CSV列包含: color_name, quantity, color_hex, material, thickness, last_used_date, price"
        )

        st.markdown("---")
        st.markdown("## 📋 CSV 格式说明")
        with st.expander("查看示例格式"):
            st.code("""
color_name,quantity,color_hex,material,thickness,last_used_date,price
大红色,10,#E74C3C,羊毛,中粗,2025-03-15,25.0
天蓝色,8,#3498DB,棉,中,2024-11-20,18.0
柠檬黄,5,#F1C40F,腈纶,细,2025-01-10,12.0
            """, language="csv")

        use_sample = st.checkbox("使用示例数据", value=False)

        st.markdown("---")
        st.markdown("## 🎨 颜色搭配设置")
        scheme_types = st.multiselect(
            "选择搭配类型",
            ['互补色', '邻近色', '三角色', '分裂互补', '同色系'],
            default=['互补色', '邻近色', '同色系']
        )
        scheme_map = {
            '互补色': 'complementary',
            '邻近色': 'analogous',
            '三角色': 'triadic',
            '分裂互补': 'split_complementary',
            '同色系': 'monochromatic'
        }
        selected_schemes = [scheme_map[s] for s in scheme_types]

        st.markdown("---")
        st.markdown("## ⏰ 库存优化阈值")
        days_threshold = st.slider(
            "长期未使用阈值（天）",
            min_value=30, max_value=365, value=180, step=30
        )

    return uploaded_file, use_sample, selected_schemes, days_threshold


def load_data(uploaded_file, use_sample, days_threshold):
    df = None
    if use_sample:
        sample_data = """color_name,quantity,color_hex,material,thickness,last_used_date,price
大红色,15,#E74C3C,羊毛,中粗,2024-08-15,28.0
玫瑰红,8,#C0392B,棉,中,2023-12-20,22.0
橙色,6,#E67E22,腈纶,中,2025-01-10,15.0
金黄色,4,#F39C12,羊毛,细,2024-06-05,30.0
柠檬黄,10,#F1C40F,棉,中,2024-09-22,18.0
嫩绿色,3,#2ECC71,腈纶,细,2023-05-18,14.0
深绿色,5,#27AE60,羊毛,中粗,2024-11-30,26.0
青色,2,#1ABC9C,棉,中,2022-10-01,20.0
天蓝色,12,#3498DB,羊毛,中,2025-02-14,25.0
藏青色,7,#2980B9,腈纶,中粗,2024-07-08,16.0
紫色,9,#8E44AD,羊毛,中,2024-03-25,32.0
浅紫色,4,#9B59B6,棉,细,2023-09-12,21.0
粉色,11,#E91E63,腈纶,中,2025-04-01,17.0
桃粉色,3,#FF69B4,棉,细,2024-12-18,19.0
米白色,14,#F5F5DC,羊毛,中粗,2025-03-20,24.0
纯白色,9,#FFFFFF,棉,中,2025-01-05,16.0
浅灰色,6,#BDC3C7,腈纶,中,2024-10-15,13.0
深灰色,8,#7F8C8D,羊毛,中粗,2024-08-30,27.0
纯黑色,5,#2C3E50,棉,中,2024-05-20,18.0
驼色,7,#A0522D,羊毛,粗,2024-02-14,35.0
米色,3,#D2B48C,腈纶,中,2023-11-11,15.0
棕色,4,#8B4513,棉,中粗,2024-06-18,20.0
珊瑚色,2,#FF7F50,羊毛,细,2023-03-08,29.0
酒红色,6,#8B0000,腈纶,中粗,2024-09-01,18.0
薄荷绿,3,#98FF98,棉,细,2024-12-01,17.0
        """
        df = load_and_process_data(io.StringIO(sample_data))
    elif uploaded_file is not None:
        try:
            df = load_and_process_data(uploaded_file)
        except ValueError as e:
            st.error(f"❌ 数据加载失败: {e}")
            return None

    if df is not None and 'last_used_date' in df.columns:
        from data_processor import analyze_long_unused as _alu
        from inventory_optimizer import generate_inventory_report as _gir
        pass

    return df


def render_dashboard(df, selected_schemes, days_threshold):
    st.markdown('<div class="main-header">🧶 手工编织线材颜色搭配与库存优化分析台</div>', unsafe_allow_html=True)

    from data_processor import analyze_long_unused
    from inventory_optimizer import generate_inventory_report

    report = generate_inventory_report(df)
    long_unused = analyze_long_unused(df, days_threshold=days_threshold)
    report['long_unused'] = long_unused
    stats = report['stats']

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">线材总数量</div></div>'.format(
            report['overview']['total_quantity']
        ), unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">颜色种类</div></div>'.format(
            report['overview']['total_colors']
        ), unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">材质种类</div></div>'.format(
            report['overview']['total_materials']
        ), unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><div class="metric-value">¥{:.1f}</div><div class="metric-label">库存总价值</div></div>'.format(
            report['overview']['total_value']
        ), unsafe_allow_html=True)
    with col5:
        render_health_gauge(inventory_health_score(report))

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 库存可视化分析",
        "🎨 颜色搭配推荐",
        "💡 编织项目匹配",
        "🔧 库存优化中心"
    ])

    with tab1:
        render_inventory_analysis(df, stats, report)

    with tab2:
        render_color_matching(df, selected_schemes)

    with tab3:
        render_project_matching(df, selected_schemes)

    with tab4:
        render_inventory_optimization(df, report, long_unused)


def render_inventory_analysis(df, stats, report):
    st.markdown('<div class="section-header">📊 库存可视化对比分析</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        pie_fig = plot_color_distribution_pie(stats['color_distribution'])
        st.plotly_chart(pie_fig, use_container_width=True)

    with col_b:
        stack_fig = plot_inventory_stack_bar(stats['material_thickness'])
        st.plotly_chart(stack_fig, use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        mat_fig = plot_material_comparison(stats['material_distribution'])
        st.plotly_chart(mat_fig, use_container_width=True)

    with col_d:
        fm_fig = plot_family_by_material(stats['by_family_material'])
        st.plotly_chart(fm_fig, use_container_width=True)

    st.markdown('<div class="section-header">📦 库存层级结构</div>', unsafe_allow_html=True)
    tree_fig = plot_inventory_treemap(df)
    st.plotly_chart(tree_fig, use_container_width=True)

    st.markdown('<div class="section-header">⚖️ 过剩与短缺分析</div>', unsafe_allow_html=True)
    rs = report['redundant_shortage']
    if len(rs) > 0:
        rs_fig = plot_redundant_shortage(rs)
        st.plotly_chart(rs_fig, use_container_width=True)

        st.markdown("**识别结果详情：**")
        display_cols = ['color_family', 'quantity', 'percentage', 'status', 'suggestion']
        available_cols = [c for c in display_cols if c in rs.columns]
        st.dataframe(
            rs[available_cols].rename(columns={
                'color_family': '色系',
                'quantity': '数量',
                'percentage': '占比(%)',
                'status': '状态',
                'suggestion': '建议'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ 库存分布均衡，未发现明显过剩或短缺色系")

    with st.expander("📋 查看完整库存数据"):
        display_df = df[[c for c in ['color_name', 'color_family', 'material', 'thickness', 'quantity', 'price', 'last_used_date'] if c in df.columns]].copy()
        display_df.columns = ['颜色名称', '色系', '材质', '粗细', '数量', '单价', '最后使用日期']
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_color_matching(df, selected_schemes):
    st.markdown('<div class="section-header">🎨 智能颜色搭配推荐</div>', unsafe_allow_html=True)

    color_options = df['color_name'].tolist()
    hex_options = df['color_hex'].tolist()
    display_options = [f"{name} ({hex_code})" if hex_code else name for name, hex_code in zip(color_options, hex_options)]

    selected_idx = st.selectbox(
        "选择一个基色生成搭配方案",
        range(len(display_options)),
        format_func=lambda i: display_options[i]
    )
    selected_row = df.iloc[selected_idx]

    st.markdown("**所选基色信息：**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if selected_row.get('color_hex'):
            st.markdown(f"""
            <div style="width:100%; height:80px; background:{selected_row['color_hex']}; border-radius:8px; border:2px solid #ddd;"></div>
            """, unsafe_allow_html=True)
    with col2:
        st.metric("颜色名称", selected_row['color_name'])
    with col3:
        st.metric("色系", selected_row.get('color_family', '-'))
    with col4:
        st.metric("库存数量", selected_row['quantity'])

    st.markdown("---")

    schemes = generate_color_schemes(selected_row, df, scheme_types=selected_schemes if selected_schemes else None)

    if not schemes:
        st.warning("⚠️ 请确保所选颜色有有效的HEX值")
        return

    for scheme_key, scheme_data in schemes.items():
        with st.container():
            st.markdown(f"### {scheme_data['name']}")
            st.info(scheme_data['description'])

            col_target, col_inventory = st.columns(2)
            with col_target:
                st.markdown("**理论目标色：**")
                target_fig = plot_color_swatch(
                    scheme_data['target_colors'],
                    labels=scheme_data['target_colors'],
                    title='理论色板'
                )
                if target_fig:
                    st.plotly_chart(target_fig, use_container_width=True)

            with col_inventory:
                st.markdown("**库存中最匹配的颜色：**")
                inv_colors = []
                inv_labels = []
                for match in scheme_data['inventory_matches']:
                    h = match.get('color_hex')
                    if h:
                        inv_colors.append(h)
                        inv_labels.append(f"{match['color_name']} ({match['quantity']})")
                if inv_colors:
                    inv_fig = plot_color_swatch(inv_colors, labels=inv_labels, title='库存匹配')
                    st.plotly_chart(inv_fig, use_container_width=True)

            st.markdown("**成品效果模拟：**")
            sim_col1, sim_col2, sim_col3, sim_col4 = st.columns(4)
            patterns = [
                ('条纹', 'stripes'),
                ('棋盘格', 'checker'),
                ('渐变', 'gradient'),
                ('费尔岛', 'fairisle')
            ]
            display_colors = inv_colors if inv_colors else scheme_data['target_colors']
            for (pname, ptype), scol in zip(patterns, [sim_col1, sim_col2, sim_col3, sim_col4]):
                with scol:
                    st.markdown(f"**{pname}**")
                    sim_buf = simulate_knit_pattern(display_colors, pattern_type=ptype, width=200, height=150)
                    if sim_buf:
                        st.image(sim_buf, caption=pname, use_column_width=True)

            st.markdown("---")


def render_project_matching(df, selected_schemes):
    st.markdown('<div class="section-header">💡 编织项目匹配度分析</div>', unsafe_allow_html=True)

    color_options = df['color_name'].tolist()
    hex_options = df['color_hex'].tolist()
    display_options = [f"{name} ({hex_code})" if hex_code else name for name, hex_code in zip(color_options, hex_options)]

    selected_idx = st.selectbox(
        "选择主色分析项目匹配度",
        range(len(display_options)),
        format_func=lambda i: display_options[i],
        key="project_match_select"
    )
    selected_row = df.iloc[selected_idx]

    schemes = generate_color_schemes(selected_row, df, scheme_types=selected_schemes if selected_schemes else None)

    col_radar, col_info = st.columns([2, 1])
    with col_radar:
        radar_fig = plot_project_match_radar(schemes)
        st.plotly_chart(radar_fig, use_container_width=True)

    with col_info:
        st.markdown("**推荐编织项目：**")
        all_matches = []
        for sk, sv in schemes.items():
            matches = sv.get('inventory_matches', [])
            projects = recommend_project_patterns(matches)
            for p in projects:
                p['scheme'] = sv['name']
                p['color_count'] = len(matches)
                all_matches.append(p)

        if all_matches:
            seen = set()
            unique_projects = []
            for p in all_matches:
                if p['name'] not in seen:
                    seen.add(p['name'])
                    unique_projects.append(p)

            for p in unique_projects[:5]:
                difficulty_color = {
                    '简单': '#27AE60',
                    '中等': '#F39C12',
                    '困难': '#E74C3C'
                }.get(p['difficulty'], '#3498DB')

                st.markdown(f"""
                <div style="background: #FFFAF0; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {difficulty_color};">
                    <div style="font-weight: bold; font-size: 1rem; color: #5D4037;">{p['name']}</div>
                    <div style="font-size: 0.85rem; color: #888;">
                        难度: <span style="color: {difficulty_color}; font-weight: bold;">{p['difficulty']}</span>
                        &nbsp;|&nbsp; 用色: {p['color_count']}色
                    </div>
                    <div style="font-size: 0.85rem; color: #666; margin-top: 4px;">{p['description']}</div>
                    <div style="font-size: 0.8rem; color: #3498DB; margin-top: 4px;">适合: {p['scheme']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暂无推荐项目，请选择有HEX值的颜色")

    st.markdown('<div class="section-header">🎯 按项目筛选线材</div>', unsafe_allow_html=True)
    project_filter = st.selectbox(
        "选择要制作的项目类型",
        ['全部', '围巾', '毛衣', '玩偶', '毯子', '小件装饰']
    )

    filtered = get_material_recommendations(df, None if project_filter == '全部' else project_filter)
    if len(filtered) > 0:
        display_filtered = filtered[[c for c in ['color_name', 'color_family', 'material', 'thickness', 'quantity'] if c in filtered.columns]].copy()
        display_filtered.columns = ['颜色名称', '色系', '材质', '粗细', '数量']
        st.dataframe(display_filtered, use_container_width=True, hide_index=True)
    else:
        st.warning("未找到匹配的线材")


def render_inventory_optimization(df, report, long_unused):
    st.markdown('<div class="section-header">🔧 库存优化中心</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("长期未使用颜色数", report['overview'].get('long_unused_count', 0))
    with col2:
        st.metric("长期未使用总数量", report['overview'].get('long_unused_quantity', 0))
    with col3:
        st.metric("占用资金价值", f"¥{report['overview'].get('long_unused_value', 0):.1f}")

    st.markdown('<div class="section-header">📋 优化建议清单</div>', unsafe_allow_html=True)
    actions = generate_optimization_actions(report)

    for action in actions:
        priority_class = {
            '高': 'action-high',
            '中': 'action-medium',
            '低': 'action-low'
        }.get(action['priority'], 'action-low')

        st.markdown(f"""
        <div class="{priority_class}">
            <div style="font-weight: bold;">
                【{action['priority']}优先级】{action['type']}: {action['target']}
                <span style="color: #888; font-weight: normal; font-size: 0.9rem;">
                    &nbsp; 库存数量: {action['quantity']}
                </span>
            </div>
            <div style="font-size: 0.9rem; color: #555; margin-top: 4px;">{action['detail']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">🧵 长期未使用线材消耗方案</div>', unsafe_allow_html=True)

    if len(long_unused) == 0:
        st.success("✅ 没有长期未使用的线材，库存管理良好！")
    else:
        plans = build_consumption_plan(long_unused, df, top_n=5)

        for i, plan in enumerate(plans):
            with st.expander(f"📌 方案 {i+1}: {plan['color_name']} ({plan['unused_category']}) - 库存 {plan['quantity']}", expanded=(i == 0)):
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    if plan.get('color_hex'):
                        st.markdown(f"""
                        <div style="width:100%; height:100px; background:{plan['color_hex']}; border-radius:8px; border:2px solid #ddd;"></div>
                        """, unsafe_allow_html=True)
                    st.markdown(f"**色系**: {plan['color_family']}")
                    st.markdown(f"**材质**: {plan['material']}")

                with col_b:
                    st.markdown("**💡 消耗建议：**")
                    for s in plan['suggestions']:
                        st.markdown(f"- {s}")

                    if plan['schemes']:
                        st.markdown("**🎨 搭配方案：**")
                        for sk, sv in list(plan['schemes'].items())[:2]:
                            inv_colors = []
                            for m in sv.get('inventory_matches', []):
                                if m.get('color_hex'):
                                    inv_colors.append(m['color_hex'])
                            if inv_colors:
                                sw = plot_color_swatch(inv_colors, title=sv['name'])
                                if sw:
                                    st.plotly_chart(sw, use_container_width=True)

                    if plan.get('recommended_projects'):
                        st.markdown("**🧶 推荐项目：**")
                        for p in plan['recommended_projects']:
                            st.markdown(f"- **{p['name']}** ({p['difficulty']}): {p['description']}")

    with st.expander("📋 长期未使用线材完整列表"):
        if len(long_unused) > 0:
            display_cols = [c for c in ['color_name', 'color_family', 'material', 'quantity', 'days_unused', 'unused_category'] if c in long_unused.columns]
            display_df = long_unused[display_cols].copy()
            col_map = {
                'color_name': '颜色名称',
                'color_family': '色系',
                'material': '材质',
                'quantity': '数量',
                'days_unused': '未使用天数',
                'unused_category': '分类'
            }
            display_df.columns = [col_map[c] for c in display_cols]
            st.dataframe(display_df, use_container_width=True, hide_index=True)


def main():
    uploaded_file, use_sample, selected_schemes, days_threshold = sidebar_section()

    df = load_data(uploaded_file, use_sample, days_threshold)

    if df is None:
        st.markdown('<div class="main-header">🧶 手工编织线材颜色搭配与库存优化分析台</div>', unsafe_allow_html=True)
        st.info("👈 请在左侧上传线材库存 CSV 文件，或勾选「使用示例数据」开始体验")

        st.markdown("---")
        st.markdown("### ✨ 功能亮点")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**📊 库存可视化**")
            st.caption("色系分布饼图、库存堆积柱状图、多层级对比分析")
        with col2:
            st.markdown("**🎨 智能配色**")
            st.caption("互补色、邻近色、三角色等多种色彩理论搭配")
        with col3:
            st.markdown("**🧵 成品模拟**")
            st.caption("条纹、棋盘格、渐变、费尔岛等编织效果预览")
        with col4:
            st.markdown("**🔧 库存优化**")
            st.caption("冗余/短缺识别、长期未使用分析、消耗方案推荐")
        return

    render_dashboard(df, selected_schemes, days_threshold)


if __name__ == "__main__":
    main()
