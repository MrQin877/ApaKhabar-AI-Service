import pathlib,xml.etree.ElementTree as E,base64,html,copy,textwrap
OUT=pathlib.Path(__file__).resolve().parent
W,H=2240,1540
mx=E.Element('mxfile',host='app.diagrams.net')
class Page:
 def __init__(self,name,w=W,h=H):
  self.w,self.h=w,h;self.name=name;self.nodes={};self.svg=[]
  self.model=E.Element('mxGraphModel',grid='1',gridSize='10',page='0',background='#ffffff');self.root=E.SubElement(self.model,'root');E.SubElement(self.root,'mxCell',id='0');E.SubElement(self.root,'mxCell',id='1',parent='0')
 def rect(self,id,x,y,w,h,fill='#ffffff',stroke='#cbd5e1',radius=14,dashed=False):
  c=E.SubElement(self.root,'mxCell',id=id,value='',vertex='1',parent='1',style=f'rounded={1 if radius else 0};arcSize=10;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;'+('dashed=1;' if dashed else ''))
  E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'});self.nodes[id]=(x,y,w,h)
  self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"'+(' stroke-dasharray="7 5"' if dashed else '')+'/>')
 def text(self,id,text,x,y,w,h,size=18,color='#0f172a',bold=False,align='left'):
  c=E.SubElement(self.root,'mxCell',id=id,value=text,vertex='1',parent='1',style=f'text;html=0;whiteSpace=wrap;align={align};verticalAlign=middle;fontFamily=Arial;fontSize={size};fontColor={color};fontStyle={1 if bold else 0};')
  E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
  lines=[]
  for line in text.split('\n'):lines+=textwrap.wrap(line,max(10,int(w/(size*.52)))) or ['']
  lh=size*1.3;yy=y+(h-len(lines)*lh)/2+size
  for i,line in enumerate(lines):self.svg.append(f'<text x="{x+w/2 if align=="center" else x+2}" y="{yy+i*lh}" font-family="Arial" font-size="{size}" fill="{color}" font-weight="{"bold" if bold else "normal"}" text-anchor="{"middle" if align=="center" else "start"}">{html.escape(line)}</text>')
 def icon(self,id,kind,x,y,size=50):
  raw=(OUT/'icons'/(kind+'.svg')).read_bytes();data=base64.b64encode(raw).decode()
  c=E.SubElement(self.root,'mxCell',id=id,value='',vertex='1',parent='1',style='shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=1;aspect=fixed;image=data:image/svg+xml;base64,'+data+';')
  E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(size),height=str(size),attrib={'as':'geometry'})
  self.svg.append(f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/svg+xml;base64,{data}"/>')
 def box(self,id,title,desc,x,y,w,h,icon=None,fill='#ffffff',stroke='#94a3b8'):
  self.rect(id,x,y,w,h,fill,stroke)
  if icon:self.icon(id+'-icon',icon,x+18,y+20,48)
  left=x+80 if icon else x+16;ww=w-(96 if icon else 32)
  self.text(id+'-title',title,left,y+12,ww,50,18,bold=True)
  self.text(id+'-desc',desc,x+16,y+70,w-32,h-78,16,color='#475569')
 def arrow(self,id,a,b,label,points,kind='runtime',labelxy=None):
  color={'runtime':'#334155','deploy':'#7c3aed','secret':'#0f766e','storage':'#0369a1'}[kind]
  # Explicit endpoints and waypoints make paths match the exported preview.
  c=E.SubElement(self.root,'mxCell',id=id,value='',edge='1',parent='1',style=f'edgeStyle=none;rounded=0;endArrow=block;endFill=1;strokeWidth=1.7;strokeColor={color};'+('dashed=1;' if kind in ['deploy','secret'] else ''))
  g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});E.SubElement(g,'mxPoint',x=str(points[0][0]),y=str(points[0][1]),attrib={'as':'sourcePoint'});E.SubElement(g,'mxPoint',x=str(points[-1][0]),y=str(points[-1][1]),attrib={'as':'targetPoint'})
  ar=E.SubElement(g,'Array',attrib={'as':'points'})
  for x,y in points[1:-1]:E.SubElement(ar,'mxPoint',x=str(x),y=str(y))
  # Named endpoints recorded as metadata; port positions remain explicitly editable.
  c.set('data-source',a);c.set('data-target',b)
  self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="1.7" marker-end="url(#arrow-{kind})"'+(' stroke-dasharray="7 5"' if kind in ['deploy','secret'] else '')+'/>')
  if label and labelxy:
   x,y,w,h=labelxy;self.rect(id+'-labelbg',x,y,w,h,'#ffffff','#ffffff',0);self.text(id+'-label',label,x,y,w,h,14,color=color,align='center')
 def save(self,slug):
  d=E.SubElement(mx,'diagram',id=slug,name=self.name);d.append(copy.deepcopy(self.model))
  defs=''.join(f'<marker id="arrow-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="{v}"/></marker>' for k,v in {'runtime':'#334155','deploy':'#7c3aed','secret':'#0f766e','storage':'#0369a1'}.items())
  (OUT/(slug+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}"><defs>{defs}</defs><rect width="100%" height="100%" fill="white"/>'+''.join(self.svg)+'</svg>')
  E.indent(self.model);E.ElementTree(self.model).write(OUT/(slug+'.xml'),encoding='utf-8',xml_declaration=True)
  cs=self.root.findall('mxCell');ids={c.get('id') for c in cs};assert len(ids)==len(cs)
  for c in cs:
   if c.get('edge'):assert c.get('data-source') in self.nodes and c.get('data-target') in self.nodes

p=Page('01 Azure architecture')
p.text('title','ApaKhabar | Microsoft Azure architecture',40,20,1700,55,32,bold=True)
p.text('subtitle','Proposed Azure deployment · Laravel application and existing self-hosted AI workflow retained',40,80,2050,35,18,color='#64748b')
# Structural grouping mirrors the original: clients left, backend/data center, AI right, CI/CD above.
p.rect('clients',40,200,320,420,'#fffaf5','#f0b878');p.text('clients-title','CLIENTS',65,210,270,35,16,color='#9a3412',bold=True)
p.box('users','Village users','Residents · Administrators',65,265,270,110,fill='#ffffff')
p.box('browser','Web browser','Inertia.js web interface',65,405,270,90)
p.box('mobile','Mobile application','HTTPS REST API',65,515,270,90)
p.rect('external',40,760,320,530,'#f4fcf7','#84cda5');p.text('external-title','EXTERNAL INTEGRATIONS',60,775,280,35,16,color='#166534',bold=True)
p.box('messaging','Messaging providers','SMS gateway\nWhatsApp service\nExpo push notifications',65,840,270,200)
p.box('meta','Meta platforms','Facebook · Instagram\nPublishing and Insights API',65,1080,270,150)
p.rect('azure',440,440,1760,1000,'#f5faff','#0078d4',22)
p.text('azure-title','MICROSOFT AZURE | Application deployment',470,455,1300,40,22,color='#0078d4',bold=True)
p.text('azure-note','Logical service grouping; network/subnet design omitted',470,497,1200,25,14,color='#64748b')
# CI/CD ecosystem boundary outside regional application grouping.
p.rect('cicd',950,145,1250,240,'#fbfaff','#a78bfa',14,True);p.text('ci-title','CI/CD · Azure DevOps + GitHub',975,153,900,35,17,color='#6d28d9',bold=True)
p.box('github','GitHub','Source repositories',980,220,230,125)
p.box('pipeline','Azure Pipelines','Test · build images\nDeploy / restart services',1320,220,330,125,icon='devops')
p.box('registry','Azure Container Registry','Versioned application\nand AI container images',1780,220,380,125,icon='registry')
p.box('gateway','Azure Application Gateway','HTTPS routing\nTLS termination · optional WAF',470,610,310,170,icon='gateway')
p.box('backend','Azure Virtual Machine','Linux · Nginx / PHP-FPM\nLaravel + Inertia.js\nFortify (web) · Sanctum (API)\nQueue worker + scheduler',860,575,390,300,icon='vm',stroke='#0078d4')
p.box('vault','Azure Key Vault','Application secrets\nProvider credentials',470,1020,310,160,icon='vault')
p.box('blob','Azure Blob Storage','Uploaded documents\nImages and media files',860,1210,390,160,icon='blob')
p.box('mysql','Azure Database for MySQL','Flexible Server\nApplication records · jobs\nLaravel-owned relational data',860,980,390,175,icon='mysql')
# Existing AI components are deliberately not labelled managed Azure AI products.
p.rect('ai',1370,550,790,820,'#fffdf8','#f59e0b',16)
p.icon('ai-vm-icon','vm',1395,570,50)
p.text('ai-title','Azure Virtual Machine — AI host',1460,565,650,40,22,bold=True)
p.text('ai-caption','GPU-capable VM as needed · self-hosted services',1460,608,650,30,16,color='#64748b')
p.box('orchestrator','AI service / agent','HTTP API · extraction · orchestration\nApproved evidence and user queries',1410,680,710,125,fill='#ffffff',stroke='#f0b878')
p.box('embedding','EmbeddingGemma-300m','Document / query embeddings',1410,875,325,125,fill='#ffffff',stroke='#f0b878')
p.box('generator','gemma-4-E2B','Generate responses / news drafts',1795,875,325,125,fill='#ffffff',stroke='#f0b878')
p.box('chroma','ChromaDB','Approved evidence + vectors\nSelf-hosted vector store',1410,1070,325,140,fill='#ffffff',stroke='#f0b878')
p.box('judge','Qwen3-4B','Evaluate and refine outputs',1795,1070,325,140,fill='#ffffff',stroke='#f0b878')
p.box('disk','Azure Managed Disks','Persistent ChromaDB data + agent SQLite checkpoints',1410,1260,710,85,icon='disk')
# Runtime flows: labels kept in dedicated corridors.
p.arrow('clients-to-gw','clients','gateway','HTTPS / REST API',[(360,460),(405,460),(405,695),(470,695)],labelxy=(365,585,100,50))
p.arrow('gw-to-app','gateway','backend','HTTPS',[(780,695),(860,695)],labelxy=(785,660,70,25))
p.arrow('app-to-ai','backend','orchestrator','Private HTTP\nrequest / response',[(1250,735),(1410,735)],labelxy=(1255,675,145,45))
p.arrow('app-to-db','backend','mysql','SQL over TLS',[(1060,875),(1060,980)],kind='storage',labelxy=(1070,910,160,30))
p.arrow('app-to-blob','backend','blob','File read / write',[(910,875),(820,875),(820,1290),(860,1290)],kind='storage',labelxy=(650,1210,160,35))
p.arrow('app-to-vault','backend','vault','Managed identity\nRead secrets',[(860,805),(810,805),(810,990),(625,990),(625,1020)],kind='secret',labelxy=(610,910,180,45))
p.arrow('app-to-external','backend','external','Outbound provider APIs',[(860,840),(830,840),(830,920),(385,920),(385,1020),(360,1020)],labelxy=(455,875,240,30))
p.arrow('ai-embed','orchestrator','embedding','Encode',[(1570,805),(1570,875)],labelxy=(1580,824,100,25))
p.arrow('embed-chroma','embedding','chroma','Index / similarity search',[(1570,1000),(1570,1070)],kind='storage',labelxy=(1410,1020,150,35))
p.arrow('ai-generate','orchestrator','generator','Prompt + evidence',[(1955,805),(1955,875)],labelxy=(1970,820,140,35))
p.arrow('chroma-gen','chroma','generator','Retrieved context',[(1735,1140),(1765,1140),(1765,950),(1795,950)],labelxy=(1660,1005,170,30))
p.arrow('gen-judge','generator','judge','Draft → evaluation',[(1955,1000),(1955,1070)],labelxy=(1970,1020,150,35))
p.arrow('judge-revise','judge','orchestrator','Quality result / revision loop',[(2120,1140),(2140,1140),(2140,740),(2120,740)],labelxy=(1820,1230,280,25))
p.arrow('chroma-disk','chroma','disk','Persist',[(1570,1210),(1570,1260)],kind='storage',labelxy=(1430,1220,120,25))
p.arrow('git-build','github','pipeline','Commit / push',[(1210,280),(1320,280)],kind='deploy',labelxy=(1210,245,110,25))
p.arrow('build-acr','pipeline','registry','Build + push',[(1650,280),(1780,280)],kind='deploy',labelxy=(1655,245,120,25))
p.arrow('deploy-app','pipeline','backend','Release application image',[(1430,345),(1430,410),(1055,410),(1055,575)],kind='deploy',labelxy=(1100,390,260,25))
p.arrow('deploy-ai','pipeline','ai','Release AI image',[(1550,345),(1550,410),(2015,410),(2015,550)],kind='deploy',labelxy=(1690,390,240,25))
p.text('deploy-note','Deploy stage pulls the selected image tag from Azure Container Registry onto each VM.',980,350,1180,25,13,color='#6d28d9')
p.text('legend','Solid arrows: application/data flow     Dashed purple: CI/CD     Dashed teal: secret access',50,1460,1600,30,16,color='#475569')
p.text('footer','Models and ChromaDB are custom software hosted on Azure, not managed Azure model/vector services. Model labels follow the supplied design.',50,1495,2130,30,15,color='#64748b')
p.save('azure-architecture')

q=Page('02 Service mapping and design notes',1800,1300)
q.text('title','Google Cloud → Microsoft Azure mapping',50,25,1700,55,32,bold=True)
q.text('sub','Infrastructure conversion with application behavior preserved',50,90,1600,35,18,color='#64748b')
rows=[('Cloud Load Balancing','Azure Application Gateway','HTTP/HTTPS routing and TLS termination','gateway'),('Compute Engine — Laravel','Azure Virtual Machines','Linux host for Laravel, workers and scheduler','vm'),('Secret Manager','Azure Key Vault','Secrets and certificates; access via managed identity','vault'),('Cloud Storage','Azure Blob Storage','Object storage for documents and media','blob'),('Cloud SQL (MySQL)','Azure Database for MySQL Flexible Server','Retain the MySQL engine; not Azure SQL Database','mysql'),('Artifact Registry','Azure Container Registry','Store versioned container images','registry'),('Cloud Build','Azure Pipelines (Azure DevOps)','Build from GitHub, push images and deploy','devops'),('Agent / model compute','Azure Virtual Machines','Retain existing models; select GPU/memory after sizing','vm'),('ChromaDB / SQLite local files','Azure Managed Disks on AI VM','Persistent storage; Blob Storage is not the live vector DB','disk')]
q.rect('tablehead',50,155,1700,50,'#0078d4','#0078d4',0)
for i,(t,x,w) in enumerate([('ORIGINAL COMPONENT',65,490),('AZURE SERVICE',620,580),('PURPOSE / DESIGN CHOICE',1190,540)]):q.text('h'+str(i),t,x,165,w,30,16,color='white',bold=True)
for i,(src,dst,desc,icon) in enumerate(rows):
 y=205+i*78;q.rect('row'+str(i),50,y,1700,78,'#f1f7fd' if i%2==0 else '#ffffff','#dbe4ef',0)
 q.text('src'+str(i),src,65,y+8,485,62,17)
 q.icon('icon'+str(i),icon,570,y+15,45);q.text('dst'+str(i),dst,630,y+8,540,62,17,bold=True)
 q.text('desc'+str(i),desc,1190,y+8,540,62,16,color='#475569')
q.rect('notes',50,950,1700,285,'#fffbea','#d8c98a')
q.text('notes-title','Implementation assumptions',75,965,1620,35,20,bold=True)
q.text('notes-text','• Laravel, Inertia.js, Fortify and Sanctum remain application components.\n• GitHub and SMS / WhatsApp / Expo / Meta remain external integrations.\n• Laravel owns relational SQL writes; the AI service uses ChromaDB and SQLite.\n• Mount persistent managed disks for the AI data paths. Choose VM SKU/region after memory and GPU sizing.\n• Blob Storage needs a compatible Laravel filesystem adapter or SDK integration. Key Vault needs identity/access configuration.\n• This is a proposed architecture drawing, not a deployed or fully configured Azure environment.',75,1010,1630,205,18,color='#334155')
q.save('azure-service-mapping')
E.indent(mx);E.ElementTree(mx).write(OUT/'apakhabar-azure-architecture.drawio',encoding='utf-8',xml_declaration=True)
print('Created 2-page draw.io architecture with embedded official Azure icons, SVG previews and raw XML.')
