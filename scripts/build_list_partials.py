"""Extract list partials and wrap list templates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SPECS = [
    (
        'templates/admin_panel/customer_list_new.html',
        'templates/admin_panel/partials/customer_list_partial.html',
        '<div class="page-head-list">',
    ),
    (
        'templates/admin_panel/wishlist_list_new.html',
        'templates/admin_panel/partials/wishlist_list_partial.html',
        '<motion class="page-head-list">',
    ),
    (
        'templates/admin_panel/inquiry_list_new.html',
        'templates/admin_panel/partials/inquiry_list_partial.html',
        '<div class="page-head-list">',
    ),
]

for src_path, partial_path, head_marker in SPECS:
    src_path = head_marker.replace('<motion ', '<div ').replace('</motion>', '</motion>')
    src = (ROOT / src_path.replace('templates/', 'templates/')).read_text(encoding='utf-8')
    if head_marker.startswith('<motion'):
        head_marker = head_marker.replace('<motion', '<div')
    lines = src.splitlines()
    start = None
    for i, line in enumerate(lines):
        if head_marker in line or (head_marker.strip('<div') in line and 'page-head' in line):
            # content after page-head block ends at first blank after head section
            pass
    # find {% block content %} then skip until after page-head closing
    in_content = False
    depth = 0
    partial_start = None
    for i, line in enumerate(lines):
        if '{% block content %}' in line:
            in_content = True
            continue
        if not in_content:
            continue
        if partial_start is None:
            if line.strip().startswith('<div class="page-head'):
                depth = 1
                continue
            if depth and line.strip() == '</div>':
                partial_start = i + 1
                continue
        if partial_start is not None and '{% endblock %}' in line:
            partial_end = i
            break
    else:
        partial_end = len(lines)

    partial_lines = lines[partial_start:partial_end]
    partial_body = '\n'.join(partial_lines).strip() + '\n'
    (ROOT / partial_path).write_text(partial_body, encoding='utf-8')

    new_content_lines = lines[:partial_start]
    wrap_id = partial_path.stem.replace('_partial', '')
    new_content_lines.append(f'<div id="ap-{wrap_id}" data-ap-partial-root>')
    new_content_lines.append(f'{{% include "admin_panel/partials/{partial_path.name}" %}}')
    new_content_lines.append('</div>')
    new_content_lines.append('{% endblock %}')
    # rebuild file: keep everything before block content inner part
    header = []
    for line in lines:
        header.append(line)
        if '{% block content %}' in line:
            break
    out = '\n'.join(header) + '\n' + '\n'.join(new_content_lines[partial_start - len(lines):]) 
    # simpler rebuild
    out_lines = []
    for line in lines:
        out_lines.append(line)
        if '{% block content %}' in line:
            break
    out_lines.append('<motion id="ap-partial" data-ap-partial-root>')
    out_lines.append(f'{{% include "admin_panel/partials/{partial_path.name}" %}}')
    out_lines.append('</div>')
    out_lines.append('{% endblock %}')
    text = '\n'.join(out_lines)
    text = text.replace('<motion ', '<div ').replace('</motion>', '</div>')
    (ROOT / src_path).write_text(text + '\n', encoding='utf-8')
    print('ok', src_path)
