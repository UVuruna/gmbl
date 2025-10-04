import json
import numpy as np

def insert_data(
    json_data: dict,
    model_name: str,
    data: dict
):
    DATA = data.copy()
    if model_name in json_data:
        DATA['version'] = str(float(json_data[model_name]['version']) + 0.01)
    else:
        json_data[model_name] = dict()
        DATA['version'] = '1.00'
    json_data[model_name] = DATA
    
    return json_data

def save_json(data, filename):
    # Pretvori sve np int/float u obične int/float
    def convert(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.ndarray,)):
            return o.tolist()
        return o

    # Prvo serijalizuj u string sa indent=4
    json_str = json.dumps(data, indent=4, ensure_ascii=False, default=convert)

    # Regex replace da sve RGB liste budu u jednom redu
    import re
    # Traži "RGB": [ ... ] gde je više whitespace-a i brojeva i stavi sve u jedan red
    json_str = re.sub(r'\[\s*([\d\s,]+)\s*\]', lambda m: f"[{','.join(x.strip() for x in m.group(1).split(','))}]", json_str)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(json_str)

def load_json(file):
    """Učitava podatke iz JSON fajla"""
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)