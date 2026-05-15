from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def extract(src_rel, dest_rel, start, end):
    lines = (ROOT / src_rel).read_text(encoding='utf-8').splitlines()
    body = '\n'.join(lines[start - 1 : end]) + '\n'
    (ROOT / dest_rel).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / dest_rel).write_text(body, encoding='utf-8')

def wrap_list(src_rel, partial_name, head_lines_end):
    src = (ROOT / src_rel).read_text(encoding='utf-8').splitlines()
    header = []
    for line in src:
        header.append(line)
        if '{% block content %}' in line:
            break
    # keep page-head (lines after block content until head_lines_end)
    for line in src[len(header) : head_lines_end]:
        header.append(line)
    out = header + [
        '',
        '<div data-ap-partial-root>',
        f'{{% include "admin_panel/partials/{partial_name}" %}}',
        '</motion>',
        '{% endblock %}',
    ]
    text = '\n'.join(out) + '\n'
    text = text.replace('<motion>', '<div>').replace('</motion>', '</div>')
    (ROOT / src_rel).write_text(text, encoding='utf-8')

extract('templates/admin_panel/customer_list_new.html', 'templates/admin_panel/partials/customer_list_partial.html', 16, 60)
wrap_list('templates/admin_panel/customer_list_new.html', 'customer_list_partial.html', 14)

extract('templates/admin_panel/wishlist_list_new.html', 'templates/admin_panel/partials/wishlist_list_partial.html', 16, 60)
wrap_list('templates/admin_panel/wishlist_list_new.html', 'wishlist_list_partial.html', 14)

extract('templates/admin_panel/inquiry_list_new.html', 'templates/admin_panel/partials/inquiry_list_partial.html', 16, 87)
wrap_list('templates/admin_panel/inquiry_list_new.html', 'inquiry_list_partial.html', 14)

extract('templates/admin_panel/sell_car_inquiry_list_new.html', 'templates/admin_panel/partials/sell_car_inquiry_partial.html', 16, 210)
# sell: keep head + partial + modal
src = (ROOT / 'templates/admin_panel/sell_car_inquiry_list_new.html').read_text(encoding='utf-8').splitlines()
head = src[:14]  # through page-head-req block line 14
head.append('')
head.append('<div data-ap-partial-root>')
head.append('{% include "admin_panel/partials/sell_car_inquiry_partial.html" %}')
head.append('</div>')
head.append('')
head.extend(src[211:237])  # modal
head.append('{% endblock %}')
head.append('{% block extra_js %}')
head.append('<script src="{% static \'js/admin-panel-requests.js\' %}"></script>')
head.append('{% endblock %}')
text = '\n'.join(head) + '\n'
(ROOT / 'templates/admin_panel/sell_car_inquiry_list_new.html').write_text(text, encoding='utf-8')

print('done')
