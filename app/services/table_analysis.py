"""Full-table descriptive statistics. Counts describe records, never unique people."""
from collections import Counter, defaultdict
from decimal import Decimal
import json
import re
from app.schemas.information import ExtractionResponse, InformationItem, Evidence


def column_key(value):
    return re.sub(r'[^a-z0-9]+', '_', value.strip().casefold()).strip('_')


def analyze_tables(document):
    if not document.elements or any(e.element_type != 'table_row' or 'cells' not in e.metadata for e in document.elements):
        return None
    tables = defaultdict(list)
    for element in document.elements:
        tables[(element.source.filename, element.source.sheet)].append(element)
    items = []
    for (filename, sheet), elements in tables.items():
        headers = elements[0].metadata['cells']
        keys = [column_key(h) for h in headers]
        if not all(keys) or len(set(keys)) != len(keys) or len(elements) < 2:
            return None
        if any(len(e.metadata['cells']) != len(keys) for e in elements[1:]):
            return None
        group_columns = [k for k in keys if k in {'event_id', 'id_acara', 'nama_kegiatan', 'event_name', 'nama_acara', 'tanggal_kegiatan', 'event_date', 'lokasi_kegiatan', 'event_location'}]
        groups = defaultdict(list)
        for element in elements[1:]:
            row = dict(zip(keys, element.metadata['cells']))
            groups[tuple(row[k] for k in group_columns)].append((element, row))
        for rows in groups.values():
            columns = {}
            for key, label in zip(keys, headers):
                values = [str(row[key]).strip() for _, row in rows]
                present = [v for v in values if v]
                counts = Counter(present)
                stats = {'label': label, 'missing': len(values) - len(present), 'distinct_values': len(counts)}
                # Do not copy identifying/contact data into public editorial summaries.
                identifying = bool(re.search(r'(^id$|^id_|_id$|email|phone|telepon|nik|attendee_name|nama_peserta|nama_pasien)', key))
                if not identifying:
                    if len(counts) <= 30:
                        stats['counts'] = dict(counts)
                    else:
                        stats['distribution_omitted'] = 'More than 30 distinct values; use original rows for detail.'
                    # Only unambiguous numeric strings; never guess decimal/thousands locale.
                    if present and all(re.fullmatch(r'-?\d+(?:\.\d+)?', v) for v in present):
                        numbers = [Decimal(v) for v in present]
                        stats['minimum'] = str(min(numbers))
                        stats['maximum'] = str(max(numbers))
                        if re.search(r'(^|_)(quantity|amount|biaya|anggaran)(_|$)', key):
                            stats['sum'] = str(sum(numbers))
                columns[key] = stats
            names = [rows[0][1][k] for k in keys if k in {'nama_kegiatan', 'event_name', 'nama_acara'} and rows[0][1][k]]
            title = names[0] if names else f'Ringkasan data {filename}' + (f' — {sheet}' if sheet else '')
            visit_key = next((k for k in keys if k in {'id_kunjungan', 'visit_id'}), None)
            distinct_visits = len({row[visit_key] for _, row in rows if row[visit_key]}) if visit_key else None
            unit = 'kunjungan' if distinct_visits == len(rows) else 'catatan'

            ranges = []
            for element, _ in rows:
                number = element.source.row
                if ranges and number == ranges[-1][1] + 1:
                    ranges[-1][1] = number
                else:
                    ranges.append([number, number])
            fields = {'table_analysis': {'record_count': len(rows), 'record_unit': unit,
                'unique_person_count': None, 'distinct_visit_id_count': distinct_visits, 'columns': columns,
                'duplicate_rows': len(rows) - len({tuple(row.values()) for _, row in rows}),
                'source_row_ranges': ranges,
                'method': 'full_table_descriptive_v1',
                'limitations': ['Jumlah catatan/kunjungan bukan jumlah orang unik.',
                    'Distribusi tiap kolom dihitung terpisah; jangan menjumlahkan hasil dan tindak lanjut sebagai orang berbeda.']}}
            marker = f'filename={filename}' + (f', sheet={sheet}' if sheet else '') + ', section=calculated-table-analysis'
            # Explicit derived provenance rather than claiming these are verbatim raw quotations.
            evidence = Evidence(source=marker, quote='Perhitungan seluruh baris sumber: ' + json.dumps(fields['table_analysis'], ensure_ascii=False))
            items.append(InformationItem(type='General', title=title,
                summary=f'{title}: {len(rows)} {unit} tercatat. Rincian kegiatan dan hasil dihitung dari seluruh baris sumber; jumlah orang unik belum diketahui.',
                labels=['ringkasan data'], fields=fields, evidence=[evidence], confidence=0.95))
    return ExtractionResponse(information=items)
