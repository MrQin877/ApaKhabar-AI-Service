"""Remove duplicated evidence from model payloads without truncating source facts."""
from copy import deepcopy
import json


def compact_context(data):
    payload = deepcopy(data)
    sources = payload.get('sources', {})
    brief = payload.get('editorial_brief')
    if brief:
        for fact in brief.get('supporting_facts', []):
            source_id = fact.get('source_id')
            if source_id in sources and fact.get('facts') == sources[source_id]:
                fact.pop('facts')
                fact['reference'] = 'See sources for the complete evidence.'
    for source in sources.values():
        analysis = (source.get('fields') or {}).get('table_analysis')
        if not analysis:
            continue
        # Only replace a machine-generated quote when its complete JSON exactly
        # matches the statistics retained in fields. Keep provenance and all other quotes.
        for evidence in source.get('evidence', []):
            quote = evidence.get('quote', '')
            prefix = 'Perhitungan seluruh baris sumber: '
            if not quote.startswith(prefix):
                continue
            try:
                duplicate = json.loads(quote[len(prefix):]) == analysis
            except (ValueError, TypeError):
                duplicate = False
            if duplicate:
                evidence['quote'] = 'Perhitungan seluruh baris sumber: lihat fields.table_analysis.'
    return payload
