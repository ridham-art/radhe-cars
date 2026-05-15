"""Fix mojibake in vehicle_master_partial.html."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'templates/admin_panel/partials/vehicle_master_partial.html'
text = path.read_text(encoding='utf-8-sig')  # strip BOM if present

replacements = [
    ('â€¦', '…'),
    ('Â·', '·'),
    ('â€œ', '"'),
    ('â€\x9d', '"'),
    ('â€"', '—'),
    ('â€"', '—'),
]
for old, new in replacements:
    text = text.replace(old, new)

path.write_text(text, encoding='utf-8', newline='\n')
print('Fixed', path.name)
