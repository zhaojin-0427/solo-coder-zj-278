import pandas as pd
import numpy as np
from colormath.color_objects import sRGBColor, LabColor, HSLColor, HSVColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000


def get_complementary(hex_color):
    if not hex_color:
        return None
    try:
        rgb = sRGBColor.new_from_rgb_hex(hex_color)
        hsl = convert_color(rgb, HSLColor)
        comp_h = (hsl.hsl_h + 180) % 360
        comp_hsl = HSLColor(comp_h, hsl.hsl_s, hsl.hsl_l)
        comp_rgb = convert_color(comp_hsl, sRGBColor)
        comp_rgb.rgb_r = max(0, min(1, comp_rgb.rgb_r))
        comp_rgb.rgb_g = max(0, min(1, comp_rgb.rgb_g))
        comp_rgb.rgb_b = max(0, min(1, comp_rgb.rgb_b))
        return comp_rgb.get_rgb_hex()
    except Exception:
        return None


def get_analogous(hex_color, num_colors=3, angle_spread=30):
    if not hex_color:
        return []
    try:
        rgb = sRGBColor.new_from_rgb_hex(hex_color)
        hsl = convert_color(rgb, HSLColor)
        colors = []
        total_angle = (num_colors - 1) * angle_spread
        start_h = hsl.hsl_h - total_angle / 2
        for i in range(num_colors):
            h = (start_h + i * angle_spread) % 360
            a_hsl = HSLColor(h, hsl.hsl_s, hsl.hsl_l)
            a_rgb = convert_color(a_hsl, sRGBColor)
            a_rgb.rgb_r = max(0, min(1, a_rgb.rgb_r))
            a_rgb.rgb_g = max(0, min(1, a_rgb.rgb_g))
            a_rgb.rgb_b = max(0, min(1, a_rgb.rgb_b))
            colors.append(a_rgb.get_rgb_hex())
        return colors
    except Exception:
        return []


def get_triadic(hex_color):
    if not hex_color:
        return []
    try:
        rgb = sRGBColor.new_from_rgb_hex(hex_color)
        hsl = convert_color(rgb, HSLColor)
        colors = []
        for offset in [0, 120, 240]:
            h = (hsl.hsl_h + offset) % 360
            t_hsl = HSLColor(h, hsl.hsl_s, hsl.hsl_l)
            t_rgb = convert_color(t_hsl, sRGBColor)
            t_rgb.rgb_r = max(0, min(1, t_rgb.rgb_r))
            t_rgb.rgb_g = max(0, min(1, t_rgb.rgb_g))
            t_rgb.rgb_b = max(0, min(1, t_rgb.rgb_b))
            colors.append(t_rgb.get_rgb_hex())
        return colors
    except Exception:
        return []


def get_split_complementary(hex_color):
    if not hex_color:
        return []
    try:
        rgb = sRGBColor.new_from_rgb_hex(hex_color)
        hsl = convert_color(rgb, HSLColor)
        colors = [hex_color]
        comp_h = (hsl.hsl_h + 180) % 360
        for offset in [-30, 30]:
            h = (comp_h + offset) % 360
            sc_hsl = HSLColor(h, hsl.hsl_s, hsl.hsl_l)
            sc_rgb = convert_color(sc_hsl, sRGBColor)
            sc_rgb.rgb_r = max(0, min(1, sc_rgb.rgb_r))
            sc_rgb.rgb_g = max(0, min(1, sc_rgb.rgb_g))
            sc_rgb.rgb_b = max(0, min(1, sc_rgb.rgb_b))
            colors.append(sc_rgb.get_rgb_hex())
        return colors
    except Exception:
        return []


def get_monochromatic(hex_color, num_shades=5):
    if not hex_color:
        return []
    try:
        rgb = sRGBColor.new_from_rgb_hex(hex_color)
        hsl = convert_color(rgb, HSLColor)
        colors = []
        lightnesses = np.linspace(0.15, 0.85, num_shades)
        for l in lightnesses:
            m_hsl = HSLColor(hsl.hsl_h, hsl.hsl_s, l)
            m_rgb = convert_color(m_hsl, sRGBColor)
            m_rgb.rgb_r = max(0, min(1, m_rgb.rgb_r))
            m_rgb.rgb_g = max(0, min(1, m_rgb.rgb_g))
            m_rgb.rgb_b = max(0, min(1, m_rgb.rgb_b))
            colors.append(m_rgb.get_rgb_hex())
        return colors
    except Exception:
        return []


def get_tetradic(hex_color):
    if not hex_color:
        return []
    try:
        rgb = sRGBColor.new_from_rgb_hex(hex_color)
        hsl = convert_color(rgb, HSLColor)
        colors = []
        for offset in [0, 90, 180, 270]:
            h = (hsl.hsl_h + offset) % 360
            t_hsl = HSLColor(h, hsl.hsl_s, hsl.hsl_l)
            t_rgb = convert_color(t_hsl, sRGBColor)
            t_rgb.rgb_r = max(0, min(1, t_rgb.rgb_r))
            t_rgb.rgb_g = max(0, min(1, t_rgb.rgb_g))
            t_rgb.rgb_b = max(0, min(1, t_rgb.rgb_b))
            colors.append(t_rgb.get_rgb_hex())
        return colors
    except Exception:
        return []


def calculate_color_distance(hex1, hex2):
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


def find_closest_in_inventory(target_hex, inventory_df, exclude_indices=None):
    valid_rows = inventory_df[inventory_df['color_hex'].notna()].copy()
    if exclude_indices is not None and len(exclude_indices) > 0:
        valid_rows = valid_rows[~valid_rows.index.isin(exclude_indices)]

    if len(valid_rows) == 0:
        return None

    valid_rows['distance'] = valid_rows['color_hex'].apply(
        lambda x: calculate_color_distance(target_hex, x)
    )
    valid_rows = valid_rows.sort_values('distance')
    return valid_rows.iloc[0]


def generate_color_schemes(selected_row, inventory_df, scheme_types=None):
    if scheme_types is None:
        scheme_types = ['complementary', 'analogous', 'triadic', 'split_complementary', 'monochromatic']

    hex_color = selected_row.get('color_hex')
    if not hex_color:
        return {}

    schemes = {}
    used_indices = {selected_row.name} if hasattr(selected_row, 'name') else set()

    if 'complementary' in scheme_types:
        comp_hex = get_complementary(hex_color)
        comp_match = find_closest_in_inventory(comp_hex, inventory_df, used_indices)
        schemes['complementary'] = {
            'name': '互补色搭配',
            'description': '色轮上相对180°的颜色，对比强烈，视觉冲击力强',
            'target_colors': [hex_color, comp_hex] if comp_hex else [hex_color],
            'inventory_matches': [selected_row] + ([comp_match] if comp_match is not None else [])
        }
        if comp_match is not None:
            used_indices.add(comp_match.name)

    if 'analogous' in scheme_types:
        ana_hexes = get_analogous(hex_color, num_colors=3, angle_spread=30)
        ana_matches = []
        temp_used = set(used_indices)
        for h in ana_hexes:
            match = find_closest_in_inventory(h, inventory_df, temp_used)
            if match is not None:
                ana_matches.append(match)
                temp_used.add(match.name)
        schemes['analogous'] = {
            'name': '邻近色搭配',
            'description': '色轮上相邻的颜色，和谐自然，过渡柔和',
            'target_colors': ana_hexes,
            'inventory_matches': ana_matches if ana_matches else [selected_row]
        }

    if 'triadic' in scheme_types:
        tri_hexes = get_triadic(hex_color)
        tri_matches = []
        temp_used = set(used_indices)
        for h in tri_hexes:
            match = find_closest_in_inventory(h, inventory_df, temp_used)
            if match is not None:
                tri_matches.append(match)
                temp_used.add(match.name)
        schemes['triadic'] = {
            'name': '三角色搭配',
            'description': '色轮上等距120°的三种颜色，平衡而富有活力',
            'target_colors': tri_hexes,
            'inventory_matches': tri_matches if tri_matches else [selected_row]
        }

    if 'split_complementary' in scheme_types:
        sc_hexes = get_split_complementary(hex_color)
        sc_matches = []
        temp_used = set(used_indices)
        for h in sc_hexes:
            match = find_closest_in_inventory(h, inventory_df, temp_used)
            if match is not None:
                sc_matches.append(match)
                temp_used.add(match.name)
        schemes['split_complementary'] = {
            'name': '分裂互补搭配',
            'description': '基色+互补色两侧的颜色，对比柔和更易搭配',
            'target_colors': sc_hexes,
            'inventory_matches': sc_matches if sc_matches else [selected_row]
        }

    if 'monochromatic' in scheme_types:
        mono_hexes = get_monochromatic(hex_color, num_shades=4)
        mono_matches = []
        temp_used = set(used_indices)
        for h in mono_hexes:
            match = find_closest_in_inventory(h, inventory_df, temp_used)
            if match is not None:
                mono_matches.append(match)
                temp_used.add(match.name)
        schemes['monochromatic'] = {
            'name': '同色系搭配',
            'description': '同一色相不同明度，简约优雅有层次感',
            'target_colors': mono_hexes,
            'inventory_matches': mono_matches if mono_matches else [selected_row]
        }

    return schemes


def recommend_project_patterns(scheme_colors):
    pattern_templates = [
        {
            'name': '渐变条纹围巾',
            'difficulty': '简单',
            'description': '利用同色系或邻近色的深浅变化，编织经典条纹围巾',
            'color_count': '2-4色',
            'best_schemes': ['monochromatic', 'analogous']
        },
        {
            'name': '祖母方格毯',
            'difficulty': '中等',
            'description': '用对比色或三角色搭配钩织方格，再拼接成毯',
            'color_count': '3-5色',
            'best_schemes': ['complementary', 'triadic', 'split_complementary']
        },
        {
            'name': '费尔岛图案毛衣',
            'difficulty': '困难',
            'description': '传统北欧风格，多色提花编织，适合分裂互补或三角色',
            'color_count': '3-6色',
            'best_schemes': ['split_complementary', 'triadic']
        },
        {
            'name': '色块拼接包',
            'difficulty': '简单',
            'description': '几何色块拼接，互补色或对比色效果最佳',
            'color_count': '2-4色',
            'best_schemes': ['complementary', 'split_complementary']
        },
        {
            'name': '彩虹渐变毯子',
            'difficulty': '中等',
            'description': '利用全色系渐变，适合邻近色或同色系扩展',
            'color_count': '5+色',
            'best_schemes': ['analogous', 'monochromatic']
        }
    ]

    n_colors = len(scheme_colors)
    suitable = []

    for pt in pattern_templates:
        count_range = pt['color_count']
        if '+' in count_range:
            min_count = int(count_range.replace('+色', ''))
            if n_colors >= min_count:
                suitable.append(pt)
        else:
            parts = count_range.replace('色', '').split('-')
            min_c, max_c = int(parts[0]), int(parts[1])
            if min_c <= n_colors <= max_c:
                suitable.append(pt)

    return suitable


def get_consumption_suggestions(color_family, material, quantity):
    suggestions = []

    project_map = {
        '红色系': ['红色玫瑰花束装饰', '爱心图案抱枕', '红色小物挂饰'],
        '橙色系': ['南瓜万圣节装饰', '胡萝卜造型玩偶', '橙色收纳篮'],
        '黄色系': ['向日葵花束', '小蜜蜂玩偶', '柠檬杯垫套装'],
        '绿色系': ['多肉植物盆栽套', '四叶草幸运挂件', '树叶图案毯子'],
        '青色系': ['海洋主题挂毯', '青蛙玩偶', '湖水蓝围巾'],
        '蓝色系': ['天空主题毯', '鲸鱼玩偶', '海军风条纹衫'],
        '紫色系': ['薰衣草香包', '葡萄串装饰', '梦幻紫色披肩'],
        '粉色系': ['樱花花环', '小猪玩偶', '粉色宝宝毯'],
        '白色': ['雪花挂饰套装', '婚礼手捧花', '白色蕾丝边饰'],
        '黑色': ['黑猫玩偶', '黑灰格纹毯', '黑色小礼帽'],
        '灰色': ['龙猫玩偶', '极简风杯垫', '灰色北欧风抱枕'],
        '米色': ['麦穗装饰', '亚麻风桌垫', '素色收纳筐'],
        '棕色': ['小熊玩偶', '森林动物系列', '原木风杯垫'],
        '中性色': ['百搭基础款围巾', '素色拖鞋', '家居装饰小件']
    }

    family = color_family if color_family in project_map else '中性色'
    base_projects = project_map[family]

    if quantity >= 10:
        suggestions.append(f'大量库存可编织大件：{base_projects[0]}大尺寸版本')
        suggestions.append(f'批量制作小件出售：{base_projects[1]}套装 x5')
    elif quantity >= 5:
        suggestions.append(f'推荐：{base_projects[0]}')
        suggestions.append(f'搭配其他颜色制作：{base_projects[1]}')
    elif quantity >= 2:
        suggestions.append(f'适合做：{base_projects[1]}（少量消耗）')
        suggestions.append(f'作为点缀色用于：其他作品的装饰边')
    else:
        suggestions.append(f'少量库存适合做装饰：{base_projects[2]}')
        suggestions.append('可作为其他项目的点缀或拼接色块')

    if material and material != '未知':
        mat_suggestions = {
            '棉': '适合贴身衣物、家居用品',
            '羊毛': '适合围巾、帽子、保暖衣物',
            '腈纶': '适合玩偶、装饰件，耐洗耐磨',
            '亚麻': '适合夏季衣物、家居装饰',
            '马海毛': '适合披肩、毛绒质感作品',
            '蚕丝': '适合高档饰品、蕾丝作品'
        }
        for key, val in mat_suggestions.items():
            if key in str(material):
                suggestions.append(f'{material}材质特性：{val}')
                break

    return suggestions
