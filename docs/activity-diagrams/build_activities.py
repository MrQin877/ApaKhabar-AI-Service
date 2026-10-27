import pathlib,xml.etree.ElementTree as E,html,textwrap,copy,zipfile
O=pathlib.Path(__file__).resolve().parent
specs=[]
def add(slug,title,lanes,nodes,edges,pre,post):specs.append(dict(slug=slug,title=title,lanes=lanes,nodes=nodes,edges=edges,pre=pre,post=post))
# Node: id, lane, row, kind, label. Edge: source,target,label, optional outside return-track.
add('01-news-generation','News Generation',['Moderator / Administrator','System','AI Service'],[
('s',0,0,'start',''),('open',0,1,'action','Open AI news assistant'),('form',1,2,'action','Display conversation and source library'),('input',0,3,'action','Enter instruction; select sources\nor upload documents'),('valid',1,4,'decision','Input valid?'),('err',0,4,'action','Correct invalid input'),('docs',1,5,'decision','New documents?'),('extract',2,6,'action','Parse / extract document information'),('approve',0,7,'action','Review extracted information\nand approve suitable evidence'),('eligible',1,8,'action','Check source ownership, approval\nand availability; record request'),('research',2,9,'action','Retrieve evidence; plan and research'),('enough',2,10,'decision','Evidence sufficient?'),('supply',0,10,'action','Add evidence or revise request'),('clarify',2,11,'decision','Clarification needed?'),('questions',1,12,'action','Display questions / approval request'),('answer',0,13,'action','Submit answers or source decisions'),('write',2,14,'action','Generate draft; evaluate and revise'),('save',1,15,'action','Save draft, sources, version\nand quality evaluation'),('show',0,16,'action','View generated draft and warnings'),('e',0,17,'end','')],
[('s','open',''),('open','form',''),('form','input',''),('input','valid',''),('valid','err','NO'),('err','input','Retry','left'),('valid','docs','YES'),('docs','extract','YES'),('extract','approve',''),('approve','eligible',''),('docs','eligible','NO','middle'),('eligible','research',''),('research','enough',''),('enough','supply','NO'),('supply','input','Retry','left'),('enough','clarify','YES'),('clarify','questions','YES'),('questions','answer',''),('answer','research','Resume','right'),('clarify','write','NO','right'),('write','save',''),('save','show',''),('show','e','')],
'Signed-in, verified moderator or administrator; source access is checked.','Draft and supporting information saved. Generation does not publish news.')
add('02-review-finalize','Review and Finalize News Post',['Moderator / Administrator','System','AI Quality Review'],[
('s',0,0,'start',''),('open',0,1,'action','Open own draft'),('load',1,2,'action','Load content, sources, version\nand quality assessment'),('review',0,3,'action','Review facts, wording, category\nand image'),('change',0,4,'decision','Changes needed?'),('edit',0,5,'action','Edit content / category / image\nor request an AI revision'),('validate',1,6,'decision','Changes valid?'),('fix',0,6,'action','Correct validation errors'),('save',1,7,'action','Save new version; clear reviewed_at'),('eval',2,8,'action','Re-evaluate applicable AI draft\nagainst its evidence'),('result',1,9,'action','Display updated draft and quality result'),('confirm',0,10,'action','Confirm review of current version'),('mark',1,11,'action','Record reviewed_at for owned draft'),('blocked',1,12,'decision','Publication blocked?'),('resolve',0,12,'action','Resolve quality / evidence issues'),('ready',1,13,'action','Keep reviewed draft ready\nfor publication checks'),('e',0,14,'end','')],
[('s','open',''),('open','load',''),('load','review',''),('review','change',''),('change','edit','YES'),('edit','validate',''),('validate','fix','NO'),('fix','edit','Retry','left'),('validate','save','YES'),('save','eval',''),('eval','result',''),('result','review','Review again','right'),('change','confirm','NO','left'),('confirm','mark',''),('mark','blocked',''),('blocked','resolve','YES'),('resolve','edit','Revise','left'),('blocked','ready','NO'),('ready','e','')],
'User owns a draft that is still editable.','Current version reviewed; publication remains a separate operation. Review alone does not override a quality block.')
add('03-publish-news','Publishing News Post',['Moderator / Administrator','System','Facebook / Instagram'],[
('s',0,0,'start',''),('select',0,1,'action','Open reviewed draft; select\nwebsite and/or social platforms'),('preview',1,2,'action','Prepare platform previews\nand identify publishing issues'),('confirm',0,3,'action','Check previews and confirm publishing'),('check',1,4,'decision','Publication checks pass?'),('correct',0,4,'action','Correct draft / review / connection\nissues; reopen preview'),('next',1,5,'action','Select next requested platform'),('web',1,6,'decision','Website target?'),('create',1,7,'action','Create active news record\nor reuse existing published ID'),('social',2,7,'action','Publish media and text through\nselected platform API'),('response',2,8,'decision','Provider successful?'),('fail',1,9,'action','Record safe platform failure'),('success',1,10,'action','Record success and published ID\nwhen available'),('more',1,11,'decision','More platforms?'),('merge',1,12,'action','Merge per-platform publication results'),('show',0,13,'action','View success / partial failure results'),('retry',0,14,'decision','Retry failed targets?'),('e',0,15,'end','')],
[('s','select',''),('select','preview',''),('preview','confirm',''),('confirm','check',''),('check','correct','NO'),('correct','select','Retry','left'),('check','next','YES'),('next','web',''),('web','create','YES'),('web','social','NO'),('social','response',''),('response','fail','NO'),('response','success','YES','right'),('create','success','','middle'),('fail','more','','left'),('success','more',''),('more','next','YES','middle'),('more','merge','NO'),('merge','show',''),('show','retry',''),('retry','select','YES','left'),('retry','e','NO')],
'Owned draft; current-version review or supported review confirmation; applicable category, quality and preview checks.','Per-platform results retained. Existing published IDs prevent repeated creation. Some targets may succeed while others fail.')
add('04-engagement-moderation','News Post Engagement and Moderation',['Reader / Villager','System','Moderator / Administrator'],[
('s',0,0,'start',''),('read',0,1,'action','Open published news article'),('display',1,2,'action','Display article and visible comments;\nissue engagement token'),('choose',0,3,'decision','Engagement action?'),('like',0,4,'action','Like / unlike post or comment'),('toggle',1,4,'action','Require login; toggle like\nand return updated count'),('comment',0,6,'action','Submit comment or reply'),('validate',1,7,'decision','Submission eligible?'),('fix',0,7,'action','Correct input / challenge / quota\nor sign in'),('moderate',1,8,'action','Check duplicates; run moderation\nAPI and link/promotion checks'),('clean',1,9,'decision','Clean valid result?'),('publish',1,10,'action','Save published comment\nand initial history'),('hold',2,10,'action','Comment awaits human review\n(pending_review)'),('report',0,12,'action','Report published comment\n(login required)'),('record',1,12,'action','Save report; add to review queue\nwithout auto-hiding comment'),('review',2,13,'action','Inspect pending / reported / flagged\ncomment and supporting history'),('decision',2,14,'decision','Allow or hide?'),('apply',1,15,'action','Authorize reviewer; lock comment;\ncheck revision / valid transition'),('conflict',1,16,'decision','Conflict detected?'),('reload',2,16,'action','Reload latest comment and review'),('commit',1,17,'action','Allow → published; hide → hidden;\nsave history and resolve reports/flags'),('done',0,18,'action','View updated public engagement state'),('e',0,19,'end','')],
[('s','read',''),('read','display',''),('display','choose',''),('choose','like','Like'),('like','toggle',''),('toggle','done','','right'),('choose','comment','Comment / reply','left'),('comment','validate',''),('validate','fix','NO'),('fix','comment','Retry','left'),('validate','moderate','YES'),('moderate','clean',''),('clean','publish','YES'),('clean','hold','NO'),('publish','done','','middle'),('hold','review','','right'),('choose','report','Report','left'),('report','record',''),('record','review',''),('review','decision',''),('decision','apply','Allow / hide'),('apply','conflict',''),('conflict','reload','YES'),('reload','review','Retry','right'),('conflict','commit','NO'),('commit','done',''),('done','e','')],
'Active article. Guests can comment subject to challenge and daily quota; likes/reports require authentication.','Engagement persisted. Unavailable/flagged/suspicious moderation stays pending. Reports alone do not hide comments. View tracking is automatic and token-validated.')
add('05-monitor-analytics','Monitor News Analytics',['Administrator','System','Meta / Background Sync'],[
('s',0,0,'start',''),('open',0,1,'action','Open analytics dashboard'),('auth',1,2,'decision','Authorized administrator?'),('denied',0,2,'action','Access denied'),('enddenied',0,3,'end',''),('filters',0,4,'action','Choose date range, category,\nplatform and sorting'),('valid',1,5,'decision','Filters valid?'),('fix',0,5,'action','Correct filters / date range'),('query',1,6,'action','Read settings; aggregate news,\nlikes, comments and audience data'),('snap',1,7,'action','Read saved social metric snapshots\nand synchronization status'),('show',0,8,'action','Inspect charts, trends and post details'),('action',0,9,'decision','Next action?'),('export',1,10,'action','Prepare filtered CSV / XLSX report'),('download',0,11,'action','Download report'),('sync',2,12,'action','Run queued Meta sync; request\ndaily metrics for selected accounts'),('result',2,13,'decision','Valid metric data?'),('store',1,14,'action','Upsert snapshots; set ready\nand last-sync timestamp'),('error',2,14,'action','Record disconnected / no-data /\nunavailable status as applicable'),('refresh',0,15,'action','Refresh analytics to read saved results'),('e',0,17,'end','')],
[('s','open',''),('open','auth',''),('auth','denied','NO'),('denied','enddenied',''),('auth','filters','YES'),('filters','valid',''),('valid','fix','NO'),('fix','filters','Retry','left'),('valid','query','YES'),('query','snap',''),('snap','show',''),('show','action',''),('action','filters','Change filters','left'),('action','export','Export'),('export','download',''),('download','e','','left'),('action','sync','Sync social data','right'),('sync','result',''),('result','store','YES'),('result','error','NO'),('store','refresh',''),('error','refresh',''),('refresh','query','Reload','middle'),('action','e','Finish','left')],
'Authenticated and verified administrator. Analytics report access is distinct from the moderator operational dashboard.','Filtered report displayed or exported. Meta snapshots refresh separately; lifetime views are not date-period view counts.')

mx=E.Element('mxfile',host='app.diagrams.net')
for s in specs:
 lw=340;left=45;top=95;step=125;maxrow=max(n[2] for n in s['nodes']);height=top+90+(maxrow+1)*step;width=left+len(s['lanes'])*lw+45
 model=E.Element('mxGraphModel',grid='1',gridSize='10',guides='1',page='0');root=E.SubElement(model,'root');E.SubElement(root,'mxCell',id='0');E.SubElement(root,'mxCell',id='1',parent='0')
 def vertex(id,value,style,x,y,w,h,parent='1'):
  c=E.SubElement(root,'mxCell',id=id,value=value,style=style,vertex='1',parent=parent);E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'});return c
 vertex('pool',s['title'],'swimlane;html=0;startSize=30;horizontal=1;fillColor=#ffffff;strokeColor=#333333;fontStyle=1;fontSize=18;',left,top,len(s['lanes'])*lw,height-top-25)
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10z"/></marker></defs><rect width="100%" height="100%" fill="white"/>',f'<text x="{width/2}" y="40" text-anchor="middle" font-family="Arial" font-size="23" font-weight="bold">{html.escape(s["title"])}</text>']
 for i,l in enumerate(s['lanes']):
  vertex('lane'+str(i),l,'swimlane;html=0;startSize=30;fillColor=#ffffff;strokeColor=#555555;fontStyle=1;fontSize=15;',i*lw,30,lw,height-top-55,'pool')
  svg.append(f'<rect x="{left+i*lw}" y="{top}" width="{lw}" height="{height-top-25}" fill="none" stroke="#555"/><text x="{left+i*lw+lw/2}" y="{top+23}" text-anchor="middle" font-family="Arial" font-size="15" font-weight="bold">{html.escape(l)}</text>')
 pos={}
 for id,l,row,kind,text in s['nodes']:
  w,h=(32,32) if kind in ['start','end'] else (96,76) if kind=='decision' else (220,70)
  x=left+l*lw+(lw-w)/2;y=top+80+row*step
  pos[id]=(x,y,w,h,l,kind,text)
  style={'start':'ellipse;fillColor=#000000;strokeColor=#000000;','end':'shape=mxgraph.sysml.actFinal;fillColor=#000000;','decision':'rhombus;fillColor=#ffffff;','action':'rounded=1;arcSize=18;fillColor=#ffffff;'}[kind]+'whiteSpace=wrap;html=0;fontSize=14;strokeColor=#222222;'
  vertex(id,text,style,x-left-l*lw,y-top-30,w,h,'lane'+str(l))
 # Connectors first in SVG so node faces cover crossing segments. Return lanes at the outside edges.
 for j,edge in enumerate(s['edges']):
  a,b,label,*route=edge;x,y,w,h,la,ka,_=pos[a];xx,yy,ww,hh,lb,kb,_=pos[b]
  backward=yy<=y;track=route[0] if route else None
  if track:
   sx,sy=(x,y+h/2) if track=='left' else (x+w,y+h/2)
   tx,ty=(xx,yy+hh/2) if track=='left' else (xx+ww,yy+hh/2)
   rail=left+12+(j%3)*10 if track=='left' else left+len(s['lanes'])*lw-12-(j%3)*10 if track=='right' else left+(la+1)*lw-15
   pts=[(sx,sy),(rail,sy),(rail,ty),(tx,ty)]
  elif la==lb:
   sx,sy=x+w/2,y+h;tx,ty=xx+ww/2,yy;pts=[(sx,sy),(tx,ty)]
  elif abs(y-yy)<50:
   sx,sy=(x+w if lb>la else x),y+h/2;tx,ty=(xx if lb>la else xx+ww),yy+hh/2;pts=[(sx,sy),(tx,ty)]
  else:
   sx,sy=x+w/2,y+h;tx,ty=xx+ww/2,yy;mid=(sy+ty)/2;pts=[(sx,sy),(sx,mid),(tx,mid),(tx,ty)]
  c=E.SubElement(root,'mxCell',id='edge'+str(j),value=label,edge='1',parent='1',source=a,target=b,style=f'edgeStyle=none;endArrow=block;endFill=1;html=0;fontSize=12;labelBackgroundColor=#ffffff;exitX={(sx-x)/w};exitY={(sy-y)/h};entryX={(tx-xx)/ww};entryY={(ty-yy)/hh};'+('dashed=1;' if backward or label in ['NO','Retry'] else ''))
  g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});ar=E.SubElement(g,'Array',attrib={'as':'points'})
  for px,py in pts[1:-1]:E.SubElement(ar,'mxPoint',x=str(px),y=str(py))
  svg.append('<polyline points="'+' '.join(f'{px},{py}' for px,py in pts)+'" fill="none" stroke="#333" marker-end="url(#a)"'+(' stroke-dasharray="5 4"' if backward or label in ['NO','Retry'] else '')+'/>')
  if label:
   px,py=pts[0];qx,qy=pts[1];lx=(px+qx)/2;ly=(py+qy)/2-6
   svg.append(f'<rect x="{lx-len(label)*3.4}" y="{ly-12}" width="{len(label)*6.8}" height="17" fill="white"/><text x="{lx}" y="{ly}" text-anchor="middle" font-family="Arial" font-size="12">{html.escape(label)}</text>')
 for id,(x,y,w,h,l,kind,text) in pos.items():
  if kind in ['start','end']:
   svg.append(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="{w/2}" fill="{"white" if kind=="end" else "black"}" stroke="black"/>')
   if kind=='end':svg.append(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="{w/2-5}" fill="black"/>')
  elif kind=='decision':svg.append(f'<polygon points="{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}" fill="white" stroke="#222"/>')
  else:svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="white" stroke="#222"/>')
  if text:
   lines=[]
   for t in text.split('\n'):lines+=textwrap.wrap(t,13 if kind=='decision' else 28)
   fs=12 if kind=='decision' else 14
   for k,line in enumerate(lines):svg.append(f'<text x="{x+w/2}" y="{y+h/2-(len(lines)-1)*8+k*16+4}" text-anchor="middle" font-family="Arial" font-size="{fs}">{html.escape(line)}</text>')
 svg.append('</svg>');(O/(s['slug']+'.svg')).write_text(''.join(svg))
 E.indent(model);E.ElementTree(model).write(O/(s['slug']+'.xml'),encoding='utf-8',xml_declaration=True)
 single=E.Element('mxfile',host='app.diagrams.net');d=E.SubElement(single,'diagram',id=s['slug'],name=s['title']);d.append(copy.deepcopy(model));E.ElementTree(single).write(O/(s['slug']+'.drawio'),encoding='utf-8',xml_declaration=True)
 d=E.SubElement(mx,'diagram',id=s['slug'],name=s['title']);d.append(copy.deepcopy(model))
 ids={c.get('id') for c in root};assert len(ids)==len(root)
 for c in root:
  if c.get('edge'):assert c.get('source') in ids and c.get('target') in ids
 # Every activity must be reachable from the start, including alternative endings.
 seen={'s'}
 while True:
  more=seen|{b for a,b,*_ in s['edges'] if a in seen}
  if more==seen:break
  seen=more
 assert set(pos)<=seen,(s['slug'],set(pos)-seen)
E.indent(mx);E.ElementTree(mx).write(O/'news-use-case-activities.drawio',encoding='utf-8',xml_declaration=True)
md=['# News use-case activity diagrams','', 'These are UML swimlane activity diagrams for the five requested use cases, matching the supplied sample (not actor/ellipse use-case diagrams). Each includes an initial node, actions, decisions, labelled alternatives, retry paths and final nodes.','', 'Open `news-use-case-activities.drawio` for all five pages. Individual draw.io files, raw mxGraphModel XML and SVG previews are also included.','']
for s in specs:md += ['## '+s['title'],'','**Actors / lanes:** '+', '.join(s['lanes']), '', '**Precondition:** '+s['pre'],'','**Postcondition / scope:** '+s['post'],'']
md += ['## Source and modeling notes','','Source-traced from the current Laravel controllers/services: NewsCreatorController, NewsWorkspaceController, NewsGenerationService, InteractionService, CommentModeration, ModerationDecisionService, GuestCommentIdentity, AnalyticsController, AnalyticsReport and MetaInsights. AI generation is summarized at the use-case level rather than exposing every internal tool call.','','Publication gates are represented together: ownership, editable draft, reviewed current version, quality block, category where applicable, and preview validity/issues when supplied. Review does not guarantee publication eligibility. Eligible conflict approval does not automatically bypass the existing publish_blocked check.','','The engagement diagram presents alternative reader actions. Published comments can later be reported in a separate interaction; the reporting path is not required after every comment. Human review is asynchronous. Automatic news view tracking is described in the postcondition rather than expanded into a separate lane.','','Analytics uses saved social snapshots; a sync request dispatches background work (or runs inline with a sync queue driver). Failed/disconnected/no-data states are distinguished in notes; no unimplemented live refresh is assumed.','','Authorization failures, unexpected service exceptions, and all UI navigation options are not expanded at every step; these are report-level activity diagrams. No application code or database was changed.','','Validation: all nodes reachable, connector IDs/endpoints valid, XML parsed; representative SVG layouts rendered for visual inspection.']
(O/'use-case-descriptions.md').write_text('\n'.join(md))
print('Generated 5 activity diagrams; validated reachability and connector endpoints.')
