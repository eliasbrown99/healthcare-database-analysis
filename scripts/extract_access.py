"""Read an Access file without modifying it; export eight application tables.

Optional dependency: access-parser==0.0.6. No Access/ODBC installation needed.
Boolean and long-text *property* values need explicit decoding because this
parser version otherwise returns empty strings for them. Row booleans are
handled by the parser itself. This is a table/metadata export, not an Access
forms/reports/VBA conversion.
"""
import argparse
import hashlib
import json
from pathlib import Path

TABLES = ['Patient', 'Hospitalization', 'Medication', 'Treatment',
          'PatientTreatment', 'PatientTreatmentMedication', 'Physician',
          'PhysicianTreatment']


def extract(path, destination):
    from access_parser import AccessParser
    from access_parser.parsing_primitives import LVPROP
    from access_parser.utils import parse_type
    db = AccessParser(str(path))
    destination.mkdir(parents=True, exist_ok=True)
    objects = db.parse_table('MSysObjects')
    catalog = [dict(zip(objects, row)) for row in zip(*objects.values())]
    properties = {}
    for row in catalog:
        if row['Name'] not in TABLES or not row.get('LvProp'):
            continue
        prop = LVPROP.parse(row['LvProp'])
        names = [n.name for n in prop.chunks[0].data.names]
        result = {}
        for chunk in prop.chunks:
            if not hasattr(chunk.data, 'data'):
                continue
            column = chunk.data.get('column_name', '__table__') or '__table__'
            result[column] = {}
            for item in chunk.data.data:
                if item.type == 1:
                    value = bool(int.from_bytes(item.actual_data, 'little'))
                elif item.type == 12:
                    value = item.actual_data.decode('utf-16-le', errors='replace')
                else:
                    value = parse_type(item.type, item.actual_data, version=db.version)
                name = names[item.name_index]
                if name in {'Required', 'AllowZeroLength', 'ValidationRule',
                            'ValidationText', 'Description', 'DefaultValue'}:
                    result[column][name] = value
        properties[row['Name']] = result
    schema = {}
    for name in TABLES:
        table = db.get_table(name)
        data = table.parse()
        rows = [dict(zip(data, row)) for row in zip(*data.values())]
        (destination / (name + '.json')).write_text(
            json.dumps(rows, default=str, indent=2) + '\n')
        schema[name] = {'row_count': len(rows), 'primary_key': table.primary_keys,
            'columns': [{'name': c.col_name_str, 'access_type_code': c.type,
                         'storage_length_bytes': c.length,
                         'text_max_characters': c.length // 2 if c.type == 10 else None,
                         'properties': properties.get(name, {}).get(c.col_name_str, {})}
                        for c in table.columns.values()],
            'table_properties': properties.get(name, {}).get('__table__', {})}
    for row in catalog:
        if row['Name'] == 'MSysRelationships':
            db.catalog[row['Name']] = row['Id']
    rel = db.parse_table('MSysRelationships')
    relations = [dict(zip(rel, row)) for row in zip(*rel.values())]
    relations = [r for r in relations if r['szObject'] in TABLES]
    manifest = {'source_filename': path.name,
                'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'reader': 'access-parser 0.0.6', 'schema': schema,
                'relationships': relations,
                'saved_queries': [r['Name'] for r in catalog if r['Type'] == 5],
                'forms': [r['Name'] for r in catalog if r['Type'] == -32768],
                'reports': [r['Name'] for r in catalog if r['Type'] == -32764]}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({name: info['row_count'] for name, info in schema.items()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('access_file', type=Path)
    parser.add_argument('--output', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'data/source')
    args = parser.parse_args()
    extract(args.access_file, args.output)
