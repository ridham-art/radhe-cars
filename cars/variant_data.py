"""
Model-specific car variants for Indian market.
Key: (brand_name_lower, model_name_lower) -> list of variants
"""

import re

from .models import CarModelVariant

VARIANTS_BY_MODEL = {
    # Maruti Suzuki
    ('maruti suzuki', 'swift'): ['LXI', 'VXI', 'ZXI', 'ZXI+', 'ZXI+ Dual Tone', 'VXI AGS', 'ZXI AGS', 'ZXI+ AGS', 'LXI CNG', 'VXI CNG', 'ZXI CNG'],
    ('maruti suzuki', 'baleno'): ['Sigma', 'Delta', 'Zeta', 'Alpha', 'Alpha (ATC)', 'Delta (ATC)', 'Zeta (ATC)'],
    ('maruti suzuki', 'wagon r'): ['LXI', 'VXI', 'ZXI', 'ZXI+', 'ZXI+ AMT', 'LXI CNG', 'VXI CNG', 'ZXI CNG'],
    ('maruti suzuki', 'dzire'): ['LXI', 'VXI', 'ZXI', 'ZXI+', 'Tour', 'LXI CNG', 'VXI CNG', 'ZXI CNG'],
    ('maruti suzuki', 'celerio'): ['LXI', 'VXI', 'ZXI', 'ZXI AMT', 'VXI AMT', 'LXI CNG', 'VXI CNG'],
    ('maruti suzuki', 'alto'): ['Std', 'LXI', 'VXI', 'ZXI', 'K10 LXI', 'K10 VXI', 'K10 ZXI'],
    ('maruti suzuki', 'alto k10'): ['LXI', 'VXI', 'ZXI', 'ZXI+', 'LXI CNG', 'VXI CNG'],
    ('maruti suzuki', 'ertiga'): ['LXI', 'VXI', 'ZXI', 'ZXI+', 'ZXI+ AGS', 'LXI CNG', 'VXI CNG'],
    ('maruti suzuki', 'brezza'): ['LXI', 'VXI', 'ZXI', 'ZXI+', 'ZXI+ Dual Tone', 'LXI CNG', 'VXI CNG', 'ZXI CNG'],
    ('maruti suzuki', 'eeco'): ['5 Seater', '7 Seater', '5 Seater CNG', '7 Seater CNG'],
    ('maruti suzuki', 's-presso'): ['Std', 'Std (O)', 'VXI', 'VXI (O)', 'VXI+', 'VXI+ (O)'],
    ('maruti suzuki', 'ignis'): ['Sigma', 'Delta', 'Zeta', 'Alpha', 'Alpha AMT'],
    ('maruti suzuki', 'xl6'): ['Zeta', 'Zeta+', 'Alpha+', 'Alpha+ AT'],
    ('maruti suzuki', 'ciaz'): ['Sigma', 'Delta', 'Zeta', 'Alpha', 'Alpha AT'],
    ('maruti suzuki', 's-cross'): ['Sigma', 'Delta', 'Zeta', 'Alpha', 'Alpha AT'],
    ('maruti suzuki', 'vitara brezza'): ['LXI', 'VXI', 'ZXI', 'ZXI+', 'ZXI+ Dual Tone'],
    ('maruti suzuki', 'grand vitara'): ['Sigma', 'Delta', 'Zeta', 'Alpha', 'Alpha+', 'Alpha+ AT'],
    ('maruti suzuki', 'invicto'): ['Zeta+', 'Alpha+', 'Alpha+ AT'],
    ('maruti suzuki', 'fronx'): ['Sigma', 'Delta', 'Zeta', 'Alpha', 'Alpha+', 'Alpha+ AT'],
    ('maruti suzuki', 'jimny'): ['Sigma', 'Alpha', 'Alpha+'],
    ('maruti suzuki', 'spresso'): ['Std', 'Std (O)', 'VXI', 'VXI (O)', 'VXI+', 'VXI+ (O)'],

    # Hyundai
    ('hyundai', 'i10'): ['Era', 'Magna', 'Sportz', 'Asta', 'Asta (O)'],
    ('hyundai', 'grand i10'): ['Era', 'Magna', 'Sportz', 'Asta', 'Asta (O)'],
    ('hyundai', 'grand i10 nios'): ['Era', 'Magna', 'Sportz', 'Asta', 'Asta (O)', 'Magna AMT', 'Sportz AMT', 'Asta AMT'],
    ('hyundai', 'i20'): ['Era', 'Magna', 'Sportz', 'Asta', 'Asta (O)', 'Sportz DCT', 'Asta DCT'],
    ('hyundai', 'venue'): ['E', 'S', 'S+', 'SX', 'SX (O)', 'SX+', 'SX+ (O)'],
    ('hyundai', 'creta'): ['E', 'EX', 'S', 'SX', 'SX (O)', 'SX+', 'SX+ (O)'],
    ('hyundai', 'santro'): ['Era', 'Magna', 'Sportz', 'Asta', 'Asta (O)'],
    ('hyundai', 'verna'): ['E', 'EX', 'S', 'SX', 'SX (O)', 'SX+', 'SX+ (O)'],
    ('hyundai', 'aura'): ['E', 'S', 'SX', 'SX (O)'],
    ('hyundai', 'tucson'): ['E', 'S', 'SX', 'SX (O)'],
    ('hyundai', 'alcazar'): ['Prestige', 'Platinum', 'Signature'],
    ('hyundai', 'exter'): ['E', 'EX', 'S', 'SX', 'SX (O)', 'SX+', 'SX+ (O)'],
    ('hyundai', 'carens'): ['Prestige', 'Prestige Plus', 'Luxury', 'Luxury Plus', 'Premium'],
    ('hyundai', 'ioniq 5'): ['RWD', 'AWD'],
    ('hyundai', 'kona'): ['Premium', 'Premium Dual Tone'],

    # Tata
    ('tata', 'punch'): ['Pure', 'Adventure', 'Creative', 'Accomplished', 'Creative (AMT)', 'Accomplished (AMT)'],
    ('tata', 'nexon'): ['Smart', 'Smart+', 'Creative', 'Creative+', 'Fearless', 'Fearless+', 'Fearless+ S', 'Creative (AMT)', 'Fearless (AMT)'],
    ('tata', 'harrier'): ['Smart', 'Smart+', 'Adventure', 'Adventure+', 'Fearless', 'Fearless+', 'Fearless+ Dark'],
    ('tata', 'safari'): ['Smart', 'Smart+', 'Adventure', 'Adventure+', 'Fearless', 'Fearless+', 'Fearless+ Dark'],
    ('tata', 'tiago'): ['XE', 'XM', 'XZ', 'XZ+', 'XZ+ AMT', 'NRG'],
    ('tata', 'altroz'): ['XE', 'XM', 'XM+', 'XZ', 'XZ+', 'XZ+ Dark', 'XM+ AMT', 'XZ+ AMT'],
    ('tata', 'tigor'): ['XE', 'XM', 'XZ', 'XZ+', 'XZ+ AMT', 'EV XZ+', 'EV XZ+ Lux'],
    ('tata', 'curvv'): ['Smart', 'Smart+', 'Creative', 'Creative+', 'Fearless', 'Fearless+'],
    ('tata', 'ev'): ['XR', 'XR+', 'XT', 'XT+', 'XZ+', 'XZ+ Lux'],

    # Kia
    ('kia', 'seltos'): ['HTE', 'HTK', 'HTK+', 'HTX', 'HTX+', 'GTX+', 'X-Line'],
    ('kia', 'sonet'): ['HTE', 'HTK', 'HTK+', 'HTX', 'HTX+', 'GTX+', 'X-Line'],
    ('kia', 'carens'): ['Premium', 'Prestige', 'Prestige Plus', 'Luxury', 'Luxury Plus'],
    ('kia', 'ev6'): ['GT Line', 'GT Line AWD'],
    ('kia', 'carnival'): ['Prestige', 'Luxury', 'Luxury Plus'],

    # Mahindra
    ('mahindra', 'xuv700'): ['MX', 'MX (Adventure)', 'AX3', 'AX5', 'AX7', 'AX7 L'],
    ('mahindra', 'scorpio'): ['Std', 'Std 2WD', 'Z2', 'Z4', 'Z8', 'Z8 L', 'S11', 'S11 4WD'],
    ('mahindra', 'scorpio n'): ['Z2', 'Z4', 'Z6', 'Z8', 'Z8 L', 'S11', 'S11 4WD'],
    ('mahindra', 'thar'): ['AX', 'AX (O)', 'LX', 'LX (O)', 'AX Opt', 'LX Opt'],
    ('mahindra', 'xuv300'): ['W4', 'W6', 'W8', 'W8 (O)', 'W8 (O) AMT'],
    ('mahindra', 'xuv400'): ['EC', 'EL', 'EP'],
    ('mahindra', 'bolero'): ['B4', 'B6', 'B6 (O)', 'Neo', 'Neo +', 'Neo (O)'],
    ('mahindra', 'marazzo'): ['M2', 'M4', 'M6', 'M8'],
    ('mahindra', 'xuv3xo'): ['MX1', 'MX2', 'MX3', 'MX4', 'MX5'],

    # Honda
    ('honda', 'city'): ['V', 'VX', 'ZX', 'ZX CVT', 'V CVT', 'VX CVT'],
    ('honda', 'amaze'): ['E', 'S', 'V', 'VX', 'V CVT', 'VX CVT'],
    ('honda', 'elevate'): ['S', 'V', 'VX', 'ZX', 'V CVT', 'VX CVT', 'ZX CVT'],
    ('honda', 'jazz'): ['V', 'VX', 'ZX', 'V CVT', 'VX CVT'],
    ('honda', 'wr-v'): ['V', 'VX', 'ZX', 'V CVT', 'VX CVT'],
    ('honda', 'civic'): ['V', 'VX', 'ZX', 'ZX CVT'],
    ('honda', 'cr-v'): ['V', 'VX', 'ZX', 'ZX AWD'],

    # Toyota
    ('toyota', 'innova crysta'): ['G', 'GX', 'V', 'VX', 'ZX', 'GX AT', 'VX AT'],
    ('toyota', 'innova hycross'): ['G', 'GX', 'VX', 'ZX', 'ZX+', 'VX AT', 'ZX AT', 'ZX+ AT'],
    ('toyota', 'fortuner'): ['Legender', '4x2', '4x4', 'Legender 4x4'],
    ('toyota', 'glanza'): ['E', 'G', 'V', 'V CVT'],
    ('toyota', 'urban cruiser'): ['E', 'S', 'G', 'G AT'],
    ('toyota', 'urban cruiser hyryder'): ['E', 'S', 'G', 'G AT', 'V', 'V AT', 'S Hybrid', 'G Hybrid', 'V Hybrid'],
    ('toyota', 'rumion'): ['G', 'V', 'V AT'],
    ('toyota', 'hilux'): ['Std', 'Std MT', 'High'],
    ('toyota', 'camry'): ['Hybrid'],
    ('toyota', 'vellfire'): ['Zx', 'Zx Lounge'],

    # Renault
    ('renault', 'kwid'): ['Std', 'RXL', 'RXT', 'RXT (O)', 'Climber', 'Climber (O)'],
    ('renault', 'triber'): ['RXE', 'RXL', 'RXT', 'RXT (O)'],
    ('renault', 'kiger'): ['RXE', 'RXL', 'RXT', 'RXT (O)', 'RXT Turbo', 'RXT Turbo (O)'],
    ('renault', 'duster'): ['RXE', 'RXL', 'RXT', 'RXT (O)', 'RXZ', 'RXZ (O)', 'RXZ 4WD'],
    ('renault', 'magnite'): ['RXE', 'RXL', 'RXT', 'RXT (O)', 'RXV', 'RXV (O)', 'RXV Turbo', 'RXV Turbo (O)'],

    # Nissan
    ('nissan', 'magnite'): ['XL', 'XV', 'XV Premium', 'XV Premium (O)', 'XV Turbo', 'XV Turbo (O)'],
    ('nissan', 'kicks'): ['XL', 'XV', 'XV Premium', 'XV Premium (O)', 'XV Turbo', 'XV Turbo (O)'],

    # MG
    ('mg', 'hector'): ['Style', 'Super', 'Smart', 'Sharp', 'Savage'],
    ('mg', 'gloster'): ['Super', 'Smart', 'Sharp', 'Savage'],
    ('mg', 'zs ev'): ['Excite', 'Exclusive'],
    ('mg', 'comet'): ['EV', 'EV (O)'],

    # Skoda
    ('skoda', 'slavia'): ['Active', 'Ambition', 'Style', 'Monte Carlo'],
    ('skoda', 'kushaq'): ['Active', 'Ambition', 'Style', 'Monte Carlo'],
    ('skoda', 'kodiaq'): ['Style', 'Sportline', 'Laurin & Klement'],
    ('skoda', 'superb'): ['Sportline', 'Laurin & Klement'],
    ('skoda', 'octavia'): ['Style', 'Sportline', 'Laurin & Klement'],

    # Volkswagen
    ('volkswagen', 'virtus'): ['Trendline', 'Highline', 'GT Edge'],
    ('volkswagen', 'taigun'): ['Trendline', 'Highline', 'GT Edge', 'GT Plus'],
    ('volkswagen', 'tiguan'): ['Comfortline', 'Highline'],
    ('volkswagen', 'polo'): ['Trendline', 'Comfortline', 'Highline', 'GT'],
    ('volkswagen', 'vento'): ['Trendline', 'Comfortline', 'Highline'],

    # Chevrolet
    ('chevrolet', 'beat'): ['LS', 'LT', 'LT (O)', 'LXI', 'VXI', 'ZXI'],
    ('chevrolet', 'spark'): ['LS', 'LT', 'LT (O)'],
    ('chevrolet', 'cruze'): ['LS', 'LT', 'LTZ'],
    ('chevrolet', 'trailblazer'): ['LT', 'LTZ'],
    ('chevrolet', 'captiva'): ['LS', 'LT', 'LTZ'],
    ('chevrolet', 'tavera'): ['LS', 'LT', 'LTZ'],
    ('chevrolet', 'optra'): ['LS', 'LT', 'LTZ'],
    ('chevrolet', 'aveo'): ['LS', 'LT', 'LTZ'],
    ('chevrolet', 'sail'): ['LS', 'LT', 'LTZ'],
    ('chevrolet', 'enjoy'): ['LS', 'LT', 'LTZ'],
}

# Fallback variants when model not found
DEFAULT_VARIANTS = [
    'LXI', 'VXI', 'ZXI', 'ZXI+', 'Alpha', 'Delta', 'Sigma', 'Zeta',
    'E', 'EX', 'S', 'S+', 'V', 'V+', 'VX', 'VX+', 'Base', 'Standard',
    'Plus', 'Premium', 'Top', 'Limited', 'Std', 'Era', 'Magna', 'Sportz', 'Asta',
    'Other',
]


# Brand name aliases (short name -> full name for lookup)
BRAND_ALIASES = {
    'maruti': 'maruti suzuki',
    'suzuki': 'maruti suzuki',
    'tata motors': 'tata',
    'tata motors limited': 'tata',
}

def get_variants_for_model(brand_name: str, model_name: str) -> list:
    """Return variant list for given brand and model. Case-insensitive lookup."""
    if not brand_name or not model_name:
        return DEFAULT_VARIANTS
    b = str(brand_name).strip().lower()
    m = str(model_name).strip().lower()
    b = BRAND_ALIASES.get(b, b)
    key = (b, m)
    if key in VARIANTS_BY_MODEL:
        return VARIANTS_BY_MODEL[key]
    b_first = b.split()[0] if b else ''
    b_aliased = BRAND_ALIASES.get(b_first, b_first)
    if (b_aliased, m) in VARIANTS_BY_MODEL:
        return VARIANTS_BY_MODEL[(b_aliased, m)]
    return DEFAULT_VARIANTS


def get_merged_variant_names(car_model) -> list:
    """DB variant names first, then static presets not already present."""
    db = list(car_model.variants.values_list('name', flat=True))
    static = get_variants_for_model(car_model.brand.name, car_model.name)
    seen = {n.casefold() for n in db}
    for s in static:
        if s.casefold() not in seen:
            db.append(s)
            seen.add(s.casefold())
    return db


def lookup_static_variant_names_strict(brand_name: str, model_name: str) -> list:
    """Like get_variants_for_model but returns [] when no catalog match (never DEFAULT_VARIANTS)."""
    if not brand_name or not model_name:
        return []
    b = str(brand_name).strip().lower()
    m = str(model_name).strip().lower()
    b = BRAND_ALIASES.get(b, b)
    key = (b, m)
    if key in VARIANTS_BY_MODEL:
        return list(VARIANTS_BY_MODEL[key])
    b_first = b.split()[0] if b else ''
    b_aliased = BRAND_ALIASES.get(b_first, b_first)
    if (b_aliased, m) in VARIANTS_BY_MODEL:
        return list(VARIANTS_BY_MODEL[(b_aliased, m)])
    return []


_AUTO_NAME_RE = re.compile(
    r'\b(AT|AMT|AGS|DCT|CVT|TC|ATC)\b|\(AT\)|\(ATC\)|\bAUTO\b',
    re.IGNORECASE,
)


def infer_transmission_from_variant_name(name: str) -> str:
    """Heuristic for catalog-only variant strings (no DB row)."""
    if not name or not str(name).strip():
        return 'Manual'
    s = str(name).strip()
    u = s.upper()
    if _AUTO_NAME_RE.search(u):
        return 'Automatic'
    if ' AT' in u or u.endswith(' AT') or '(AT)' in u or '(ATC)' in u:
        return 'Automatic'
    return 'Manual'


def get_merged_variants_for_sell(car_model) -> list:
    """
    Variants for sell form: DB rows first (exact transmission), then static catalog
    names only when VARIANTS_BY_MODEL matches (never DEFAULT_VARIANTS).
    Each item: {"name", "transmission", "fuel_type"}.
    """
    rows = []
    for v in CarModelVariant.objects.filter(car_model=car_model).order_by('name'):
        rows.append(
            {
                'name': v.name,
                'transmission': v.transmission,
                'fuel_type': v.fuel_type,
            }
        )
    seen = {r['name'].casefold() for r in rows}
    for s in lookup_static_variant_names_strict(
        car_model.brand.name, car_model.name
    ):
        if s.casefold() not in seen:
            rows.append(
                {
                    'name': s,
                    'transmission': infer_transmission_from_variant_name(s),
                    'fuel_type': None,
                }
            )
            seen.add(s.casefold())
    return rows
