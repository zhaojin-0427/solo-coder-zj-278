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
    simulate_knit_pattern,
    plot_pre_post_replenishment_preview,
    plot_multi_project_metrics_summary
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
from multi_project_analyzer import (
    ProjectRequirement,
    PROJECT_YARN_REQUIREMENTS,
    PROJECT_SIZE_OPTIONS,
    PRIORITY_WEIGHTS,
    aggregate_project_analysis,
    calculate_long_unused_consumption_potential,
    export_report_csv
)
from multi_project_strategy import (
    compute_optimal_allocation,
    compare_strategies,
    STRATEGY_NAMES
)
from multi_project_visualizations import (
    plot_project_feasibility_radar,
    plot_inventory_change_comparison,
    plot_budget_allocation,
    plot_strategy_comparison_bar,
    plot_conflict_heatmap,
    plot_replenishment_priority,
    plot_long_unused_consumption_gauge,
    plot_color_reuse_sunburst,
    plot_project_color_allocation
)
from historical_data_analyzer import (
    load_and_validate_history,
    build_experience_library,
    SEASON_THEMES,
    STYLE_PROFILES
)
from series_strategy_planner import (
    SeriesConfig,
    SeriesProject,
    SERIES_STRATEGY_NAMES,
    run_series_strategy,
    compare_series_strategies,
    export_series_report_csv,
    PROJECT_YARN_REQUIREMENTS as SERIES_PROJECT_REQUIREMENTS,
    PROJECT_SIZE_OPTIONS as SERIES_SIZE_OPTIONS
)
from series_visualizer import (
    plot_series_color_consistency,
    plot_series_inventory_change,
    plot_series_budget_allocation,
    plot_series_strategy_comparison,
    plot_series_replenishment_priority,
    plot_long_unused_contribution_gauge,
    plot_history_similarity_radar,
    plot_series_metrics_summary,
    plot_shared_yarn_sunburst
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
    .project-card {
        background: linear-gradient(135deg, #FFFAF0 0%, #FFF8DC 100%);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #DEB887;
        margin-bottom: 1rem;
    }
    .strategy-card {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #1976D2;
        margin-bottom: 0.8rem;
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

        st.markdown("### 📜 历史项目数据")
        history_file = st.file_uploader(
            "上传历史项目记录 CSV（可选）",
            type=['csv'],
            help="CSV列包含: project_name, project_type, completion_date, color_name, color_hex, material, quantity_used, effect_rating, customer_feedback"
        )

        st.markdown("---")
        st.markdown("## 📋 CSV 格式说明")
        with st.expander("查看库存格式"):
            st.code("""
color_name,quantity,color_hex,material,thickness,last_used_date,price
大红色,10,#E74C3C,羊毛,中粗,2025-03-15,25.0
天蓝色,8,#3498DB,棉,中,2024-11-20,18.0
柠檬黄,5,#F1C40F,腈纶,细,2025-01-10,12.0
            """, language="csv")
        with st.expander("查看历史项目格式"):
            st.code("""
project_name,project_type,completion_date,color_name,color_hex,material,quantity_used,effect_rating,customer_feedback
春日围巾系列,围巾,2025-03-15,樱花粉,#FFB6C1,羊毛,3,5,客户非常满意
夏日海滩毯,毯子,2024-08-20,海洋蓝,#00CED1,棉,8,4,色彩清新
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

    return uploaded_file, history_file, use_sample, selected_schemes, days_threshold


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


def render_dashboard(df, selected_schemes, days_threshold, history_df=None, experience_library=None):
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

    if experience_library and experience_library.get('total_projects', 0) > 0:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #E8F8F5 0%, #D5F5E3 100%); padding: 12px; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #27AE60;">
            <b style="color: #1E8449;">📚 经验库已加载：</b>
            共 <b>{experience_library['total_projects']}</b> 个历史项目，
            <b>{len(experience_library.get('successful_combinations', []))}</b> 个高评分成功案例可用于参考
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 库存可视化分析",
        "🎨 颜色搭配推荐",
        "💡 编织项目匹配",
        "🔧 库存优化中心",
        "📋 多项目规划与补货决策",
        "🌸 季节胶囊系列企划中心"
    ])

    with tab1:
        render_inventory_analysis(df, stats, report)

    with tab2:
        render_color_matching(df, selected_schemes)

    with tab3:
        render_project_matching(df, selected_schemes)

    with tab4:
        render_inventory_optimization(df, report, long_unused)

    with tab5:
        render_multi_project_planning(df, days_threshold)

    with tab6:
        render_season_capsule_planning(df, days_threshold, experience_library)


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


def render_multi_project_planning(df, days_threshold):
    st.markdown('<div class="section-header">📋 多项目编织规划与补货决策中心</div>', unsafe_allow_html=True)

    if 'projects' not in st.session_state:
        st.session_state.projects = []
    if 'project_id_counter' not in st.session_state:
        existing_ids = [p.project_id for p in st.session_state.projects]
        max_num = 0
        for pid in existing_ids:
            try:
                num = int(pid.replace('P', ''))
                max_num = max(max_num, num)
            except ValueError:
                pass
        st.session_state.project_id_counter = max_num + 1

    with st.expander("➕ 添加新项目", expanded=True):
        render_project_creation_form(df)

    if not st.session_state.projects:
        st.info("👆 请先添加至少一个编织项目，系统将自动进行综合分析与补货决策")
        return

    render_project_list_editor(df)

    st.markdown('<div class="section-header">🔬 跨项目综合分析视图</div>', unsafe_allow_html=True)

    projects = st.session_state.projects

    analysis_result = aggregate_project_analysis(projects, df)
    summary = analysis_result['summary']

    metrics_fig = plot_multi_project_metrics_summary(summary)
    st.plotly_chart(metrics_fig, use_container_width=True)

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        radar_fig = plot_project_feasibility_radar(analysis_result['feasibilities'])
        st.plotly_chart(radar_fig, use_container_width=True)

    with col_a2:
        long_unused_potential = calculate_long_unused_consumption_potential(
            df, projects, analysis_result['feasibilities'], days_threshold
        )
        gauge_fig = plot_long_unused_consumption_gauge(long_unused_potential)
        st.plotly_chart(gauge_fig, use_container_width=True)

        st.markdown(f"""
        <div style="margin-top: 10px; padding: 12px; background: #E8F8F5; border-radius: 8px;">
            <div style="font-weight: bold; color: #27AE60;">📦 长期未使用线材消耗潜力</div>
            <div style="font-size: 0.9rem; margin-top: 8px;">
                可消耗: <b>{long_unused_potential.get('consumable_count', 0)}</b> 种颜色
                共 <b>{long_unused_potential.get('consumable_quantity', 0)}</b> 卷
                释放资金 <b>¥{long_unused_potential.get('locked_value_saved', 0):.1f}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        reuse_info = analysis_result['reuse_efficiency']
        if reuse_info.get('reusable_colors'):
            sunburst_fig = plot_color_reuse_sunburst(reuse_info)
            st.plotly_chart(sunburst_fig, use_container_width=True)

    with col_b2:
        project_ids = [p.project_id for p in projects]
        conflicts = analysis_result['conflicts']
        if len(project_ids) >= 2:
            conflict_fig = plot_conflict_heatmap(conflicts, project_ids)
            st.plotly_chart(conflict_fig, use_container_width=True)

            if conflicts:
                st.markdown("**⚠️ 检测到的线材冲突：**")
                for c in conflicts[:5]:
                    sev_color = {'高': '#E74C3C', '中': '#F39C12', '低': '#3498DB'}.get(c['severity'], '#95A5A6')
                    st.markdown(f"""
                    <div style="padding: 8px; background: #FFF4E6; border-radius: 5px; border-left: 4px solid {sev_color}; margin-bottom: 6px;">
                        <b style="color: {sev_color};">[{c['severity']}]</b>
                        {c['project_1']} ↔ {c['project_2']}：
                        {c['conflict_color']} 短缺 {c['shortage']}
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">🎯 最优分配与补货策略</div>', unsafe_allow_html=True)

    strategy_options = list(STRATEGY_NAMES.keys())
    strategy_labels = list(STRATEGY_NAMES.values())

    selected_strategy_label = st.radio(
        "选择分配策略：",
        strategy_labels,
        horizontal=True,
        help="优先消耗库存：最大化消耗现有库存特别是长期未使用的线材；最少补货成本：最小化补货金额；综合色彩协调度最高：优先保证配色效果"
    )
    selected_strategy = strategy_options[strategy_labels.index(selected_strategy_label)]

    compare_all = st.checkbox("同时对比三种策略效果", value=False)

    if compare_all:
        comparison_result = compare_strategies(projects, analysis_result, df, days_threshold)
        comp_fig = plot_strategy_comparison_bar(comparison_result['comparison'])
        st.plotly_chart(comp_fig, use_container_width=True)

        st.markdown("**📊 三种策略对比详情：**")
        comp_df = comparison_result['comparison'].copy()
        comp_df_display = comp_df.rename(columns={
            'strategy_name': '策略名称',
            'total_replenish_cost': '补货总成本(¥)',
            'total_replenish_qty': '补货总量',
            'average_harmony_score': '平均色彩协调度',
            'average_long_unused_score': '库存消耗得分',
            'color_reuse_score': '颜色复用分'
        }).drop(columns=['strategy_code'])
        st.dataframe(comp_df_display, use_container_width=True, hide_index=True)

        allocation_result = comparison_result['strategy_results'][selected_strategy]
    else:
        allocation_result = compute_optimal_allocation(
            projects, analysis_result, df, selected_strategy, days_threshold
        )

    st.markdown(f"### 当前策略：{STRATEGY_NAMES[selected_strategy]}")

    alloc_summary = allocation_result['summary']
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.metric("库存消耗成本", f"¥{alloc_summary.get('total_allocation_cost', 0):.1f}")
    with sc2:
        st.metric("补货总成本", f"¥{alloc_summary.get('total_replenish_cost', 0):.1f}")
    with sc3:
        st.metric("补货总量", f"{alloc_summary.get('total_replenish_qty', 0):.1f}")
    with sc4:
        st.metric("平均色彩协调度", f"{alloc_summary.get('average_harmony_score', 0):.1f}")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        inv_before = alloc_summary.get('inventory_before', {})
        inv_after = alloc_summary.get('inventory_after', {})
        inv_change_fig = plot_inventory_change_comparison(inv_before, inv_after)
        st.plotly_chart(inv_change_fig, use_container_width=True)

    with col_c2:
        budget_fig = plot_budget_allocation(allocation_result.get('allocations', {}))
        st.plotly_chart(budget_fig, use_container_width=True)

    st.markdown('<div class="section-header">📦 各项目分配详情与配色预览</div>', unsafe_allow_html=True)

    allocations = allocation_result.get('allocations', {})
    for project in projects:
        pid = project.project_id
        alloc = allocations.get(pid, {})
        feasibility = analysis_result['feasibilities'].get(pid, {})

        with st.expander(f"🎨 {pid} - {project.project_type} ({project.target_size}) | 优先级: {project.delivery_priority}", expanded=True):
            pc1, pc2 = st.columns([1, 2])
            with pc1:
                st.markdown(f"""
                <div class="project-card">
                    <div style="font-weight: bold; font-size: 1.1rem;">{project.project_type}</div>
                    <div style="margin-top: 8px;">
                        <b>尺寸:</b> {project.target_size}<br>
                        <b>用色数:</b> {project.color_count}<br>
                        <b>优先级:</b> {project.delivery_priority}<br>
                        <b>可完成度:</b> <span style="color: #27AE60; font-weight: bold;">{feasibility.get('feasibility_score', 0)}%</span><br>
                        <b>状态:</b> {feasibility.get('status', '')}<br>
                        <b>色彩协调:</b> {alloc.get('harmony_score', 0)}<br>
                        <b>库存消耗分:</b> {alloc.get('long_unused_consumption_score', 0)}
                    </div>
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #DEB887;">
                        <b>库存消耗:</b> ¥{alloc.get('total_allocated_cost', 0):.1f}<br>
                        <b>补货成本:</b> ¥{alloc.get('total_replenish_cost', 0):.1f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with pc2:
                allocated_colors = alloc.get('allocated_colors', [])
                if allocated_colors:
                    preview_fig = plot_pre_post_replenishment_preview(
                        allocated_colors,
                        allocated_colors,
                        project_type=project.project_type
                    )
                    st.plotly_chart(preview_fig, use_container_width=True)

                    color_alloc_fig = plot_project_color_allocation(
                        alloc, title=f"{pid} 颜色分配方案"
                    )
                    if color_alloc_fig:
                        st.plotly_chart(color_alloc_fig, use_container_width=True)

            if allocated_colors:
                st.markdown("**分配明细表：**")
                alloc_detail = pd.DataFrame(allocated_colors)
                display_cols = ['color_name', 'color_family', 'material', 'thickness',
                                'allocated_quantity', 'replenish_quantity', 'total_needed', 'price']
                available_cols = [c for c in display_cols if c in alloc_detail.columns]
                display_df = alloc_detail[available_cols].copy()
                display_df.columns = ['颜色名称', '色系', '材质', '粗细', '库存分配', '需补货', '总需求', '单价']
                st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">🛒 智能补货推荐清单</div>', unsafe_allow_html=True)

    replenishment = allocation_result.get('replenishment', pd.DataFrame())
    if len(replenishment) == 0:
        st.success("🎉 恭喜！现有库存足以完成所有项目，无需补货")
    else:
        rep_fig = plot_replenishment_priority(replenishment)
        st.plotly_chart(rep_fig, use_container_width=True)

        st.markdown("**补货详细清单（已按综合优先级排序）：**")
        rep_display = replenishment.copy()
        cols_available = [c for c in ['project_id', 'project_type', 'color_name', 'color_family',
                                       'material', 'thickness', 'shortage', 'unit_price',
                                       'estimated_cost', 'priority', 'composite_score'] if c in rep_display.columns]
        rep_display = rep_display[cols_available]
        col_names = {
            'project_id': '项目ID', 'project_type': '项目类型',
            'color_name': '颜色名称', 'color_family': '色系',
            'material': '材质', 'thickness': '粗细',
            'shortage': '补货数量', 'unit_price': '单价',
            'estimated_cost': '预计成本', 'priority': '优先级',
            'composite_score': '综合优先级分'
        }
        rep_display.columns = [col_names[c] for c in cols_available]
        st.dataframe(rep_display, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">📥 导出报告</div>', unsafe_allow_html=True)

    csv_content = export_report_csv(analysis_result, allocation_result)

    col_d1, col_d2 = st.columns([3, 1])
    with col_d1:
        st.download_button(
            label="📥 下载完整分析报告 (CSV)",
            data=csv_content,
            file_name=f"多项目规划报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_d2:
        st.info("报告包含：项目分配结果、补货建议、库存变化摘要")


def render_project_creation_form(df):
    col1, col2 = st.columns(2)

    with col1:
        project_types = list(PROJECT_YARN_REQUIREMENTS.keys())
        project_type = st.selectbox("项目类型", project_types, key="new_project_type")

        size_options = PROJECT_SIZE_OPTIONS.get(project_type, ['中号'])
        target_size = st.selectbox("目标尺寸", size_options, key="new_project_size")

        color_count = st.slider("预计用色数", min_value=2, max_value=6, value=3, key="new_color_count")

        material_options = sorted(df['material'].unique().tolist()) if 'material' in df.columns else []
        material_restrictions = st.multiselect(
            "材质限制（可选，不选则不限制）",
            material_options,
            key="new_material_restrictions"
        )

    with col2:
        color_options = df['color_name'].tolist()
        hex_options = df['color_hex'].tolist()
        display_options = [f"{name} ({hex_code})" if hex_code else name for name, hex_code in zip(color_options, hex_options)]

        primary_idx = st.selectbox(
            "主色偏好（可选）",
            range(-1, len(display_options)),
            format_func=lambda i: "无特别偏好" if i < 0 else display_options[i],
            key="new_primary_color"
        )

        if primary_idx >= 0:
            primary_color_preference = color_options[primary_idx]
            primary_color_hex = hex_options[primary_idx]
        else:
            primary_color_preference = None
            primary_color_hex = None

        priority_options = list(PRIORITY_WEIGHTS.keys())
        delivery_priority = st.selectbox(
            "交付优先级",
            priority_options,
            index=priority_options.index('中'),
            key="new_priority"
        )

        budget_limit = st.number_input(
            "预算上限（元，0表示不限制）",
            min_value=0.0, max_value=10000.0, value=0.0, step=50.0,
            key="new_budget"
        )

    if st.button("➕ 添加到项目列表", use_container_width=True, type="primary"):
        pid_num = st.session_state.project_id_counter
        pid = f"P{pid_num:03d}"
        st.session_state.project_id_counter += 1
        project = ProjectRequirement(
            project_id=pid,
            project_type=project_type,
            target_size=target_size,
            primary_color_preference=primary_color_preference,
            primary_color_hex=primary_color_hex,
            material_restrictions=material_restrictions if material_restrictions else None,
            budget_limit=budget_limit if budget_limit > 0 else None,
            delivery_priority=delivery_priority,
            color_count=color_count
        )
        st.session_state.projects.append(project)
        st.success(f"✅ 项目 {pid} ({project_type}) 已添加！")


def render_project_list_editor(df):
    st.markdown(f"**当前共 {len(st.session_state.projects)} 个项目**")

    for i, project in enumerate(st.session_state.projects):
        col1, col2, col3 = st.columns([4, 1, 1])

        with col1:
            primary_info = f"主色: {project.primary_color_preference}" if project.primary_color_preference else "无主色偏好"
            material_info = f"材质: {', '.join(project.material_restrictions)}" if project.material_restrictions else "材质: 不限"
            budget_info = f"预算: ¥{project.budget_limit}" if project.budget_limit else "预算: 不限"

            st.markdown(f"""
            <div class="project-card">
                <b>{project.project_id}</b> - {project.project_type} ({project.target_size})
                &nbsp;|&nbsp; 优先级: <b>{project.delivery_priority}</b>
                &nbsp;|&nbsp; 用色: {project.color_count}色
                <br>
                <span style="color: #666; font-size: 0.9rem;">
                    {primary_info} &nbsp;|&nbsp; {material_info} &nbsp;|&nbsp; {budget_info}
                </span>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            if st.button("⬆️ 上移", key=f"up_{i}", disabled=(i == 0)):
                st.session_state.projects[i], st.session_state.projects[i - 1] = \
                    st.session_state.projects[i - 1], st.session_state.projects[i]
                st.rerun()

        with col3:
            if st.button("🗑️ 删除", key=f"del_{i}"):
                st.session_state.projects.pop(i)
                st.rerun()

    if st.button("清空所有项目", type="secondary"):
        st.session_state.projects = []
        st.session_state.project_id_counter = 1
        st.rerun()


def render_season_capsule_planning(df, days_threshold, experience_library=None):
    st.markdown('<div class="section-header">🌸 季节胶囊系列编织企划与配方回溯中心</div>', unsafe_allow_html=True)

    if 'series_config' not in st.session_state:
        st.session_state.series_config = None
    if 'series_projects' not in st.session_state:
        st.session_state.series_projects = []
    if 'series_project_counter' not in st.session_state:
        st.session_state.series_project_counter = 1
    if 'series_result' not in st.session_state:
        st.session_state.series_result = None
    if 'series_comparison' not in st.session_state:
        st.session_state.series_comparison = None

    st.markdown("""
    <div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFE4E1 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border-left: 4px solid #DEB887;">
        <b>💡 使用说明：</b>先设置系列整体参数（风格、季节、预算等），再添加系列内各单品项目，系统将自动生成色板、配方、共享用线方案及三套策略对比结果。
    </div>
    """, unsafe_allow_html=True)

    with st.expander("⚙️ 系列基础参数配置", expanded=True):
        col_cfg1, col_cfg2 = st.columns(2)

        with col_cfg1:
            series_name = st.text_input("系列名称", value="2026春夏胶囊系列", key="series_name_input")
            target_style = st.selectbox(
                "目标风格",
                list(STYLE_PROFILES.keys()),
                index=0,
                key="series_style_input"
            )
            season_theme = st.selectbox(
                "季节主题",
                list(SEASON_THEMES.keys()),
                index=0,
                key="series_season_input"
            )
            st.caption(f"**{season_theme}关键词**: {', '.join(SEASON_THEMES[season_theme]['keywords'])}")

        with col_cfg2:
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                budget_min = st.number_input("预算下限 (¥)", min_value=0.0, max_value=50000.0, value=200.0, step=50.0, key="series_budget_min")
            with col_b2:
                budget_max = st.number_input("预算上限 (¥)", min_value=0.0, max_value=50000.0, value=2000.0, step=50.0, key="series_budget_max")

            reuse_rate_target = st.slider(
                "跨项目用线复用率目标 (%)",
                min_value=20, max_value=100, value=60, step=5,
                key="series_reuse_target"
            )

            material_options = sorted(df['material'].unique().tolist()) if 'material' in df.columns else []
            material_taboos = st.multiselect(
                "材质禁忌（不可使用的材质）",
                material_options,
                key="series_material_taboos"
            )

    with st.expander("➕ 添加系列单品项目", expanded=len(st.session_state.series_projects) == 0):
        col_sp1, col_sp2 = st.columns(2)

        with col_sp1:
            sp_types = list(SERIES_PROJECT_REQUIREMENTS.keys())
            sp_type = st.selectbox("单品类型", sp_types, key="sp_type_input")
            sp_size_options = SERIES_SIZE_OPTIONS.get(sp_type, ['中号'])
            sp_size = st.selectbox("目标尺寸", sp_size_options, key="sp_size_input")
            sp_color_count = st.slider("预计用色数", min_value=2, max_value=6, value=3, key="sp_color_count")
            sp_role = st.selectbox(
                "系列中角色",
                ['核心', '主款', '搭配款', '点缀款'],
                index=1,
                key="sp_role_input"
            )

        with col_sp2:
            sp_delivery = st.number_input(
                "交付批次顺序 (1=最早)",
                min_value=1, max_value=10, value=max(1, len(st.session_state.series_projects) + 1),
                step=1,
                key="sp_delivery_input"
            )

            color_options = df['color_name'].tolist()
            hex_options = df['color_hex'].tolist()
            display_options = [f"{name} ({hex_code})" if hex_code else name for name, hex_code in zip(color_options, hex_options)]
            sp_primary_idx = st.selectbox(
                "主色偏好（可选）",
                range(-1, len(display_options)),
                format_func=lambda i: "无特别偏好" if i < 0 else display_options[i],
                key="sp_primary_input"
            )
            if sp_primary_idx >= 0:
                sp_primary_color = color_options[sp_primary_idx]
                sp_primary_hex = hex_options[sp_primary_idx]
            else:
                sp_primary_color = None
                sp_primary_hex = None

            sp_mat_restrict = st.multiselect(
                "材质要求（仅使用这些材质，不选则不限）",
                material_options,
                key="sp_mat_restrict"
            )

        if st.button("➕ 添加到系列", use_container_width=True, type="primary", key="sp_add_btn"):
            sp_num = st.session_state.series_project_counter
            sp_id = f"S{sp_num:03d}"
            st.session_state.series_project_counter += 1
            sp = SeriesProject(
                series_project_id=sp_id,
                project_type=sp_type,
                target_size=sp_size,
                delivery_order=sp_delivery,
                color_count=sp_color_count,
                material_restrictions=sp_mat_restrict if sp_mat_restrict else None,
                primary_color_preference=sp_primary_color,
                primary_color_hex=sp_primary_hex,
                role_in_series=sp_role
            )
            st.session_state.series_projects.append(sp)
            st.success(f"✅ 单品 {sp_id} ({sp_type}) 已添加到系列！")
            st.rerun()

    if st.session_state.series_projects:
        st.markdown(f"**当前系列共 {len(st.session_state.series_projects)} 个单品项目**")
        for i, sp in enumerate(st.session_state.series_projects):
            col_spl, col_spu, col_spd = st.columns([5, 1, 1])
            with col_spl:
                primary_info = f"主色: {sp.primary_color_preference}" if sp.primary_color_preference else "无主色偏好"
                mat_info = f"材质: {', '.join(sp.material_restrictions)}" if sp.material_restrictions else "材质: 不限"
                st.markdown(f"""
                <div class="project-card">
                    <b>{sp.series_project_id}</b> - {sp.project_type} ({sp.target_size})
                    &nbsp;|&nbsp; 角色: <b>{sp.role_in_series}</b>
                    &nbsp;|&nbsp; 交付批次: <b>第{sp.delivery_order}批</b>
                    &nbsp;|&nbsp; 用色: {sp.color_count}色
                    <br>
                    <span style="color: #666; font-size: 0.9rem;">
                        {primary_info} &nbsp;|&nbsp; {mat_info}
                    </span>
                </div>
                """, unsafe_allow_html=True)
            with col_spu:
                if st.button("⬆️", key=f"sp_up_{i}", disabled=(i == 0)):
                    st.session_state.series_projects[i], st.session_state.series_projects[i - 1] = \
                        st.session_state.series_projects[i - 1], st.session_state.series_projects[i]
                    st.rerun()
            with col_spd:
                if st.button("🗑️", key=f"sp_del_{i}"):
                    st.session_state.series_projects.pop(i)
                    st.rerun()

        if st.button("清空系列所有项目", type="secondary", key="sp_clear_all"):
            st.session_state.series_projects = []
            st.session_state.series_project_counter = 1
            st.session_state.series_result = None
            st.session_state.series_comparison = None
            st.rerun()
    else:
        st.info("👆 请先添加至少一个单品项目到系列中")

    st.markdown("---")
    st.markdown('<div class="section-header">🎯 系列策略生成与对比</div>', unsafe_allow_html=True)

    col_act1, col_act2 = st.columns([1, 1])

    with col_act1:
        strategy_options = list(SERIES_STRATEGY_NAMES.keys())
        strategy_labels = list(SERIES_STRATEGY_NAMES.values())
        selected_strategy_label = st.radio(
            "选择主策略：",
            strategy_labels,
            horizontal=True,
            help="最稳妥交付：优先保证库存充足和交付可靠性；最低补货成本：最小化补货金额；视觉统一性最高：最大化系列整体色彩协调度"
        )
        selected_strategy = strategy_options[strategy_labels.index(selected_strategy_label)]

    with col_act2:
        compare_all = st.checkbox("同时对比三套策略效果", value=True, key="sp_compare_all")
        run_planning = st.button(
            "🚀 生成系列规划方案",
            use_container_width=True,
            type="primary",
            disabled=len(st.session_state.series_projects) == 0,
            key="sp_run_btn"
        )

    if run_planning:
        with st.spinner("正在生成系列规划方案..."):
            series_config = SeriesConfig(
                series_name=series_name,
                target_style=target_style,
                season_theme=season_theme,
                budget_min=budget_min,
                budget_max=budget_max,
                material_taboos=material_taboos if material_taboos else None,
                reuse_rate_target=reuse_rate_target / 100.0,
                series_projects=st.session_state.series_projects
            )
            st.session_state.series_config = series_config

            if compare_all:
                comparison = compare_series_strategies(
                    series_config, df, days_threshold, experience_library
                )
                st.session_state.series_comparison = comparison
                st.session_state.series_result = comparison['strategy_results'][selected_strategy]
            else:
                result = run_series_strategy(
                    series_config, df, selected_strategy, days_threshold, experience_library
                )
                st.session_state.series_result = result
                st.session_state.series_comparison = None

    if st.session_state.series_result is None:
        return

    result = st.session_state.series_result
    summary = result.get('summary', {})
    visual_unity = result.get('visual_unity', {})
    history_sim = result.get('history_similarity', {})
    long_unused_contr = result.get('long_unused_contribution', {})

    metrics_fig = plot_series_metrics_summary(summary)
    st.plotly_chart(metrics_fig, use_container_width=True)

    budget_status = "✅ 预算范围内" if summary.get('budget_within_range', False) else "⚠️ 超出预算"
    reuse_status = "✅ 达标" if summary.get('cross_project_reuse_rate', 0) >= summary.get('reuse_target', 60) else "⚠️ 未达标"
    st.markdown(f"""
    <div style="display: flex; gap: 12px; margin-bottom: 1rem;">
        <div style="flex: 1; background: #E3F2FD; padding: 12px; border-radius: 8px; border-left: 4px solid #1976D2;">
            <b>💰 预算状态：</b>{budget_status} &nbsp;|&nbsp; 总额 ¥{summary.get('total_budget', 0):.1f} (目标 ¥{summary.get('budget_min', 0):.0f}~¥{summary.get('budget_max', 0):.0f})
        </div>
        <div style="flex: 1; background: #E8F8F5; padding: 12px; border-radius: 8px; border-left: 4px solid #27AE60;">
            <b>🔄 复用率：</b>{reuse_status} &nbsp;|&nbsp; {summary.get('cross_project_reuse_rate', 0):.1f}% (目标 {summary.get('reuse_target', 0):.0f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.series_comparison is not None:
        st.markdown('<div class="section-header">⚖️ 三套策略对比</div>', unsafe_allow_html=True)
        comp_fig = plot_series_strategy_comparison(st.session_state.series_comparison['comparison'])
        st.plotly_chart(comp_fig, use_container_width=True)

        comp_df = st.session_state.series_comparison['comparison'].copy()
        comp_display = comp_df.rename(columns={
            'strategy_name': '策略名称',
            'total_replenish_cost': '补货总成本(¥)',
            'total_budget': '总预算(¥)',
            'visual_unity_score': '视觉统一性',
            'cross_project_reuse_rate': '跨项目复用率(%)',
            'history_similarity': '历史相似度',
            'long_unused_contribution': '滞销贡献(%)',
            'budget_within_range': '预算内'
        }).drop(columns=['strategy_code'])
        st.dataframe(comp_display, use_container_width=True, hide_index=True)

        st.markdown("---")

    st.markdown('<div class="section-header">🎨 系列色板与配色方案</div>', unsafe_allow_html=True)

    col_pal1, col_pal2 = st.columns([2, 1])

    with col_pal1:
        base_palette = result.get('base_palette', [])
        if base_palette:
            st.markdown("**📌 核心基础色板**")
            base_hexes = [c.get('color_hex') for c in base_palette if c.get('color_hex')]
            base_labels = [
                f"{c.get('color_name', '')}\n{c.get('role', '')}\n库存:{c.get('quantity', 0)}"
                for c in base_palette
            ]
            if base_hexes:
                sw_fig = plot_color_swatch(base_hexes, labels=base_labels, title=f'{summary.get("series_name", "")} 基础色板')
                if sw_fig:
                    st.plotly_chart(sw_fig, use_container_width=True)

            pal_df = pd.DataFrame(base_palette)
            display_pal = pal_df[[c for c in [
                'color_name', 'color_family', 'material', 'quantity',
                'price', 'role', 'composite_score'
            ] if c in pal_df.columns]].copy()
            display_pal.columns = ['颜色名称', '色系', '材质', '库存', '单价', '角色', '综合评分']
            st.dataframe(display_pal, use_container_width=True, hide_index=True)

    with col_pal2:
        alt_palettes = result.get('alternative_palettes', [])
        if alt_palettes:
            st.markdown("**🔀 替代配色方案**")
            for alt in alt_palettes:
                with st.expander(f"{alt.get('name', '')} (协调度: {alt.get('harmony_score', '')}, 差异度: {alt.get('difference_from_base', '')}%)"):
                    alt_hexes = [c.get('color_hex') for c in alt.get('colors', []) if c.get('color_hex')]
                    alt_labels = [
                        f"{c.get('color_name', '')}\n{c.get('variation_type', '')}"
                        for c in alt.get('colors', [])
                    ]
                    if alt_hexes:
                        alt_fig = plot_color_swatch(alt_hexes, labels=alt_labels, title=alt.get('name', ''))
                        if alt_fig:
                            st.plotly_chart(alt_fig, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-header">📊 系列整体评估与可视化</div>', unsafe_allow_html=True)

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        radar_fig = plot_history_similarity_radar(history_sim, visual_unity, summary)
        st.plotly_chart(radar_fig, use_container_width=True)

    with col_v2:
        gauge_fig = plot_long_unused_contribution_gauge(long_unused_contr)
        st.plotly_chart(gauge_fig, use_container_width=True)

        st.markdown(f"""
        <div style="margin-top: 10px; padding: 12px; background: #F4ECF7; border-radius: 8px;">
            <div style="font-weight: bold; color: #8E44AD;">📦 长期滞销线材消耗</div>
            <div style="font-size: 0.9rem; margin-top: 8px;">
                可消耗: <b>{long_unused_contr.get('consumed_long_unused_colors', 0)}</b> 种 / 共 <b>{long_unused_contr.get('total_long_unused_colors', 0)}</b> 种
                <br>
                共 <b>{long_unused_contr.get('consumed_quantity', 0)}</b> 卷
                <br>
                释放资金 <b>¥{long_unused_contr.get('value_freed', 0):.1f}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    col_v3, col_v4 = st.columns(2)
    with col_v3:
        consistency_fig = plot_series_color_consistency(result.get('series_plans', {}), base_palette)
        st.plotly_chart(consistency_fig, use_container_width=True)

    with col_v4:
        shared_scheme = result.get('shared_yarn_scheme', {})
        if shared_scheme and shared_scheme.get('shared_colors'):
            sun_fig = plot_shared_yarn_sunburst(shared_scheme)
            st.plotly_chart(sun_fig, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-header">📈 库存变化与资金占用</div>', unsafe_allow_html=True)

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        inv_changes = result.get('inventory_changes', {})
        inv_fig = plot_series_inventory_change(inv_changes)
        st.plotly_chart(inv_fig, use_container_width=True)

    with col_i2:
        budget_fig = plot_series_budget_allocation(result.get('series_plans', {}), summary)
        st.plotly_chart(budget_fig, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-header">🧵 各项目配方与补货明细</div>', unsafe_allow_html=True)

    series_plans = result.get('series_plans', {})
    sorted_plans = sorted(
        series_plans.items(),
        key=lambda x: x[1].get('delivery_order', 99)
    )

    for pid, plan in sorted_plans:
        with st.expander(
            f"🎨 {pid} - {plan.get('project_type', '')} ({plan.get('target_size', '')}) "
            f"| 交付批次: 第{plan.get('delivery_order', 1)}批 | 角色: {plan.get('role_in_series', '')}",
            expanded=True
        ):
            pc1, pc2 = st.columns([1, 2])
            with pc1:
                st.markdown(f"""
                <div class="project-card">
                    <div style="font-weight: bold; font-size: 1.1rem;">{plan.get('project_type', '')}</div>
                    <div style="margin-top: 8px;">
                        <b>尺寸:</b> {plan.get('target_size', '')}<br>
                        <b>用色数:</b> {len(plan.get('selected_colors', []))}<br>
                        <b>交付批次:</b> 第{plan.get('delivery_order', 1)}批<br>
                        <b>可完成度:</b> <span style="color: #27AE60; font-weight: bold;">{plan.get('feasibility_score', 0)}%</span><br>
                        <b>色彩协调:</b> {plan.get('harmony_score', 0)}<br>
                        <b>综合评分:</b> {plan.get('allocation_score', 0)}
                    </div>
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #DEB887;">
                        <b>库存消耗:</b> ¥{plan.get('total_allocated_cost', 0):.1f}<br>
                        <b>补货成本:</b> ¥{plan.get('total_replenish_cost', 0):.1f}<br>
                        <b>共享池分配:</b> {plan.get('from_shared_pool', 0):.1f} 卷
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with pc2:
                sel_colors = plan.get('selected_colors', [])
                if sel_colors:
                    sel_hexes = [c.get('color_hex') for c in sel_colors if c.get('color_hex')]
                    sel_labels = [
                        f"{c.get('color_name', '')}\n需:{c.get('total_needed', 0):.0f} | 补:{c.get('replenish_qty', 0):.0f}"
                        for c in sel_colors
                    ]
                    if sel_hexes:
                        proj_sw = plot_color_swatch(sel_hexes, labels=sel_labels, title=f"{pid} 配色方案")
                        if proj_sw:
                            st.plotly_chart(proj_sw, use_container_width=True)

            if sel_colors:
                st.markdown("**配方明细表：**")
                alloc_detail = pd.DataFrame(sel_colors)
                display_cols = ['color_name', 'color_family', 'material', 'thickness',
                                'quantity', 'total_needed', 'replenish_qty', 'price',
                                'history_confidence', 'history_rating']
                available_cols = [c for c in display_cols if c in alloc_detail.columns]
                display_df = alloc_detail[available_cols].copy()
                col_map = {
                    'color_name': '颜色名称', 'color_family': '色系',
                    'material': '材质', 'thickness': '粗细',
                    'quantity': '可用库存', 'total_needed': '总需求',
                    'replenish_qty': '需补货', 'price': '单价',
                    'history_confidence': '历史置信度', 'history_rating': '历史评分'
                }
                display_df.columns = [col_map[c] for c in available_cols]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">🛒 补货优先级推荐</div>', unsafe_allow_html=True)

    replenishment = result.get('replenishment', pd.DataFrame())
    if len(replenishment) == 0:
        st.success("🎉 恭喜！现有库存足以完成整个系列，无需补货")
    else:
        rep_fig = plot_series_replenishment_priority(replenishment)
        st.plotly_chart(rep_fig, use_container_width=True)

        st.markdown("**补货详细清单（按综合优先级排序）：**")
        rep_display = replenishment.copy()
        cols_available = [c for c in [
            'priority_rank', 'series_project_id', 'project_type', 'delivery_order',
            'color_name', 'color_family', 'material', 'replenish_qty',
            'unit_price', 'estimated_cost', 'composite_score'
        ] if c in rep_display.columns]
        rep_display = rep_display[cols_available]
        col_names = {
            'priority_rank': '优先级排名',
            'series_project_id': '项目ID', 'project_type': '项目类型',
            'delivery_order': '交付批次',
            'color_name': '颜色名称', 'color_family': '色系',
            'material': '材质', 'replenish_qty': '补货数量',
            'unit_price': '单价', 'estimated_cost': '预计成本',
            'composite_score': '综合优先级分'
        }
        rep_display.columns = [col_names[c] for c in cols_available]
        st.dataframe(rep_display, use_container_width=True, hide_index=True)

    if history_sim and history_sim.get('best_match'):
        st.markdown('<div class="section-header">📚 历史成功案例匹配</div>', unsafe_allow_html=True)
        best = history_sim['best_match']
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFE4B5 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border-left: 4px solid #DAA520;">
            <div style="font-weight: bold; font-size: 1.1rem; color: #B8860B;">🏆 最佳匹配历史案例</div>
            <div style="margin-top: 8px;">
                <b>{best.get('project_name', '')}</b> ({best.get('project_type', '')})
                &nbsp;|&nbsp; 相似度: <b style="color: #27AE60;">{best.get('similarity', '')}%</b>
                &nbsp;|&nbsp; 历史评分: <b>{best.get('avg_rating', '')}/5</b>
            </div>
            <div style="font-size: 0.9rem; color: #666; margin-top: 6px;">
                使用材质: {', '.join(best.get('materials', []))}
                {'<br>客户反馈: ' + str(best.get('feedback', '')) if best.get('feedback') else ''}
            </div>
            <div style="margin-top: 8px;">
                <b>季节主题匹配度:</b> {history_sim.get('season_match_score', 0)}%
            </div>
        </div>
        """, unsafe_allow_html=True)

        all_matches = history_sim.get('all_matches', [])
        if len(all_matches) > 1:
            with st.expander("查看更多相似历史案例"):
                match_rows = []
                for m in all_matches[1:6]:
                    match_rows.append({
                        '项目名称': m.get('project_name', ''),
                        '类型': m.get('project_type', ''),
                        '相似度(%)': m.get('similarity', ''),
                        '色彩相似度(%)': m.get('color_similarity', ''),
                        '历史评分': m.get('avg_rating', ''),
                        '材质': ', '.join(m.get('materials', []))
                    })
                if match_rows:
                    st.dataframe(pd.DataFrame(match_rows), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">📥 导出系列报告</div>', unsafe_allow_html=True)

    csv_content = export_series_report_csv(result, experience_library)

    col_exp1, col_exp2 = st.columns([3, 1])
    with col_exp1:
        st.download_button(
            label="📥 下载完整季节胶囊系列规划报告 (CSV)",
            data=csv_content,
            file_name=f"季节胶囊系列_{summary.get('series_name', '')}_{summary.get('strategy', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_exp2:
        st.info("报告包含：系列摘要、基础色板、项目级配方、补货建议、库存变化、历史案例匹配说明")


def main():
    uploaded_file, history_file, use_sample, selected_schemes, days_threshold = sidebar_section()

    df = load_data(uploaded_file, use_sample, days_threshold)

    history_df = None
    experience_library = None
    if history_file is not None:
        history_df, history_warnings = load_and_validate_history(history_file)
        if history_df is not None:
            experience_library = build_experience_library(history_df)
            if history_warnings:
                with st.sidebar:
                    for w in history_warnings:
                        st.warning(w)

    if df is None:
        st.markdown('<div class="main-header">🧶 手工编织线材颜色搭配与库存优化分析台</div>', unsafe_allow_html=True)
        st.info("👈 请在左侧上传线材库存 CSV 文件，或勾选「使用示例数据」开始体验")

        st.markdown("---")
        st.markdown("### ✨ 功能亮点")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
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
        with col5:
            st.markdown("**📋 多项目规划**")
            st.caption("多项目联合规划、智能补货决策、三策略对比")
        with col6:
            st.markdown("**🌸 季节胶囊系列**")
            st.caption("系列级企划、经验库回溯、三策略级联对比")
        return

    render_dashboard(df, selected_schemes, days_threshold, history_df, experience_library)


if __name__ == "__main__":
    main()
