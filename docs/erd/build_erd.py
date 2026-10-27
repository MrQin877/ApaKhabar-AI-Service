import json, pathlib, xml.etree.ElementTree as E, html, sys
out=pathlib.Path(__file__).resolve().parent; s=json.load(open(sys.argv[1] if len(sys.argv)>1 else '/tmp/apakhabar-erd-schema.json'))
groups={
'01 Accounts':['user_roles','users','emails','phones','password_reset_tokens','personal_access_tokens'],
'02 Broadcasts':['broadcast_categories','channels','broadcasts','broadcast_channel','broadcast_user'],
'03 News':['news_categories','news','likes','news_viewers','news_visits'],
'04 News moderation':['comments','comment_likes','comment_reports','comment_flags','comment_moderation_history'],
'05 Short videos':['short_videos','short_video_publications','short_video_viewers','short_video_likes'],
'06 Video moderation':['short_video_comments','short_video_comment_likes','short_video_comment_reports','short_video_comment_flags','short_video_comment_history'],
'07 Guests and notifications':['guest_comment_identities','guest_comment_days','notifications'],
'08 Intelligence':['intelligence_documents','intelligence_extraction_requests','intelligence_information'],
'09 Drafting and review':['intelligent_news_drafts','intelligent_news_draft_sources','intelligent_news_draft_versions','ai_quality_evaluations'],
'10 AI conversations':['intelligent_news_sessions','intelligent_news_messages','intelligent_news_runs','intelligent_news_run_events','intelligent_news_source_selections'],
'11 Social and analytics':['social_connections','meta_insight_snapshots','analytics_settings','analytics_setting_changes','villager_activity_hours'],
'12 Archives and legacy':['archived_comment_moderation_assessments','archived_comment_moderation_feedback','two_factors'],
'13 Laravel infrastructure':['jobs','failed_jobs','migrations']}
assert set(sum(groups.values(),[]))==set(s)
for t in s.values():
 if isinstance(t['indexes'],dict): t['indexes']=list(t['indexes'].values())
laravel_count=len(s)
import ast, sqlite3
ai_conn=sqlite3.connect(':memory:')
for source in [pathlib.Path('app/services/agent_service.py'), pathlib.Path('app/services/extraction_progress.py'), pathlib.Path('.venv/lib/python3.12/site-packages/langgraph/checkpoint/sqlite/__init__.py')]:
 tree=ast.parse(source.read_text())
 for node in ast.walk(tree):
  if isinstance(node, ast.Constant) and isinstance(node.value,str) and 'CREATE TABLE IF NOT EXISTS' in node.value:
   ai_conn.executescript(node.value)
for (name,) in ai_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
 cols=list(ai_conn.execute('PRAGMA table_info('+name+')'))
 indexes=[{'name':'primary','columns':[c[1] for c in sorted(cols,key=lambda c:c[5]) if c[5]],'primary':True,'unique':True}]
 for idx in ai_conn.execute('PRAGMA index_list('+name+')'):
  if idx[3]=='pk': continue
  indexes.append({'name':idx[1],'columns':[c[2] for c in ai_conn.execute('PRAGMA index_info('+idx[1]+')')],'primary':False,'unique':bool(idx[2])})
 s[name]={'columns':[{'name':c[1],'type':c[2],'nullable':not bool(c[3]),'default':c[4]} for c in cols], 'indexes':indexes,'foreign_keys':[]}
groups['14 AI service SQLite']=['runs','events','progress','checkpoints','writes']
def keys(t,n):
 return ','.join((['PK'] if any(i['primary'] and n in i['columns'] for i in t['indexes']) else [])+(['FK'] if any(n in f['columns'] for f in t['foreign_keys']) else [])+(['UK'] if any(i['unique'] and not i['primary'] and i['columns']==[n] for i in t['indexes']) else []))
intro='''# ApaKhabar database dictionary and ERD

Generated 26 October 2026 from the current working-tree source in both repositories. This is the **code-defined schema**, not a verification of a deployed database. All 60 Laravel migrations were executed in a disposable in-memory SQLite database in testing mode; no application database was modified. The bundled database/database.sqlite contains an older starter schema and was not used as the schema authority.

There are **56 Laravel tables** (50 operational tables, 2 archives, 1 legacy two_factors table, and jobs, failed_jobs and migrations), **5 AI-service SQLite tables**, and **2 code-defined Chroma collection patterns**. Chroma engine internals are excluded. SQL types below are SQLite-resolved types: Laravel JSON, enum, unsigned sizes and string lengths may be represented differently on MySQL. Consult the original migrations for engine-specific types and enum/check constraints.

PK = primary key; FK = enforced foreign key; UK = single-column unique key. Composite keys and unique constraints are listed after each table. Nullable reflects SQLite introspection; a primary key remains an identity constraint. Diagram pages repeat external referenced tables as key-only reference boxes. Solid connectors are enforced FKs; dashed connectors are explicitly identified logical links. Relationship labels give both endpoint ranges: parent 1 or 0..1, child 0..1 or 0..N. Unique foreign keys correctly produce one-to-one relationships. Solid versus dashed distinguishes enforced from logical relationships in draw.io; Mermaid uses its own identifying/non-identifying line convention. No inferred user-ID relationships are presented as enforced FKs.

## Files

- `apakhabar-erd.drawio`: editable, uncompressed draw.io XML; open it in diagrams.net/draw.io.
- `apakhabar-erd.mmd`: Mermaid ER code for all relational tables.
- `schema.json`: machine-readable schema metadata.

## Table inventory

'''
md=[intro]
for group,names in groups.items(): md.append(f"- **{group}:** "+', '.join('`'+n+'`' for n in names)+'\n')
mer=['erDiagram']
for group,names in groups.items():
 md.append('\n## '+group+'\n')
 for n in names:
  t=s[n]; md.append('\n### `'+n+'`\n\n| Attribute | Type | Key | Nullable | Default |\n|---|---|---|---|---|')
  mer.append('    '+n+' {')
  for c in t['columns']:
   k=keys(t,c['name']); md.append(f"| {c['name']} | {c['type']} | {k or '—'} | {'Yes' if c['nullable'] else 'No'} | {str(c.get('default')) if c.get('default') is not None else '—'} |")
   typ=c['type'].split('(')[0].replace(' ','_'); mer.append(f"        {typ} {c['name']}"+(f' {k}' if k else ''))
  mer.append('    }')
  for i in t['indexes']:
   if i['unique']: md.append('\n'+('Primary key' if i['primary'] else 'Unique')+': `'+', '.join(i['columns'])+'`.')
  for f in t['foreign_keys']:
   md.append(f"\nFK: `{','.join(f['columns'])}` → `{f['foreign_table']}.{','.join(f['foreign_columns'])}`; on delete: {f['on_delete']}.")
   nullable=any(c['nullable'] for c in t['columns'] if c['name'] in f['columns'])
   unique=any(i['unique'] and set(i['columns'])==set(f['columns']) for i in t['indexes'])
   mer.append(f"    {f['foreign_table']} {'|o' if nullable else '||'}..{'o|' if unique else 'o{'} {n} : \"{','.join(f['columns'])}\"")
md.append('''
## AI persistence notes

`runs` and `events` live in `agent_db_path + '.runs'`; `progress` lives in `agent_db_path + '.extractions'`. `checkpoints` and `writes` live at `agent_db_path` and are library-managed by the installed LangGraph SQLite saver. The default base path is `./data/agent/checkpoints.sqlite`.

`events.run_id` logically references `runs.id`, but SQLite does not enforce an FK. `writes` logically associates with `checkpoints` using `(thread_id, checkpoint_ns, checkpoint_id)`; no FK is declared. `parent_checkpoint_id` records checkpoint ancestry within the same thread and namespace. `runs.id` is a hash of owner and external run ID, so it must not be drawn as an FK to Laravel `intelligent_news_runs.id`. SQLite permits NULL in some non-integer primary key declarations here; application code supplies IDs.

## Chroma vector collections

| Collection | Stored attributes |
|---|---|
| `approved_information_<embedding fingerprint>` | id (SHA-256 of owner_id:information_id), embedding, document (serialized KnowledgeItem), metadata: owner_id, information_id, document_id, review_status, is_active, archived |
| `apakhabar_documents` | id (document_id:chunk_index), embedding, document (chunk text), metadata: document_id, filename, source, chunk_index |

KnowledgeItem document fields: `information_id`, `document_id`, `owner_id`, `title`, `summary`, `labels`, `fields`, `evidence`, `source`, `review_status`, `is_active`, `archived`. These are vector-store records, not relational SQL tables. References to Laravel records are application-level only. Raw-document collection code is present; this inventory does not claim it is populated or used by the approved-evidence agent flow.

## Schema details to preserve in your report

- Drafts now use `title`, `excerpt`, and `content`; the old `headline`, `subheadline`, `lead`, and `body` columns are not in the final schema.
- `two_factors` is retained as a legacy table. Its enrollment data is copied into `users` by the Fortify migration; active authentication uses `users`.
- The latest cleanup removes `comments.moderator_id`, `short_video_comments.moderator_id`, and `short_video_comments.moderation_assessment`. `comment_moderation_history.moderator_id` remains without an enforced FK.
- Both report tables now store `category` and `explanation`; their old `reason` columns are removed.
- `comment_moderation_assessments` and `comment_moderation_feedback` are retired; their `archived_...` replacements preserve snapshots without foreign keys. `comment_flags` is the active moderator flag table.
- Guest identity tables are present, but comments have no guest_id FK; no link is invented.
- The overview is deliberately selective. Every relational table and column appears on its detailed page.
- JSON arrays such as selected document/information IDs and meta connection IDs are attributes, not normalized junction tables or enforced FKs.
- `news_visits` has only `id` and `expires_at`; do not invent a news_id relationship.

## Reusable diagram prompt

Create an editable crow's-foot ERD from the attached schema.json and database dictionary. Preserve every exact table and attribute name. Display PK, FK, single-column unique keys, composite constraints, and nullable parent relationships. Group tables into Accounts, Broadcasts and notifications, News and moderation, Intelligence and drafting, AI conversations, Social and analytics, Laravel infrastructure, and AI service SQLite. Use separate pages and key-only reference boxes for cross-page entities. Draw solid lines only for foreign_keys in schema.json. Draw the documented AI logical relationships as dashed lines explicitly marked 'logical; no FK'. Keep Chroma collections in a separate non-relational section. Do not infer foreign keys from column names or JSON arrays, and do not restore removed legacy draft columns.

## Sources

- Laravel: `database/migrations/*.php` in ApaKhabar-Intelligence-Information-News-Management-System.
- AI service: `app/services/agent_service.py`, `app/services/extraction_progress.py`, `app/services/knowledge_service.py`, `app/services/rag_service.py`, `app/schemas/knowledge.py`.
- Installed LangGraph schema: `.venv/lib/python3.12/site-packages/langgraph/checkpoint/sqlite/__init__.py`.
''')
(out/'database-dictionary.md').write_text('\n'.join(md))
mer.extend(['    runs ||..o{ events : "logical_run_id_no_FK"', '    checkpoints ||..o{ writes : "logical_checkpoint_key_no_FK"'])
(out/'apakhabar-erd.mmd').write_text('\n'.join(mer)+'\n')
(out/'schema.json').write_text(json.dumps(s,indent=2))

# Editable native draw.io cells, with one attribute per row and visible unique constraints.
mx=E.Element('mxfile',host='app.diagrams.net')
svg_ns='http://www.w3.org/2000/svg'
previews=out/'previews'; previews.mkdir(exist_ok=True)
def cell(root,id,value,style,parent='1',**attrs):
 return E.SubElement(root,'mxCell',id=id,value=value,style=style,parent=parent,**attrs)
def geom(c,x,y,w,h):
 E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
def parent_range(t,f):
 return '0..1' if any(c['nullable'] for c in t['columns'] if c['name'] in f['columns']) else '1'
def child_range(t,f):
 return '0..1' if any(i['unique'] and set(i['columns']).issubset(f['columns']) for i in t['indexes']) else '0..N'
def esc(x): return html.escape(str(x),quote=True)
owner={n:g for g,names in groups.items() for n in names}
scenes=[]
def page(title,names,overview=False):
 refs=[] if overview else sorted({f['foreign_table'] for n in names for f in s[n]['foreign_keys']}-set(names))
 order=names+refs
 entries=[]
 for n in order:
  t=s[n]; ref=n in refs
  cols=[c for c in t['columns'] if 'PK' in keys(t,c['name'])] if ref or overview else t['columns']
  uq=[] if ref or overview else ['UQ: '+', '.join(i['columns']) for i in t['indexes'] if i['unique'] and not i['primary'] and len(i['columns'])>1]
  note=('REF · '+owner[n]) if ref else ('KEYS ONLY · '+owner[n]) if overview else 'PK primary · FK foreign · UK unique · ? nullable'
  color='#334155' if ref else '#92400e' if 'Archives' in title else '#0f766e' if 'SQLite' in title else '#1e40af'
  height=72+24*len(cols)+24*len(uq)
  entries.append(dict(n=n,cols=cols,uq=uq,note=note,color=color,h=height,ref=ref))
 cols_per_row=3; width=560; gap=230; y=260
 for k in range(0,len(entries),cols_per_row):
  row=entries[k:k+cols_per_row]
  for j,e in enumerate(row): e.update(x=200+j*(width+gap),y=y,w=width,row=k//cols_per_row,col=j)
  y+=max(e['h'] for e in row)+170
 positions={e['n']:e for e in entries}
 d=E.SubElement(mx,'diagram',name=title,id='page-'+str(len(mx)))
 model=E.SubElement(d,'mxGraphModel',grid='1',gridSize='10',page='0',background='#f8fafc'); root=E.SubElement(model,'root'); E.SubElement(root,'mxCell',id='0'); E.SubElement(root,'mxCell',id='1',parent='0')
 geom(cell(root,'title',title,'text;html=0;fontSize=30;fontStyle=1;align=left;fontColor=#0f172a;',vertex='1'),50,25,2200,45)
 subtitle='Selected core entities and relationships — open numbered pages for the complete schema.' if overview else 'All attributes shown. Grey boxes reference another page. Parent / child labels give exact cardinality; dashed lines are logical only.'
 geom(cell(root,'subtitle',subtitle,'text;html=0;fontSize=14;align=left;fontColor=#475569;',vertex='1'),50,80,2200,40)
 svg=[f'<svg xmlns="{svg_ns}" width="{200+3*(width+gap)}" height="{y}" viewBox="0 0 {200+3*(width+gap)} {y}"><rect width="100%" height="100%" fill="#f8fafc"/>',f'<text x="50" y="60" font-family="Arial" font-size="30" font-weight="bold">{esc(title)}</text>',f'<text x="50" y="100" font-family="Arial" font-size="16" fill="#475569">{esc(subtitle)}</text>']
 edges=[]
 for n in names:
  for f in s[n]['foreign_keys']:
   if overview and not set(f['columns']).intersection({'roleID','category_id','document_id','extraction_request_id','draft_id','information_id','published_news_id','session_id','newsID','short_video_id','connection_id'}): continue
   if f['foreign_table'] in positions: edges.append((f['foreign_table'],n,','.join(f['columns']),parent_range(s[n],f),child_range(s[n],f),False))
 if 'SQLite' in title:
  edges += [('runs','events','run_id → id','1','0..N',True),('checkpoints','writes','thread_id + checkpoint_ns + checkpoint_id','1','0..N',True)]
 for i,(src,dst,label,pr,cr,logical) in enumerate(edges):
  a,b=positions[src],positions[dst]; sy=a['y']+45+(i%3)*14; ty=b['y']+45+(i%3)*14
  sx=a['x']+width; tx=b['x'] if a['col']!=b['col'] else b['x']+width
  lane=sx+30+(i%6)*22
  if src==dst:
   points=[(lane,sy),(lane,a['y']-28),(a['x']+width/2,a['y']-28),(a['x']+width/2,a['y'])]; tx=a['x']+width/2; ty=a['y']
  elif a['col']==b['col']: points=[(lane,sy),(lane,ty)]
  else:
   gy=min(a['y'],b['y'])-35-(i%5)*20
   points=[(lane,sy),(lane,gy),(b['x']-30-(i%5)*18,gy),(b['x']-30-(i%5)*18,ty)]
  style='edgeStyle=none;rounded=0;html=0;fontSize=10;fontColor=#475569;strokeColor=#94a3b8;labelBackgroundColor=#f8fafc;'
  style+='startArrow='+('ERzeroToOne' if pr=='0..1' else 'ERmandOne')+';endArrow='+('ERzeroToOne' if cr=='0..1' else 'ERzeroToMany')+';'
  style+=f'exitX=1;exitY={(sy-a["y"])/a["h"]};entryX={1 if tx==b["x"]+width else 0.5 if src==dst else 0};entryY={(ty-b["y"])/b["h"]};'
  if logical: style+='dashed=1;'
  value=f'{label}\nparent {pr} / child {cr}'+ (' · logical, no FK' if logical else '')
  c=cell(root,'edge-'+str(i),value,style,edge='1',source=src,target=dst)
  g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'}); ar=E.SubElement(g,'Array',attrib={'as':'points'})
  for px,py in points: E.SubElement(ar,'mxPoint',x=str(px),y=str(py))
  path=[(sx,sy)]+points+[(tx,ty)]
  svg.append('<polyline points="'+' '.join(f'{x},{yy}' for x,yy in path)+'" fill="none" stroke="#94a3b8" stroke-width="1.5"'+(' stroke-dasharray="6 4"' if logical else '')+'/>')
  # Exact cardinalities remain readable beside endpoints in the static preview.
  svg.append(f'<text x="{sx+5}" y="{sy-5}" font-family="Arial" font-size="11" fill="#475569">{esc(pr)}</text><text x="{tx-25}" y="{ty-5}" font-family="Arial" font-size="11" fill="#475569">{esc(cr)}</text>')
 for e in entries:
  n=e['n']; x,y0,w,h=e['x'],e['y'],e['w'],e['h']; t=s[n]
  c=cell(root,n,'','rounded=0;fillColor=#ffffff;strokeColor=#cbd5e1;container=1;collapsible=0;',vertex='1'); geom(c,x,y0,w,h)
  geom(cell(root,n+'-header',n,'rounded=0;html=0;align=left;spacingLeft=12;fontSize=16;fontStyle=1;fontColor=#ffffff;fillColor='+e['color']+';strokeColor=none;',parent=n,vertex='1'),0,0,w,40)
  geom(cell(root,n+'-note',e['note'],'text;html=0;align=left;spacingLeft=12;fontSize=11;fontColor=#64748b;',parent=n,vertex='1'),0,40,w,28)
  svg += [f'<rect x="{x}" y="{y0}" width="{w}" height="{h}" fill="white" stroke="#cbd5e1"/>',f'<rect x="{x}" y="{y0}" width="{w}" height="40" fill="{e["color"]}"/>',f'<text x="{x+12}" y="{y0+26}" font-family="Arial" font-weight="bold" font-size="16" fill="white">{esc(n)}</text>',f'<text x="{x+12}" y="{y0+58}" font-family="Arial" font-size="11" fill="#64748b">{esc(e["note"])}</text>']
  for k,c in enumerate(e['cols']):
   row=68+k*24; key=keys(t,c['name']); name=c['name']+(' ?' if c['nullable'] else '')
   fill='#f1f5f9' if k%2==0 else '#ffffff'
   geom(cell(root,n+'-row-'+str(k),'','fillColor='+fill+';strokeColor=none;',parent=n,vertex='1'),1,row,w-2,24)
   for suffix,txt,xx,ww in [('key',key,8,76),('name',name,86,320),('type',c['type'],410,145)]:
    geom(cell(root,n+'-'+suffix+str(k),txt,'text;html=0;align=left;fontSize=12;fontColor='+('#1d4ed8' if suffix=='key' else '#0f172a')+';',parent=n,vertex='1'),xx,row,ww,24)
   svg += [f'<rect x="{x+1}" y="{y0+row}" width="{w-2}" height="24" fill="{fill}"/>',f'<text x="{x+8}" y="{y0+row+17}" font-family="Arial" font-size="12" fill="#1d4ed8">{esc(key)}</text>',f'<text x="{x+86}" y="{y0+row+17}" font-family="Arial" font-size="12">{esc(name)}</text>',f'<text x="{x+410}" y="{y0+row+17}" font-family="Arial" font-size="12" fill="#64748b">{esc(c["type"])}</text>']
  for k,u in enumerate(e['uq']):
   row=68+24*len(e['cols'])+k*24
   geom(cell(root,n+'-uq-'+str(k),u,'text;html=0;align=left;spacingLeft=10;fontSize=11;fontColor=#7c3aed;',parent=n,vertex='1'),0,row,w,24)
   svg.append(f'<text x="{x+10}" y="{y0+row+17}" font-family="Arial" font-size="11" fill="#7c3aed">{esc(u)}</text>')
 svg.append('</svg>'); slug=title.lower().replace(' ','-')
 (previews/(slug+'.svg')).write_text('\n'.join(svg))
 scenes.append((title,entries,edges))
page('00 Core overview',['user_roles','users','news_categories','intelligence_documents','intelligence_extraction_requests','intelligence_information','intelligent_news_drafts','intelligent_news_draft_sources','news','intelligent_news_sessions','intelligent_news_messages','comments','short_videos','short_video_publications','social_connections'],True)
for title,names in groups.items(): page(title,names)
E.indent(mx); E.ElementTree(mx).write(out/'apakhabar-erd.drawio',encoding='utf-8',xml_declaration=True)
# Validate schema coverage, foreign keys, XML references and box layout.
for title,entries,edges in scenes:
 for i,a in enumerate(entries):
  for b in entries[i+1:]:
   assert a['x']+a['w']<=b['x'] or b['x']+b['w']<=a['x'] or a['y']+a['h']<=b['y'] or b['y']+b['h']<=a['y'], (title,a['n'],b['n'])
for d in mx:
 cells=d.findall('.//mxCell'); ids=[c.get('id') for c in cells]; assert len(ids)==len(set(ids))
 for c in cells:
  assert c.get('parent','0') in ids
  if c.get('edge'): assert c.get('source') in ids and c.get('target') in ids
for n,t in s.items():
 for f in t['foreign_keys']:
  assert set(f['columns'])<={c['name'] for c in t['columns']}
  assert set(f['foreign_columns'])<={c['name'] for c in s[f['foreign_table']]['columns']}
assert 'comment_moderation_feedback' not in s and 'comment_moderation_assessments' not in s
assert 'moderator_id' not in [c['name'] for c in s['comments']['columns']]
assert 'reason' not in [c['name'] for c in s['comment_reports']['columns']]
print(f'Validated {len(mx)} pages, {laravel_count} Laravel + {len(s)-laravel_count} AI SQLite tables, {sum(len(t["columns"]) for t in s.values())} attributes, {sum(len(t["foreign_keys"]) for t in s.values())} enforced FKs. No overlapping entity boxes.')
