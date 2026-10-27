"""Native draw.io sequence diagrams following the user's sample, traced from current Laravel code."""
import pathlib,json,html,textwrap,xml.etree.ElementTree as E,copy
OUT=pathlib.Path(__file__).resolve().parent
P=[]
def msg(a,b,label,ret=False):return {'kind':'message','from':a,'to':b,'label':label,'return':ret}
def note(s):return {'kind':'note','label':s}
def frame(s):return {'kind':'frame','label':s}
def otherwise(s):return {'kind':'else','label':s}
def end():return {'kind':'end'}
def page(slug,title,people,events,sources):P.append(dict(slug=slug,title=title,people=people,events=events,sources=sources))
page('01-view-analytics','View analytics and export reports',
['Administrator','Web Application\n(Analytics UI)','AnalyticsController','Analytics Services\n(Report / Performance / Export)','Application Database'],[
msg(0,1,'navigateAnalyticsPage(filters)'),msg(1,2,'GET /admin/analytics'),
msg(2,2,'authorize administrator; validate dates, filters and range'),
note('Authenticated, verified administrator required. Invalid filters stop the request; no report is returned.'),
msg(2,4,'read AnalyticsSetting::current() and layout'),msg(4,2,'return dashboard configuration',True),
msg(2,3,'build(widgets, from, to, source, platform)'),
msg(3,4,'aggregate users, activity, news and broadcasts'),msg(4,3,'return aggregate rows',True),
msg(3,4,'read selected social connections and saved Meta snapshots'),msg(4,3,'return social metrics and sync status',True),
msg(3,2,'return report widgets',True),
frame('alt [export requested]'),msg(2,3,'data(scope, filters); build CSV or XLSX'),msg(3,4,'read additional export rows as required'),msg(4,3,'return export data',True),msg(3,2,'return export content / workbook path',True),msg(2,1,'download CSV / XLSX (private, no-store)',True),msg(1,0,'save report file',True),
otherwise('[view dashboard]'),msg(2,3,'interactionTrend(); listing(); optional post inspection'),msg(3,4,'query likes, comments and post performance'),msg(4,3,'return rows and trends',True),msg(3,2,'return performance data',True),msg(2,4,'read categories and administrator connections'),msg(4,2,'return selection options',True),msg(2,1,'render admin/analytics with filters and configuration',True),msg(1,0,'display charts, tables and social sync status',True),end(),
note('Changing filters repeats GET /admin/analytics. Dashboard reads stored Meta metrics; it does not call Meta live. The generic engagement widget is still a placeholder; post performance is calculated separately.')],
['app/Http/Controllers/Admin/AnalyticsController.php:index','app/Services/Analytics/AnalyticsReport.php:build','app/Services/Analytics/PostPerformance.php','app/Services/Analytics/MetaInsights.php:report','app/Services/Analytics/AnalyticsExport.php'])
page('02-sync-social-analytics','Synchronize social-media analytics',
['Administrator','Web Application\n(System)','MetaAnalyticsController','Queue Worker\nSyncMetaInsights / MetaInsights','Application Database','Meta Graph API'],[
msg(0,1,'select accounts or request synchronization'),
frame('alt [change selected accounts]'),msg(1,2,'PUT /admin/analytics/meta (connection_ids)'),msg(2,4,'validate owned connections; one account per platform'),msg(4,2,'return validated connections',True),msg(2,4,'transaction: update analytics_settings; insert setting change'),msg(4,2,'commit configuration',True),
otherwise('[manual refresh]'),msg(1,2,'POST /admin/analytics/meta/sync'),msg(2,2,'authorize administrator; apply route throttle'),end(),
msg(2,3,'dispatch SyncMetaInsights (unique job)'),msg(2,1,'redirect back',True),msg(1,0,'display current saved metrics',True),
msg(3,4,'read selected social_connections'),msg(4,3,'return configured connections',True),
frame('loop [each selected connection]'),
frame('alt [connection is disconnected]'),msg(3,4,'set insights_status = disconnected'),
otherwise('[connection is usable]'),msg(3,5,'GET account insights (daily metrics; last 7 days)'),msg(5,3,'return metric series / provider error',True),
frame('alt [valid points and same account/token still selected]'),msg(3,4,'transaction: lock connection; recheck identity; upsert snapshots'),msg(3,4,'set insights_status = ready and insights_synced_at'),msg(4,3,'commit snapshots',True),
otherwise('[no data / failure / changed connection]'),msg(3,4,'set no_data or unavailable; discard stale-account response'),end(),end(),end(),
note('A later analytics request reads these snapshots. Queue timing depends on the configured driver; with a sync driver, dispatch runs inline. No automatic UI polling is implied.')],
['app/Http/Controllers/Admin/MetaAnalyticsController.php','app/Jobs/SyncMetaInsights.php','app/Services/Analytics/MetaInsights.php:sync'])
page('03-record-news-view','Record a news view',
['Reader\n(Guest / signed-in)','Web Application\n(News UI)','EngagementController','Application Database'],[
msg(0,1,'open article'),msg(1,2,'GET /news/{id}/engagement'),msg(2,3,'verify active news'),msg(3,2,'return news record',True),msg(2,2,'create viewer key and session-bound encrypted token'),msg(2,1,'return token; set news_visitor cookie',True),
note('The UI waits for the qualified reading interval while the document is visible. Server accepts token age 5 seconds to 2 hours.'),
msg(1,2,'POST /news/{id}/view (token)'),msg(2,2,'decrypt; validate news ID, token age and session'),
frame('alt [invalid token]'),msg(2,1,'422: reject view request',True),
otherwise('[valid token]'),msg(2,3,'begin transaction; lock active news'),msg(2,3,'check hashed visit ID in news_visits'),msg(3,2,'return visit existence',True),
frame('alt [visit already recorded]'),msg(2,3,'read unchanged unique_views; commit'),
otherwise('[new visit]'),msg(2,3,'insert news_visits; check news_viewers'),msg(3,2,'return viewer existence',True),
frame('opt [new viewer]'),msg(2,3,'insert news_viewers; increment news.unique_views'),end(),msg(2,3,'increment news.view; commit'),end(),msg(3,2,'return unique_views',True),msg(2,1,'JSON: unique_views',True),msg(1,0,'update displayed view count',True),end(),
note('Repeat submissions of one visit token do not increment counts again. A new visit from a known viewer increases total views, but not unique views.')],
['app/Http/Controllers/News/EngagementController.php:context/view','resources/js/components/news-engagement.tsx'])
page('04-record-short-view','Record a short-video view',
['Viewer\n(Guest / signed-in)','Web Application\n(Short-video player)','ShortViewerController','Application Database'],[
msg(0,1,'open and play a published short video'),msg(1,2,'GET /shorts/{id}/view-token'),msg(2,3,'verify published video and published_at'),msg(3,2,'return video',True),msg(2,2,'create viewer key and session-bound encrypted token'),msg(2,1,'return token; set short_visitor cookie',True),
note('The player tracks qualified visible playback before submitting a view. Server accepts token age 5 seconds to 2 hours.'),msg(1,2,'POST /shorts/{id}/view (token)'),msg(2,2,'validate video, age, current viewer and session'),
frame('alt [invalid token]'),msg(2,1,'422: reject request',True),
otherwise('[valid token]'),msg(2,3,'begin transaction; lock published short_videos row'),msg(2,3,'insertOrIgnore short_video_viewers(video_id, viewer_key)'),msg(3,2,'return whether a row was inserted',True),
frame('opt [first recorded view for this viewer]'),msg(2,3,'increment short_videos.view_count'),end(),msg(2,3,'commit; read view_count'),msg(3,2,'return view_count',True),msg(2,1,'JSON: view_count',True),msg(1,0,'update displayed count',True),end(),
note('Short-video view_count is deduplicated by (short_video_id, viewer_key). Unlike news, this flow has no separate news_visits-style total-visit counter.')],
['app/Http/Controllers/Home/ShortViewerController.php:token/view','resources/js/pages/short-viewer.tsx'])
page('05-like-unlike','Like or unlike news and comments',
['Signed-in reader','Web Application\n(Engagement UI)','News controllers','InteractionService','Application Database'],[
msg(0,1,'click Like'),msg(1,2,'POST /news/{id}/like or /comments/{id}/like'),msg(2,2,'authentication and throttle middleware'),msg(2,3,'likeNews(userId, newsId) / likeComment(userId, commentId)'),msg(3,4,'begin transaction; lock target; verify visibility'),msg(3,4,'find existing like for this user and target'),msg(4,3,'return existing / absent',True),
frame('alt [not liked]'),msg(3,4,'insert likes / comment_likes row'),
otherwise('[already liked]'),msg(3,4,'delete existing like row'),end(),msg(3,4,'count remaining likes'),msg(4,3,'return count',True),
frame('opt [news post]'),msg(3,4,'update news.likes_count'),end(),msg(3,4,'commit'),msg(3,2,'return liked and likes_count',True),msg(2,1,'JSON: liked, likes_count',True),msg(1,0,'update Like state and count',True),
note('Comment likes are counted directly; there is no cached comments.likes_count column. Unauthenticated requests stop at middleware. Short-video equivalents use ShortEngagementController and short_video_likes / short_video_comment_likes, with the same toggle pattern.')],
['app/Services/News/InteractionService.php:likeNews/likeComment','app/Http/Controllers/News/PostLikeController.php','app/Http/Controllers/News/CommentController.php:like','app/Http/Controllers/Home/ShortEngagementController.php:likeVideo/likeComment','routes/web.php'])
page('06-comment-reply','Submit a comment or reply with moderation',
['Reader\n(Guest / signed-in)','Web Application\n(News UI)','CommentController /\nGuestCommentIdentity','InteractionService /\nCommentModeration','Application Database','Moderation API\n(OpenAI)'],[
msg(0,1,'enter comment or reply'),msg(1,2,'POST /news/{id}/comment or /comments/{id}/replies'),msg(2,2,'validate content; resolve published parent for replies'),
frame('opt [guest reader]'),msg(2,2,'validate challenge age 3s–2h, news ID and session'),msg(2,4,'find/create guest identity; lock identity; read daily quota'),msg(4,2,'return username and comment_count',True),note('Invalid challenge or quota of 3/day reached: stop with validation error. Guest quota day uses Asia/Jakarta in the implementation.'),end(),
msg(2,3,'addComment(...) / addReply(...)'),msg(3,4,'verify active news; check duplicate submission_hash'),msg(4,3,'return eligibility and duplicate result',True),note('Duplicate content stops with validation error. Replies must reference a published parent.'),
msg(3,3,'check(content): detect suspicious links / promotion'),
frame('alt [moderation API key configured]'),msg(3,5,'POST /v1/moderations (omni-moderation-latest, content)'),msg(5,3,'return flags / categories, or error',True),
otherwise('[no moderation key]'),msg(3,3,'use pending_review fallback'),end(),
msg(3,3,'choose published only if clean, valid and not suspicious'),note('Flagged, suspicious, unavailable or malformed results remain pending_review. The Laravel moderation service calls this API directly; it does not call the project AI service.'),
msg(3,4,'transaction: lock news; recheck duplicate; insert comment'),msg(3,4,'insert initial comment_moderation_history'),msg(4,3,'return saved comment',True),msg(3,2,'return status',True),
frame('opt [guest submission succeeded]'),msg(2,4,'increment guest_comment_days; commit guest transaction'),end(),msg(2,1,'201: status, remaining_quota and confirmation',True),msg(1,0,'show published or awaiting-review confirmation',True),
note('Short-video comments use ShortCommentService with short_video_comments / short_video_comment_history and the shared moderation and guest-identity services.')],
['app/Http/Controllers/News/CommentController.php','app/Services/GuestCommentIdentity.php','app/Services/News/InteractionService.php:addComment/addReply','app/Services/News/CommentModeration.php','app/Services/Shorts/ShortCommentService.php'])
page('07-report-flag','Report or flag a comment',
['Reader / reviewer','Web Application\n(Engagement UI)','EngagementController /\nCommentFlagController','Application Database'],[
frame('alt [signed-in reader reports]'),msg(0,1,'submit report category and details'),msg(1,2,'POST /comments/{id}/report'),msg(2,2,'require authenticated non-admin/non-moderator; validate'),msg(2,3,'find published comment and active news'),msg(3,2,'return eligible target',True),msg(2,3,'insertOrIgnore comment_reports (category, explanation)'),msg(3,2,'report stored / duplicate ignored',True),msg(2,1,'JSON: report received',True),msg(1,0,'display acknowledgement',True),
otherwise('[verified admin/moderator flags]'),msg(0,1,'select comment and submit flag'),msg(1,2,'POST /admin/news/{news}/moderation-comments/{comment}/flag'),msg(2,2,'authorize reviewer; validate category and explanation'),msg(2,3,'transaction: lock published/pending comment; check open flag'),msg(3,2,'return open flag existence',True),
frame('opt [no open flag by same reviewer]'),msg(2,3,'insert comment_flags'),end(),msg(2,3,'commit'),msg(2,1,'JSON: marked for review',True),msg(1,0,'display acknowledgement',True),end(),
note('Reporting or flagging creates a review item; it does not immediately hide the comment. Moderator review is a separate request. Short-video reports/flags use equivalent short_video_comment_reports / short_video_comment_flags tables.')],
['app/Http/Controllers/News/EngagementController.php:report','app/Http/Controllers/Admin/CommentFlagController.php:flag','app/Models/Comment.php:scopeAwaitingReview','app/Http/Controllers/Home/ShortEngagementController.php:report/flag'])
page('08-moderation-decision','Review comments and apply a moderation decision',
['Administrator /\nModerator','Web Application\n(Moderation UI)','CommentModerationController','ModerationDecisionService','Application Database'],[
msg(0,1,'open comment review queue'),msg(1,2,'GET /admin/comments (filters)'),msg(2,4,'query pending comments, reports, flags and history'),msg(4,2,'return paginated review data',True),msg(2,1,'render admin/comments',True),msg(1,0,'display review queue and revision',True),
msg(0,1,'choose allow / hide; enter reason'),msg(1,2,'POST /admin/comments/{id}/decision'),msg(2,2,'validate action, reason, optional expected_revision'),msg(2,3,'decide(actor, id, action, reason, expectedRevision)'),msg(3,3,'authorize verified admin/moderator'),msg(3,4,'begin transaction; lock comment; read open reports/flags'),msg(4,3,'return current status and revision',True),
frame('alt [revision mismatch or invalid transition]'),msg(3,2,'409 conflict; transaction rolls back',True),msg(2,1,'return conflict response',True),msg(1,0,'ask reviewer to reload current comment',True),
otherwise('[valid decision]'),msg(3,4,'allow → published; hide → hidden; increment revision'),msg(3,4,'insert moderation history with actor/action/reason'),msg(3,4,'resolve open reports and flags; commit'),msg(4,3,'return history ID',True),msg(3,2,'decision saved',True),msg(2,1,'JSON: confirmation',True),msg(1,0,'refresh review queue / show saved decision',True),end(),
note('content_type=shorts routes to ShortCommentDecisionService and short-video tables. No AI re-evaluation or new legacy feedback/assessment record is created by this decision.')],
['app/Http/Controllers/Admin/CommentModerationController.php:index/decide','app/Services/News/ModerationDecisionService.php','app/Services/Shorts/ShortCommentDecisionService.php'])

# Layout shared by editable XML, SVG previews, and Mermaid code.
allfile=E.Element('mxfile',host='app.diagrams.net')
def esc(t):return html.escape(str(t),quote=True)
def v(root,id,text,style,x,y,w,h,parent='1'):
 c=E.SubElement(root,'mxCell',id=id,value=text,style=style,vertex='1',parent=parent);E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'});return c
for spec in P:
 n=len(spec['people']); gap=390; xs=[150+i*gap for i in range(n)]; width=xs[-1]+240;y=225;stack=[];frames=[];placed=[]
 for ev in spec['events']:
  e=dict(ev);e['y']=y
  if e['kind']=='frame':stack.append(e);y+=55
  elif e['kind']=='end':
   f=stack.pop();f['bottom']=y+10;frames.append(f);y+=40
  elif e['kind']=='else':y+=55
  elif e['kind']=='note':e['lines']=textwrap.wrap(e['label'],int((width-160)/7.4));e['h']=max(55,22*len(e['lines'])+20);y+=e['h']+25
  else:
   span=abs(xs[e['to']]-xs[e['from']]);chars=max(32,int((span-40)/7)) if span else 37
   e['lines']=textwrap.wrap(e['label'],chars);e['y']=y+max(0,(len(e['lines'])-1)*18);y=e['y']+85
  if e['kind'] not in ['frame','end']:placed.append(e)
 assert not stack
 height=y+80
 model=E.Element('mxGraphModel',grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='0',pageScale='1',pageWidth='1169',pageHeight='827')
 root=E.SubElement(model,'root');E.SubElement(root,'mxCell',id='0');E.SubElement(root,'mxCell',id='1',parent='0')
 v(root,'title',spec['title'],'text;html=0;align=left;fontSize=25;fontStyle=1;',40,15,width-80,45)
 v(root,'legend','Solid arrow: request / call     Dashed arrow: return     Frames: alternative, optional or repeated flow','text;html=0;align=left;fontSize=13;fontColor=#475569;',40,65,width-80,30)
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#333"/></marker></defs><rect width="100%" height="100%" fill="white"/>',f'<text x="40" y="47" font-family="Arial" font-size="25" font-weight="bold">{esc(spec["title"])}</text>',f'<text x="40" y="85" font-family="Arial" font-size="13" fill="#475569">Solid arrow: request / call     Dashed arrow: return     Frames: alternative, optional or repeated flow</text>']
 for i,f in enumerate(frames):
  # outer frame borders, no opaque fill over lifelines/messages
  v(root,'frame'+str(i),f['label'],'shape=umlFrame;whiteSpace=wrap;html=0;pointerEvents=0;width=500;height=30;fillColor=none;strokeColor=#64748b;fontSize=13;',40,f['y']-20,width-80,f['bottom']-f['y']+20)
  svg.append(f'<rect x="40" y="{f["y"]-20}" width="{width-80}" height="{f["bottom"]-f["y"]+20}" fill="none" stroke="#64748b"/><text x="55" y="{f["y"]+2}" font-family="Arial" font-size="13">{esc(f["label"])}</text>')
 for i,name in enumerate(spec['people']):
  color='#ffd2a8' if i==0 else '#dae8fc' if 'Database' in name else '#fff2cc' if 'API' in name else '#e2f0d9'
  style='shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=0;container=1;dropTarget=0;collapsible=0;recursiveResize=0;size=65;fontSize=14;fillColor='+color+';strokeColor=#64748b;'
  if i==0:style+='participant=umlActor;verticalAlign=bottom;labelPosition=center;verticalLabelPosition=top;align=center;'
  v(root,'p'+str(i),name,style,xs[i]-100,125,200,height-160)
  svg.append(f'<line x1="{xs[i]}" y1="190" x2="{xs[i]}" y2="{height-35}" stroke="#94a3b8" stroke-dasharray="6 5"/>')
  if i==0:
   svg.append(f'<circle cx="{xs[i]}" cy="143" r="10" fill="{color}" stroke="#555"/><path d="M {xs[i]} 153 v 22 m -22 -12 h44 m-22 12 l-18 18 m18 -18 l18 18" fill="none" stroke="#555"/>')
   name_lines=name.split('\n')
   for k,line in enumerate(name_lines):svg.append(f'<text x="{xs[i]}" y="{108+k*15}" text-anchor="middle" font-family="Arial" font-size="13">{esc(line)}</text>')
  else:
   svg.append(f'<rect x="{xs[i]-100}" y="125" width="200" height="65" fill="{color}" stroke="#64748b"/>')
   for k,line in enumerate(name.split('\n')):svg.append(f'<text x="{xs[i]}" y="{151+k*19}" text-anchor="middle" font-family="Arial" font-size="14">{esc(line)}</text>')
 for j,e in enumerate(placed):
  yy=e['y'];kind=e['kind']
  if kind=='else':
   c=E.SubElement(root,'mxCell',id='else-line'+str(j),edge='1',parent='1',style='endArrow=none;dashed=1;strokeColor=#64748b;');g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});E.SubElement(g,'mxPoint',x='40',y=str(yy-20),attrib={'as':'sourcePoint'});E.SubElement(g,'mxPoint',x=str(width-40),y=str(yy-20),attrib={'as':'targetPoint'})
   v(root,'else'+str(j),e['label'],'text;html=0;align=left;fontSize=13;',55,yy-18,width-120,30)
   svg.append(f'<line x1="40" y1="{yy-20}" x2="{width-40}" y2="{yy-20}" stroke="#64748b" stroke-dasharray="6 4"/><text x="55" y="{yy+2}" font-family="Arial" font-size="13">{esc(e["label"])}</text>')
  elif kind=='note':
   v(root,'note'+str(j),e['label'],'shape=note;whiteSpace=wrap;html=0;align=left;spacing=10;fontSize=13;fillColor=#fffbea;strokeColor=#c9b975;',65,yy-10,width-130,e['h'])
   svg.append(f'<rect x="65" y="{yy-10}" width="{width-130}" height="{e["h"]}" fill="#fffbea" stroke="#c9b975"/>')
   for k,line in enumerate(e['lines']):svg.append(f'<text x="77" y="{yy+12+k*22}" font-family="Arial" font-size="13">{esc(line)}</text>')
  else:
   a,b=e['from'],e['to']; selfcall=a==b;xx1,xx2=xs[a],xs[b]
   # Ports and activation bars are children of their lifeline, so they move together.
   for side,p,offset in [('s',a,0),('t',b,25 if selfcall else 0)]:v(root,'port'+str(j)+side,'','opacity=0;fillOpacity=0;strokeOpacity=0;',99,yy-125+offset-1,2,2,parent='p'+str(p))
   if not e['return'] and b!=0:
    v(root,'activation'+str(j),'','fillColor=#ffffff;strokeColor=#64748b;',94,yy-125+(25 if selfcall else 0),12,28,parent='p'+str(b))
    svg.append(f'<rect x="{xx2-6}" y="{yy+(25 if selfcall else 0)}" width="12" height="28" fill="white" stroke="#64748b"/>')
   style='edgeStyle=none;html=0;rounded=0;endArrow='+('open' if e['return'] else 'block')+';strokeColor=#333;strokeWidth=1.2;'+('dashed=1;' if e['return'] else '')
   c=E.SubElement(root,'mxCell',id='message'+str(j),edge='1',parent='1',source='port'+str(j)+'s',target='port'+str(j)+'t',style=style)
   g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
   if selfcall:
    ar=E.SubElement(g,'Array',attrib={'as':'points'});E.SubElement(ar,'mxPoint',x=str(xx1+45),y=str(yy));E.SubElement(ar,'mxPoint',x=str(xx1+45),y=str(yy+25));
    labelx=xx1+55;labelw=gap-70
    points=f'{xx1},{yy} {xx1+45},{yy} {xx1+45},{yy+25} {xx1},{yy+25}'
   else:labelx=min(xx1,xx2)+12;labelw=abs(xx2-xx1)-24;points=f'{xx1},{yy} {xx2},{yy}'
   label='\n'.join(e['lines']);lh=len(e['lines'])*18
   v(root,'label'+str(j),label,'text;html=0;whiteSpace=wrap;align='+('left' if selfcall else 'center')+';fontSize=13;verticalAlign=bottom;',labelx,yy-lh-7,labelw,lh)
   svg.append(f'<polyline points="{points}" fill="none" stroke="#333" stroke-width="1.2" marker-end="url(#arrow)"'+(' stroke-dasharray="6 4"' if e['return'] else '')+'/>')
   for k,line in enumerate(e['lines']):svg.append(f'<text x="{labelx if selfcall else labelx+labelw/2}" y="{yy-lh-4+(k+1)*18}" text-anchor="{"start" if selfcall else "middle"}" font-family="Arial" font-size="13">{esc(line)}</text>')
 svg.append('</svg>')
 E.indent(model);E.ElementTree(model).write(OUT/(spec['slug']+'.xml'),encoding='utf-8',xml_declaration=True)
 d=E.SubElement(allfile,'diagram',id=spec['slug'],name=spec['title']);d.append(copy.deepcopy(model))
 standalone=E.Element('mxfile',host='app.diagrams.net');d=E.SubElement(standalone,'diagram',id=spec['slug'],name=spec['title']);d.append(copy.deepcopy(model));E.indent(standalone);E.ElementTree(standalone).write(OUT/(spec['slug']+'.drawio'),encoding='utf-8',xml_declaration=True)
 (OUT/(spec['slug']+'.svg')).write_text('\n'.join(svg))
 mer=['sequenceDiagram','    autonumber']
 for i,p in enumerate(spec['people']):mer.append(f'    {"actor" if i==0 else "participant"} P{i} as '+p.replace('\n',' '))
 for e in spec['events']:
  if e['kind']=='message':mer.append(f'    P{e["from"]}{"-->>" if e["return"] else "->>"}P{e["to"]}: '+e['label'].replace(';',','))
  elif e['kind']=='note':mer.append(f'    Note over P0,P{n-1}: '+e['label'].replace(';',','))
  elif e['kind']=='frame':mer.append('    '+e['label'])
  elif e['kind']=='else':mer.append('    else '+e['label'])
  elif e['kind']=='end':mer.append('    end')
 (OUT/(spec['slug']+'.mmd')).write_text('\n'.join(mer)+'\n')
 cs=root.findall('mxCell');ids={c.get('id') for c in cs};assert len(ids)==len(cs)
 for c in cs:
  if c.get('parent'):assert c.get('parent') in ids
  if c.get('edge') and c.get('source'):assert c.get('source') in ids and c.get('target') in ids
E.indent(allfile);E.ElementTree(allfile).write(OUT/'analytics-and-engagement-sequences.drawio',encoding='utf-8',xml_declaration=True)
(OUT/'sequence-specification.json').write_text(json.dumps(P,indent=2))
md=['# Analytics and engagement sequence diagrams','', 'Eight editable diagrams follow the supplied sample: actor/lifelines, activation bars, solid calls, dashed returns, and UML alternative/optional/loop frames. Each page is based on the current source, with domain-level grouping of controller and service calls for readability. Message labels describe behavior; not every label is a literal PHP method.','', 'Open **analytics-and-engagement-sequences.drawio** for all eight pages. Each numbered diagram is also provided as a standalone `.drawio`, raw `.xml` (mxGraphModel), `.svg` preview, and Mermaid `.mmd`.','', '## Diagrams and code references','']
for p in P:md+=['### '+p['title'],'',f'Files: `{p["slug"]}.drawio`, `.xml`, `.svg`, `.mmd`.','']+['- `'+s+'`' for s in p['sources']]+['']
md+=['## Scope and important details','', '- Diagrams model the web routes. Mobile API middleware and response details can differ.','- Analytics is administrator-only; the separate operational dashboard also permits moderators.','- Date-filtered likes/comments and lifetime view counters are not interchangeable. The generic engagement widget remains a placeholder; PostPerformance supplies actual post engagement statistics.','- Meta reads are snapshot-based. Dispatch timing depends on the queue driver; no unimplemented live updates are assumed.','- Guest comments have a three-per-day limit using Asia/Jakarta in the implementation. Both signed-in and guest content goes through moderation.','- Reports and flags do not automatically change comment visibility. Allow/hide decisions do, with optional revision conflict checks.','- Stored fields use the latest moderation schema: comment_flags, category/explanation on reports, and history action. No new legacy assessment/feedback writes are shown.','- News and short-video view counters have different deduplication rules, so they are diagrammed separately.','- News comment/like flows are detailed; short-video equivalents are called out where they share the same structure. No content or requests were sent to external APIs while producing these diagrams.','', '## Validation','', 'All XML files were parsed; message endpoints, participant references, frame nesting and unique IDs were checked. SVG previews were rendered for layout inspection. These are source-traced diagrams, not runtime tracing captures.','', 'Rebuild from this folder or repository with `python3 docs/sequence-diagrams/build_sequences.py`.']
(OUT/'README.md').write_text('\n'.join(md)+'\n')
print(f'Generated and validated {len(P)} sequence diagrams.')
