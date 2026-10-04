"""Build an evidence inventory and audit coverage without inventing missing facts."""
import re
from datetime import date

MONTHS = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember')


def natural_dates(text):
    def replace(match):
        try:
            value = date.fromisoformat(match.group())
            return f'{value.day} {MONTHS[value.month - 1]} {value.year}'
        except ValueError:
            return match.group()
    return re.sub(r'\b\d{4}-\d{2}-\d{2}\b', replace, text)


def build_brief(sources):
    brief = {'context': [], 'activities': [], 'results': [], 'supporting_facts': [], 'limitations': [], 'required_totals': []}
    for source_id, source in sources.items():
        fields = source.get('fields') or {}
        analysis = fields.get('table_analysis')
        if not analysis:
            brief['supporting_facts'].append({'source_id': source_id, 'facts': source})
            continue
        unit = analysis['record_unit']
        brief['required_totals'].append({'source_id': source_id, 'label': 'Jumlah ' + unit,
            'count': analysis['record_count'], 'unit': unit})
        if analysis.get('unique_person_count') is not None:
            brief['required_totals'].append({'source_id': source_id, 'label': 'Jumlah peserta unik',
                'count': analysis['unique_person_count'], 'unit': 'orang', 'kind': 'unique_people'})
        elif analysis.get('known_unique_person_count') is not None:
            brief['supporting_facts'].append({'source_id': source_id,
                'known_unique_person_count': analysis['known_unique_person_count'],
                'missing_person_id_rows': analysis['missing_person_id_rows'], 'exact_total_unknown': True})
        brief['limitations'].extend(analysis['limitations'])
        if analysis.get('service_totals') is not None:
            brief['required_totals'].extend({'source_id': source_id, 'label': label, 'column': 'layanan',
                'count': count, 'unit': 'layanan'} for label, count in analysis['service_totals'].items())
        for key, stats in analysis['columns'].items():
            label = stats['label'].replace('_', ' ')
            counts = stats.get('counts', {})
            if analysis.get('row_semantics', 'records') != 'records':
                counts = {}  # Aggregate rows are not individual service occurrences.
            role = ('results' if re.search(r'hasil|result|outcome|tindak_lanjut|follow_up', key)
                    else 'activities' if re.search(r'jenis|layanan|service|activity|aktivitas|produk|product', key)
                    else 'context' if len(counts) == 1 else 'supporting_facts')
            entry = {'source_id': source_id, 'label': label,
                     'distribution': [{'value': natural_dates(value), 'count': count, 'unit': unit} for value, count in counts.items()]}
            if 'sum' in stats:
                entry['sum'] = stats['sum']
            brief[role].append(entry)
            if role in {'activities', 'results'}:
                brief['required_totals'].extend({'source_id': source_id, 'label': value, 'column': label,
                    'count': count, 'unit': unit} for value, count in counts.items())
    brief['limitations'] = list(dict.fromkeys(brief['limitations']))
    return brief


def coverage_issues(article, brief):
    """Concrete revision findings; summaries/headlines do not substitute for article coverage."""
    text = ' '.join([article['lead'], *article['body']]).casefold()
    issues = []
    for fact in brief['required_totals']:
        if fact['source_id'] not in article['sources_used']:
            continue
        number = str(fact['count'])
        number_forms = {number, f"{fact['count']:,}".replace(',', '.')}
        candidates = [text]
        if 'column' in fact:
            words = [w for w in re.findall(r'\w+', fact['label'].casefold()) if len(w) > 2 and w not in {'yang', 'ada', 'untuk', 'the', 'and', 'with'}]
            candidates = [sentence for sentence in re.split(r'[.!?;](?:\s|$)', text)
                          if not words or sum(w in sentence for w in words) / len(words) >= .6]
        if not any(re.search(r'(?<!\d)' + re.escape(n) + r'(?!\d)', sentence)
                   for n in number_forms for sentence in candidates):
            issues.append(f"Include supported total: {fact['label']} = {number} {fact['unit']} ({fact['source_id']}).")
    for fact in brief['required_totals']:
        supported_people = any(f.get('kind') == 'unique_people' and f['count'] == fact['count']
                               and f['source_id'] in article['sources_used'] for f in brief['required_totals'])
        if fact['source_id'] in article['sources_used'] and fact.get('kind') != 'unique_people' and not supported_people and 'column' not in fact and re.search(r'\b' + str(fact['count']) + r'\s+(?:orang|peserta|warga|people|persons)\b', text):
            issues.append('Unsupported unique-person count: source establishes records/visits, not distinct people.')
        if 'column' not in fact and len(re.findall(r'\b' + str(fact['count']) + r'\s+' + re.escape(fact['unit']) + r'\b', text)) > 1:
            issues.append('State the overall record/visit total once; other paragraphs should describe activities and results without repeating that total.')
    # Dates and event locations belong in one narrative position, normally the lead.
    for item in brief['context']:
        if not re.search(r'tanggal|date|lokasi|location|tempat|venue', item['label'], re.I):
            continue
        for value in item.get('distribution', []):
            fact = value['value'].casefold()
            if fact and text.count(fact) > 1:
                issues.append(f'Mention {value["value"]} once in lead/body; replace repetitive context with activities or results.')
    paragraphs = [re.sub(r'\W+', ' ', p).strip().casefold() for p in [article['lead'], *article['body']]]
    if len(set(paragraphs)) < len(paragraphs):
        issues.append('Remove repeated paragraphs; each paragraph must add a distinct supported fact.')
    return list(dict.fromkeys(issues))


WRITING_RULES = '''Use the editorial_brief to plan distinct paragraphs before writing.
Lead: event/topic, main finding, and date/location together when known. Body: activities, results and relevant implications explicitly supported by evidence.
State the overall record/visit total once in the narrative. Do not repeat it in body introductions or transitions.
Do not create separate paragraphs merely restating when or where the event occurred. Each paragraph adds new facts. Do not repeat the lead as body[0].
Include the important table totals and explain what was counted. Visit, service, registration and record counts are NOT unique people.
Use supplied unique-person totals when available; do not request counts already established by the evidence. Known IDs with missing IDs are a lower bound, not an exact total. Never sum distinct people across groups.
Column distributions are separate measures; do not add overlapping outcomes and follow-up counts. A recommendation is not a completed action.
Do not infer diagnoses, success, benefits, causation or quotations. Do not invent missing facts. Preserve synthetic/test-data labels as a visible qualification.
Use natural Indonesian dates such as 21 September 2026, not ISO dates, when language is id. Keep the original units and uncertainty.
Select relevant supported facts across files for the requested topic; never pad a short article with repeated context.'''


def deduplicate_narrative(article, brief):
    """Remove context-only repeats, never sentences that introduce new content words.

    This is deliberately conservative; semantic repetition still goes to reflection.
    Headlines and summaries are separate presentation fields, not body paragraphs.
    """
    stop = set('di pada ini itu tersebut kegiatan acara berlangsung dilaksanakan diselenggarakan mencatat tercatat sebanyak total jumlah ada telah melibatkan yang oleh dengan dan dari untuk the a an in on at this that event was held recorded of and'.split())
    def tokens(sentence):
        return set(re.findall(r'\w+', sentence.casefold())) - stop
    previous = [article.lead]
    context = [v['value'].casefold() for item in brief['context']
               if re.search(r'tanggal|date|lokasi|location|tempat|venue', item['label'], re.I)
               for v in item.get('distribution', [])]
    totals = [f for f in brief['required_totals'] if 'column' not in f]
    clean = []
    for paragraph in article.body:
        sentences = []
        for sentence in re.split(r'(?<=[.!?])\s+', paragraph):
            prior = ' '.join(previous).casefold()
            for fact in totals:
                phrase = rf"{fact['count']}\s+{re.escape(fact['unit'])}"
                if re.search(phrase, prior):
                    # Remove only a redundant transition before a comma, retaining its finding.
                    sentence = re.sub(rf'^Dari\s+(?:total\s+|jumlah\s+)?{phrase}\s+tersebut,\s*', '', sentence, flags=re.I)
            words = tokens(sentence)
            has_context = any(value in sentence.casefold() and value in prior for value in context)
            has_context = has_context or any(re.search(rf"\b{f['count']}\s+{re.escape(f['unit'])}\b", sentence, re.I) for f in totals)
            repeated = any(sentence.strip().casefold() == old.strip().casefold() for old in previous)
            if has_context and words:
                repeated = repeated or any(words <= tokens(old) and
                    (words & {'tidak', 'bukan', 'not', 'never'}) == (tokens(old) & {'tidak', 'bukan', 'not', 'never'})
                    for old in previous)
            if not repeated and sentence.strip():
                sentence = sentence[0].upper() + sentence[1:]
                sentences.append(sentence)
                previous.append(sentence)
        if sentences:
            clean.append(' '.join(sentences))
    # An empty narrative needs model revision; don't manufacture filler to satisfy the schema.
    if clean:
        article.body = clean
    return article
