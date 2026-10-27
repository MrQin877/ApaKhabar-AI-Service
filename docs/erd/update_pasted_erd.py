"""Reconcile the supplied diagram with the exported migration schema, preserving its visual style."""
import collections, copy, html, json, pathlib, xml.etree.ElementTree as E
out=pathlib.Path(__file__).resolve().parent
source=pathlib.Path('/Users/mrqin877/.codex/attachments/2709ba65-7e5e-4afc-b095-dcf846ece0fe/Pasted text.txt')
original=E.parse(source).getroot()
schema=json.load(open('/tmp/apakhabar-erd-current.json'))
for t in schema.values():
 if isinstance(t['indexes'],dict):t['indexes']=list(t['indexes'].values())
cells=original.findall('.//mxCell'); byid={c.get('id'):c for c in cells}; children=collections.defaultdict(list)
for c in cells:children[c.get('parent')].append(c)
tables=[c for c in cells if 'shape=table;' in c.get('style','')]
mapping=['intelligence_documents','users','emails','phones','two_factors','user_roles','personal_access_tokens','password_reset_tokens','news','news_categories','comments','likes','broadcasts','broadcast_categories','broadcast_user','channels','notifications','intelligent_news_drafts','intelligence_extraction_requests','intelligent_news_draft_sources','intelligent_news_draft_versions','intelligence_information','ai_quality_evaluations','intelligent_news_sessions','intelligent_news_run_events','intelligent_news_messages','intelligent_news_source_selections','intelligent_news_runs','archived_comment_moderation_assessments','archived_comment_moderation_feedback','news_viewers',None]
assert len(mapping)==len(tables)
styles={}
styles['table']=tables[0].get('style')
row=children[tables[0].get('id')][0]; styles['row']=row.get('style')
styles['key']=children[row.get('id')][0].get('style'); styles['name']=children[row.get('id')][1].get('style')
styles['name']=styles['name'].replace('fontStyle=5;','fontStyle=0;')
# Expand coordinates around the original top-left anchor, preserving each entity's relative placement.
positions={}; labels={}; oldrows={}
for t,n in zip(tables,mapping):
 if not n:continue
 g=t.find('mxGeometry'); positions[n]=(100+(float(g.get('x'))-520)*2.3,220+(float(g.get('y'))-420)*2.3)
 labels[n]=t.get('value'); oldrows[n]=[ ' | '.join(c.get('value','') for c in children[r.get('id')]) for r in children[t.get('id')] if 'shape=tableRow;' in r.get('style','')]
W=380; RH=30

def constraints(n):
 return [i for i in schema[n]['indexes'] if i['unique'] and not i['primary'] and len(i['columns'])>1]
def height(n):return 30+RH*len(schema[n]['columns'])+RH*len(constraints(n))
# Move only vertically where the corrected field count would create an overlap.
for n in sorted(positions,key=lambda n:positions[n][1]):
 x,y=positions[n]
 while True:
  collisions=[m for m,(xx,yy) in positions.items() if m!=n and (yy<y or yy==y and m<n) and x<xx+W+30 and xx<x+W+30 and y<yy+height(m)+50 and yy<y+height(n)+50]
  if not collisions:break
  y=max(positions[m][1]+height(m)+80 for m in collisions)
 positions[n]=(x,y)
base=max(y+height(n) for n,(x,y) in positions.items())+220
missing=[n for n in schema if n not in positions]
groups=[('Additional broadcast and news tables',['broadcast_channel','comment_likes','comment_reports','comment_flags','comment_moderation_history','news_visits']),('Short videos and engagement',[n for n in missing if n.startswith('short_video')]),('Guest identities, social and analytics',['guest_comment_identities','guest_comment_days','social_connections','meta_insight_snapshots','analytics_settings','analytics_setting_changes','villager_activity_hours']),('Laravel infrastructure',['jobs','failed_jobs','migrations'])]
assert set(sum((ns for _,ns in groups),[]))==set(missing)
sections=[]
for title,ns in groups:
 sections.append((title,base)); base+=60
 for start in range(0,len(ns),6):
  batch=ns[start:start+6]
  for i,n in enumerate(batch):positions[n]=(100+i*600,base)
  base+=max(height(n) for n in batch)+160

def keys(n,col):
 t=schema[n]; key=[]
 if any(i['primary'] and col in i['columns'] for i in t['indexes']):key.append('PK')
 if any(col in f['columns'] for f in t['foreign_keys']):key.append('FK')
 if any(i['unique'] and not i['primary'] and i['columns']==[col] for i in t['indexes']):key.append('UK')
 return ','.join(key)
def vertex(root,id,value,style,parent,x,y,w,h):
 c=E.SubElement(root,'mxCell',id=id,value=value,style=style,parent=parent,vertex='1');E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'});return c
model=E.Element('mxGraphModel',dx='5237',dy='2944',grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='0',pageScale='1',pageWidth='827',pageHeight='1169',math='0',shadow='0')
root=E.SubElement(model,'root');E.SubElement(root,'mxCell',id='0');E.SubElement(root,'mxCell',id='1',parent='0')
vertex(root,'heading','ApaKhabar — updated physical database ERD','text;html=0;align=left;fontSize=28;fontStyle=1;','1',100,20,2200,50)
vertex(root,'legend','56 Laravel tables · 85 enforced foreign keys · PK / FK / UK · ? nullable · UQ(...) composite unique constraint\nConnectors point from parent key to child FK. Endpoint labels give min..max cardinality. Archives intentionally have no FK links.\nExisting relative arrangement retained with wider spacing; newly added modules appear below. Names match the current migration schema.','text;html=0;align=left;fontSize=15;whiteSpace=wrap;','1',100,75,2600,100)
for i,(label,y) in enumerate(sections):vertex(root,'section'+str(i),label,'text;html=0;fontSize=24;fontStyle=1;align=left;','1',100,y,3500,50)
ports={}
for n,(x,y) in positions.items():
 t=schema[n]; suffix=' [archive]' if n.startswith('archived_') else ' [legacy]' if n=='two_factors' else ''
 style=styles['table']+'fontSize=13;whiteSpace=wrap;fillColor=#ffffff;'
 vertex(root,n,n+suffix,style,'1',x,y,W,height(n))
 for k,c in enumerate(t['columns']):
  rid=n+'__'+c['name'];ports[n,c['name']]=rid
  vertex(root,rid,'',styles['row'],n,0,30+k*RH,W,RH)
  vertex(root,rid+'__key',keys(n,c['name']),styles['key']+'fontSize=11;',rid,0,0,65,RH)
  vertex(root,rid+'__name',c['name']+(' ?' if c['nullable'] else ''),styles['name']+'fontSize=12;',rid,65,0,W-65,RH)
 for k,idx in enumerate(constraints(n)):
  rid=n+'__uq'+str(k);vertex(root,rid,'',styles['row'],n,0,30+(len(t['columns'])+k)*RH,W,RH)
  vertex(root,rid+'__label','UQ('+', '.join(idx['columns'])+')','text;html=0;align=left;spacingLeft=8;fontSize=10;whiteSpace=wrap;',rid,0,0,W,RH)
# Connect row ports, not vague entity headers. Preserve conventional crow's-foot styling.
edges=[]
for n,t in schema.items():
 for j,f in enumerate(t['foreign_keys']):
  p=f['foreign_table']; optional=any(c['nullable'] for c in t['columns'] if c['name'] in f['columns'])
  unique=any(i['unique'] and set(i['columns']).issubset(f['columns']) for i in t['indexes'])
  pr='0..1' if optional else '1'; cr='0..1' if unique else '0..N'
  sx,sy=positions[p]; tx,ty=positions[n]
  right=tx>=sx
  style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;jettySize=auto;orthogonalLoop=1;strokeColor=#64748b;strokeWidth=1;fontSize=10;labelBackgroundColor=#ffffff;'
  style+='startArrow='+('ERzeroToOne' if optional else 'ERmandOne')+';endArrow='+('ERzeroToOne' if unique else 'ERzeroToMany')+';'
  style+=f'exitX={1 if right else 0};exitY=0.5;entryX={0 if right else 1};entryY=0.5;'
  id='fk__'+n+'__'+str(j)
  c=E.SubElement(root,'mxCell',id=id,value='',edge='1',parent='1',source=ports[p,f['foreign_columns'][0]],target=ports[n,f['columns'][0]],style=style)
  E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
  for end,text,xx in [('parent',pr,-0.85),('child',cr,0.85)]:
   label=E.SubElement(root,'mxCell',id=id+'__'+end,value=text,vertex='1',connectable='0',parent=id,style='edgeLabel;html=0;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;labelBackgroundColor=#ffffff;')
   g=E.SubElement(label,'mxGeometry',x=str(xx),y='-12',relative='1',attrib={'as':'geometry'});E.SubElement(g,'mxPoint',x='0',y='0',attrib={'as':'offset'})
  edges.append((p,n,f,pr,cr))
# Deliver the raw XML for Edit Diagram, as well as a standard draw.io wrapper.
E.indent(model);E.ElementTree(model).write(out/'pasted-erd-updated.xml',encoding='utf-8',xml_declaration=True)
mx=E.Element('mxfile',host='app.diagrams.net');d=E.SubElement(mx,'diagram',id='updated-user-layout',name='Updated original layout');d.append(copy.deepcopy(model))
# Smaller module pages remain available as an optional companion in the existing apakhabar-erd.drawio.
E.indent(mx);E.ElementTree(mx).write(out/'pasted-erd-updated.drawio',encoding='utf-8',xml_declaration=True)
for n,(x,y) in positions.items():
 for m,(xx,yy) in positions.items():
  if n>=m:continue
  assert x+W<=xx or xx+W<=x or y+height(n)<=yy or yy+height(m)<=y,(n,m)
cs=root.findall('mxCell');ids=[c.get('id') for c in cs];assert len(ids)==len(set(ids))
for c in cs:
 if c.get('parent'):assert c.get('parent') in ids
 if c.get('edge'):assert c.get('source') in ids and c.get('target') in ids
assert len(positions)==len(schema)==56 and len(edges)==85
assert len(ports)==sum(len(t['columns']) for t in schema.values())==526
report=['# Corrections to your pasted ERD','', 'The updated single-canvas diagram keeps the original rounded table shape, two-column PK/FK + attribute layout, and relative placement of the original entities. Coordinates are expanded and collisions resolved to accommodate corrected attributes. Exact physical table/column names replace conceptual aliases. The attachment is unchanged.','', '**Verified:** 56 Laravel tables, 526 attributes, 85 enforced foreign keys; all row-port endpoints exist and no table boxes overlap. Schema reconstructed from all 60 migrations in an isolated in-memory SQLite test database. Deployed migration status was not queried.','', '## Key corrections','', '- The second `Intelligent_News_Run_Events` box contains run fields: corrected to `intelligent_news_runs`.','- Removed the duplicate feedback shape. The remaining assessment/feedback shapes now represent `archived_comment_moderation_assessments` and `archived_comment_moderation_feedback`, with their actual archive attributes and no invented FKs.','- `Broadcast_Recipient` is replaced by the actual `broadcast_user` junction table. There is no recipient entity or broadcasts.recipientID column.','- The old `Broadcast_Channel` catalog shape becomes `channels`; added the separate `broadcast_channel` junction table.','- `View` becomes `news_viewers`, with exact `id` and `news_id` names.','- Added current user demographics and Fortify fields; retained `two_factors` labelled legacy.','- Corrected aliases and typos: the AI entities mostly use `id`, not documentID/draftID/etc.; corrected updated_at, deleted_at, unique_views, information_embedding_status, approval_note, and other mismatches.','- Removed deleted moderator/assessment attributes and obsolete report reason fields. Included report category/explanation and moderation-history action.','- Regenerated all foreign keys with row-level connectors; unique FKs show 0..1 children, and nullable FKs show 0..1 parents. Composite primary and unique keys are preserved.','', '## Added tables','']
report += ['- `'+n+'`' for n in missing]
report += ['', '## Original shape → current table','', '| Original shape | Current physical table |','|---|---|']
report += [f'| {t.get("value")} | `{n}` |' if n else f'| {t.get("value")} (duplicate) | Removed duplicate shape |' for t,n in zip(tables,mapping)]
report += ['', '## Scope','', 'This preserves the scope of your Laravel ERD. The five AI-service SQLite tables and Chroma collections remain documented in the separate complete ERD/dictionary. JSON lists are not treated as foreign keys. `comment_moderation_history.moderator_id` is not connected to users because no FK is declared. Archive references are historical values, not enforced relationships.','', 'Open `pasted-erd-updated.drawio` directly in draw.io. `pasted-erd-updated.xml` is the raw mxGraphModel if you prefer to paste XML.']
(out/'pasted-erd-changes.md').write_text('\n'.join(report)+'\n')
# Static preview preserves entity geometry. Draw.io is authoritative for automatic connector routing.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="'+str(max(x+W for x,y in positions.values())+100)+'" height="'+str(base)+'">','<rect width="100%" height="100%" fill="white"/>','<text x="100" y="65" font-family="Arial" font-size="34">Updated original layout — table placement preview</text>']
for n,(x,y) in positions.items():
 svg.append(f'<rect x="{x}" y="{y}" width="{W}" height="{height(n)}" rx="8" fill="white" stroke="#333"/>')
 svg.append(f'<text x="{x+W/2}" y="{y+20}" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold">{html.escape(n)}</text>')
 for k,c in enumerate(schema[n]['columns']):
  yy=y+30+k*RH
  svg.append(f'<text x="{x+5}" y="{yy+20}" font-family="Arial" font-size="11">{html.escape(keys(n,c["name"]))}</text><text x="{x+70}" y="{yy+20}" font-family="Arial" font-size="12">{html.escape(c["name"]+(" ?" if c["nullable"] else ""))}</text>')
for title,y in sections:svg.append(f'<text x="100" y="{y+30}" font-family="Arial" font-size="26">{html.escape(title)}</text>')
svg.append('</svg>');(out/'previews/pasted-erd-layout.svg').write_text('\n'.join(svg))
print(f'Validated {len(positions)} tables, {len(ports)} attributes, {len(edges)} FK connectors; {len(missing)} tables added; no table overlaps.')
