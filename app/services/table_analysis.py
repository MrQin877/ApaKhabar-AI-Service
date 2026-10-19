"""Full-table descriptive statistics. Keep record, service and identified-person counts separate."""
from collections import Counter, defaultdict
from decimal import Decimal
import json
import re
from app.schemas.information import ExtractionResponse, InformationItem, Evidence


def column_key(value):
    return re.sub(r'[^a-z0-9]+', '_', value.strip().casefold()).strip('_')


# Explicit semantic aliases: a generic "id" or a person's name is not a person key.
PERSON_KEYS = {'participant_id', 'patient_id', 'person_id', 'attendee_id',
               'id_participant', 'id_peserta', 'id_pasien', 'id_orang', 'peserta_id', 'pasien_id'}
SERVICE_KEYS = {'service', 'service_type', 'jenis_layanan', 'layanan'}
COUNT_KEYS = {'count', 'total_count', 'service_count', 'visit_count', 'jumlah',
              'jumlah_layanan', 'jumlah_kunjungan', 'total'}
MISSING_IDS = {'', 'na', 'n/a', 'null', 'none', 'unknown', '-', 'tidak diketahui'}


def population_counts(rows, keys):
    roles = ({'laki_laki', 'male', 'men'}, {'perempuan', 'female', 'women'},
             {'wilayah', 'dusun', 'area', 'region'})
    matches = [[k for k in keys if k in aliases] for aliases in roles]
    if not all(len(m) == 1 for m in matches):
        return None
    male, female, area = [m[0] for m in matches]
    result = {'row_semantics': 'population_summary', 'population_totals': None,
              'limitations': ['Data adalah rekap penduduk per wilayah, bukan daftar peserta layanan.']}
    areas = [r[area].strip().casefold() for _, r in rows]
    dates = [k for k in keys if k in {'tanggal_referensi', 'reference_date', 'year', 'tahun'}]
    valid = (all(areas) and len(set(areas)) == len(areas)
             and not any(re.search(r'\b(total|subtotal|jumlah|keseluruhan)\b', a) for a in areas)
             and all(len({r[k].strip() for _, r in rows}) == 1 and rows[0][1][k].strip() for k in dates)
             and all(re.fullmatch(r'\d+', r[k].strip()) for _, r in rows for k in (male, female)))
    if valid:
        men = sum(int(r[male]) for _, r in rows)
        women = sum(int(r[female]) for _, r in rows)
        result['population_totals'] = {'male': men, 'female': women, 'total': men + women, 'area_count': len(areas)}
        result['limitations'].append('Total penduduk menjumlahkan kategori laki-laki dan perempuan pada wilayah berbeda dalam periode yang sama; bukan jumlah peserta unik berdasarkan ID.')
    else:
        result['limitations'].append('Rekap memiliki wilayah berulang, baris total, periode berbeda, atau angka tidak lengkap; total penduduk tidak dihitung untuk menghindari hitung ganda.')
    return result


def semantic_counts(rows, keys):
    person_keys = [k for k in keys if k in PERSON_KEYS]
    service_keys = [k for k in keys if k in SERVICE_KEYS]
    count_keys = [k for k in keys if k in COUNT_KEYS]
    result = {'unique_person_count': None, 'known_unique_person_count': None,
              'person_id_column': None, 'missing_person_id_rows': None,
              'service_totals': None, 'row_semantics': 'records', 'limitations': []}
    population = population_counts(rows, keys)
    if population is not None:
        result.update(population)
        return result
    if count_keys:
        result['row_semantics'] = 'ambiguous_aggregate'
        if len(count_keys) == len(service_keys) == 1:
            count_key, service_key = count_keys[0], service_keys[0]
            values = [row[count_key].strip() for _, row in rows]
            if all(re.fullmatch(r'\d+', v) for v in values) and all(row[service_key].strip() for _, row in rows):
                totals = Counter()
                for (_, row), value in zip(rows, values):
                    totals[row[service_key].strip()] += int(value)
                result.update(row_semantics='service_totals', service_totals=dict(totals), count_column=count_key)
        result['limitations'].append('Baris berisi atau mungkin berisi total agregat; jumlah baris bukan jumlah kunjungan atau orang. Total layanan dapat tumpang tindih dan bukan orang unik.')
    elif len(person_keys) == 1:
        key = person_keys[0]
        values = [row[key].strip() for _, row in rows]
        present = [v for v in values if v.casefold() not in MISSING_IDS]
        known = len(set(present))
        result.update(person_id_column=key, known_unique_person_count=known,
                      missing_person_id_rows=len(values) - len(present),
                      unique_person_count=known if len(present) == len(values) else None)
        result['limitations'].append('Orang unik dihitung berdasarkan ID dalam kelompok data ini; jangan menjumlahkan orang unik antarkelompok.')
        if len(present) != len(values):
            result['limitations'].append('Sebagian ID peserta kosong/tidak diketahui; jumlah ID unik yang tersedia hanya batas bawah jumlah peserta.')
    else:
        result['limitations'].append('Kolom ID orang tidak tersedia atau ambigu; jumlah orang unik belum dapat ditentukan. Jangan menebak dari nama atau ID kunjungan.')
    return result


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

            semantics = semantic_counts(rows, keys)
            if semantics['row_semantics'] != 'records':
                unit = 'baris agregat'

            ranges = []
            for element, _ in rows:
                number = element.source.row
                if ranges and number == ranges[-1][1] + 1:
                    ranges[-1][1] = number
                else:
                    ranges.append([number, number])
            fields = {'table_analysis': {'record_count': len(rows), 'record_unit': unit,
                **{k: v for k, v in semantics.items() if k != 'limitations'}, 'distinct_visit_id_count': distinct_visits, 'columns': columns,
                'duplicate_rows': len(rows) - len({tuple(row.values()) for _, row in rows}),
                'source_row_ranges': ranges,
                'method': 'full_table_descriptive_v2',
                'limitations': semantics['limitations'] + ['Jumlah catatan/kunjungan bukan jumlah orang unik.',
                    'Distribusi tiap kolom dihitung terpisah; jangan menjumlahkan hasil dan tindak lanjut sebagai orang berbeda.']}}
            marker = f'filename={filename}' + (f', sheet={sheet}' if sheet else '') + ', section=calculated-table-analysis'
            # Explicit derived provenance rather than claiming these are verbatim raw quotations.
            evidence = Evidence(source=marker, quote='Perhitungan seluruh baris sumber: ' + json.dumps(fields['table_analysis'], ensure_ascii=False))
            people = (f"{semantics['unique_person_count']} orang unik berdasarkan ID."
                      if semantics['unique_person_count'] is not None else 'Jumlah orang unik belum diketahui.')
            if semantics.get('population_totals'):
                totals = semantics['population_totals']
                people = f"Jumlah penduduk {totals['total']}: {totals['male']} laki-laki dan {totals['female']} perempuan di {totals['area_count']} wilayah."
            items.append(InformationItem(type='General', title=title,
                summary=f'{title}: {len(rows)} {unit} tercatat. Rincian kegiatan dan hasil dihitung dari seluruh baris sumber. {people}',
                labels=['ringkasan data'], fields=fields, evidence=[evidence], confidence=0.95))
    return ExtractionResponse(information=items)
