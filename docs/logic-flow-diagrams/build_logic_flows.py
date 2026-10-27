"""Create conventional logic flowcharts from the source-traced activity specifications."""
import pathlib,xml.etree.ElementTree as E,copy,html,textwrap,zipfile
O=pathlib.Path(__file__).resolve().parent
# Load only the declarative workflow definitions, without regenerating other artifacts.
source=(O.parent/'activity-diagrams/build_activities.py').read_text()
ns={"__file__":str(O.parent/"activity-diagrams/build_activities.py")};exec(source[:source.index("mx=E.Element('mxfile'")],ns)
specs=ns['specs']
inputs={'01-news-generation':{'input','approve','answer','supply'},'02-review-finalize':{'edit','confirm'},'03-publish-news':{'select','confirm'},'04-engagement-moderation':{'comment','report','like'},'05-monitor-analytics':{'filters'}}
errors={'err','fix','correct','denied','resolve','reload','error','fail'}
# Convert the choice that has a single outgoing arrow into a process: the status mapping occurs later.
for s in specs:
 if s['slug']=='04-engagement-moderation':
  s['nodes']=[(id,l,row,'action' if id=='decision' else kind,'Select Allow or Hide' if id=='decision' else label) for id,l,row,kind,label in s['nodes']]
mx=E.Element('mxfile',host='app.diagrams.net')
for s in specs:
 width=1340;step=145;offset=125
 # Preserve branch grouping but remove responsibility lanes; actor prefixes make ownership explicit.
 pos={};maxrow=max(n[2] for n in s['nodes']);height=offset+(maxrow+1)*step+100
 model=E.Element('mxGraphModel',grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',page='0')
 root=E.SubElement(model,'root');E.SubElement(root,'mxCell',id='0');E.SubElement(root,'mxCell',id='1',parent='0')
 def vertex(id,label,style,x,y,w,h):
  c=E.SubElement(root,'mxCell',id=id,value=label,vertex='1',parent='1',style=style);E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
 vertex('title',s['title']+' — Logic Flow','text;html=0;align=center;fontSize=25;fontStyle=1;',30,20,width-60,45)
 vertex('legend','START / END  •  Process  •  Input / Output  •  Decision  •  Labelled alternate and retry paths','text;html=0;align=center;fontSize=13;fontColor=#555555;',30,70,width-60,30)
 for id,l,row,kind,label in s['nodes']:
  if kind in ['start','end']:kind='terminal';label='START' if id=='s' else 'END';w,h=180,55
  elif kind=='decision':w,h=170,100
  else:w,h=270,88;kind='io' if id in inputs[s['slug']] else 'process'
  if kind not in ['terminal','decision']:
   who=s['lanes'][l]
   who='User' if who in ['Moderator / Administrator','Reader / Villager','Administrator'] else 'Moderator' if 'Moderator' in who else 'AI service' if 'AI' in who else 'Background sync' if 'Meta' in who else 'System'
   label=who+': '+label
   if id in errors:label='Display issue / correction\n'+label
  if kind=='io':label='INPUT\n'+label
  x=235+l*400-w/2;y=offset+row*step
  pos[id]=(x,y,w,h,kind,label,l)
  style={'terminal':'rounded=1;arcSize=50;fillColor=#eeeeee;strokeColor=#999999;','decision':'rhombus;fillColor=#ffffff;strokeColor=#333333;','io':'shape=parallelogram;perimeter=parallelogramPerimeter;fixedSize=1;fillColor=#ffffff;strokeColor=#333333;','process':'rounded=0;fillColor=#ffffff;strokeColor=#333333;'}[kind]
  vertex(id,label,style+'whiteSpace=wrap;html=0;strokeWidth=2;fontSize=14;',x,y,w,h)
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10z"/></marker></defs><rect width="100%" height="100%" fill="white"/>',f'<text x="{width/2}" y="50" text-anchor="middle" font-family="Arial" font-size="25" font-weight="bold">{html.escape(s["title"])} — Logic Flow</text>',f'<text x="{width/2}" y="87" text-anchor="middle" font-family="Arial" font-size="13" fill="#555">START / END • Process • Input / Output • Decision • Alternate and retry paths</text>']
 for j,(a,b,label,*route) in enumerate(s['edges']):
  x,y,w,h,ka,_,la=pos[a];xx,yy,ww,hh,kb,_,lb=pos[b];track=route[0] if route else None
  if track:
   left=track=='left';sx,sy=(x if left else x+w),y+h/2;tx,ty=(xx if left else xx+ww),yy+hh/2
   rail=35+(j%4)*12 if left else width-35-(j%4)*12 if track=='right' else 435+la*400-15
   pts=[(sx,sy),(rail,sy),(rail,ty),(tx,ty)]
  elif la==lb:
   sx,sy=x+w/2,y+h;tx,ty=xx+ww/2,yy;pts=[(sx,sy),(tx,ty)]
  elif y==yy:
   sx,sy=(x+w if lb>la else x),y+h/2;tx,ty=(xx if lb>la else xx+ww),yy+hh/2;pts=[(sx,sy),(tx,ty)]
  else:
   sx,sy=x+w/2,y+h;tx,ty=xx+ww/2,yy;mid=(sy+ty)/2;pts=[(sx,sy),(sx,mid),(tx,mid),(tx,ty)]
  c=E.SubElement(root,'mxCell',id='edge'+str(j),value=label,edge='1',parent='1',source=a,target=b,style=f'edgeStyle=none;rounded=0;endArrow=block;endFill=1;html=0;strokeWidth=1.5;fontSize=12;labelBackgroundColor=#ffffff;exitX={(sx-x)/w};exitY={(sy-y)/h};entryX={(tx-xx)/ww};entryY={(ty-yy)/hh};')
  g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});arr=E.SubElement(g,'Array',attrib={'as':'points'})
  for px,py in pts[1:-1]:E.SubElement(arr,'mxPoint',x=str(px),y=str(py))
  svg.append('<polyline points="'+' '.join(f'{px},{py}' for px,py in pts)+'" fill="none" stroke="#333" stroke-width="1.5" marker-end="url(#a)"/>')
  if label:
   px,py=pts[0];qx,qy=pts[1];lx=(px+qx)/2;ly=(py+qy)/2-7
   svg.append(f'<rect x="{lx-len(label)*3.7}" y="{ly-13}" width="{len(label)*7.4}" height="18" fill="white"/><text x="{lx}" y="{ly}" text-anchor="middle" font-family="Arial" font-size="12">{html.escape(label)}</text>')
 for id,(x,y,w,h,kind,label,l) in pos.items():
  if kind=='decision':svg.append(f'<polygon points="{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}" fill="white" stroke="#333" stroke-width="2"/>')
  elif kind=='io':svg.append(f'<polygon points="{x+24},{y} {x+w},{y} {x+w-24},{y+h} {x},{y+h}" fill="white" stroke="#333" stroke-width="2"/>')
  else:svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{25 if kind=="terminal" else 0}" fill="{"#eeeeee" if kind=="terminal" else "white"}" stroke="{"#999" if kind=="terminal" else "#333"}" stroke-width="2"/>')
  lines=[]
  for t in label.split('\n'):lines+=textwrap.wrap(t,17 if kind=='decision' else 29 if kind=='io' else 33)
  for k,t in enumerate(lines):svg.append(f'<text x="{x+w/2}" y="{y+h/2-(len(lines)-1)*8+k*16+5}" text-anchor="middle" font-family="Arial" font-size="14">{html.escape(t)}</text>')
 svg.append('</svg>');(O/(s['slug']+'.svg')).write_text(''.join(svg))
 E.indent(model);E.ElementTree(model).write(O/(s['slug']+'.xml'),encoding='utf-8',xml_declaration=True)
 single=E.Element('mxfile',host='app.diagrams.net');d=E.SubElement(single,'diagram',id=s['slug'],name=s['title']);d.append(copy.deepcopy(model));E.ElementTree(single).write(O/(s['slug']+'.drawio'),encoding='utf-8',xml_declaration=True)
 d=E.SubElement(mx,'diagram',id=s['slug'],name=s['title']);d.append(copy.deepcopy(model))
 ids={c.get('id') for c in root};assert len(ids)==len(root)
 for c in root:
  if c.get('edge'):assert c.get('source') in ids and c.get('target') in ids
 seen={'s'}
 while True:
  nxt=seen|{b for a,b,*_ in s['edges'] if a in seen}
  if nxt==seen:break
  seen=nxt
 assert set(pos)<=seen
 for id,(_,_,_,_,kind,_,_) in pos.items():
  outgoing=[e for e in s['edges'] if e[0]==id]
  if kind=='decision':assert len(outgoing)>=2 and all(e[2] for e in outgoing),(s['slug'],id)
  if id!='s' and kind=='terminal':assert not outgoing
E.indent(mx);E.ElementTree(mx).write(O/'news-logic-flow-diagrams.drawio',encoding='utf-8',xml_declaration=True)
(O/'README.md').write_text('''# News logic-flow diagrams

Five conventional flowcharts match the supplied registration-flow sample: grey START/END terminators, rectangular processes, input parallelograms, decision diamonds, labelled alternatives and return paths. There are no swimlanes. Actor prefixes explain responsibility.

Open **news-logic-flow-diagrams.drawio** for all five pages:

1. News Generation
2. Review and Finalize News Post
3. Publishing News Post
4. News Post Engagement and Moderation
5. Monitor News Analytics

Individual `.drawio` files, raw `.xml` (mxGraphModel) and `.svg` previews are supplied. These share the source-traced logic of the activity diagrams; consult `../activity-diagrams/use-case-descriptions.md` for preconditions, postconditions, code sources and scope.

The diagrams describe user-level workflows rather than every exception or internal method. The engagement options are alternative interactions, not mandatory sequential steps. Human review is asynchronous. Reviewing a draft does not remove a publication quality block. Meta metrics are read from stored snapshots and synchronization is separate.

Validation checks XML, unique IDs, connector endpoints, reachability, labelled branches on all decisions, and terminal nodes. Representative SVGs are rendered for layout inspection. No application or database changes are made.

Rebuild: `python3 docs/logic-flow-diagrams/build_logic_flows.py`.
''')
print('Generated five flowcharts. All decisions have labelled alternatives; endpoints and reachability validated.')
