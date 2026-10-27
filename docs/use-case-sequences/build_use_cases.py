import pathlib
O=pathlib.Path(__file__).resolve().parent
base=(O.parent/'sequence-diagrams/build_sequences.py').read_text()
ns={'__file__':str(O/'build_use_cases.py')}
exec(base[:base.index('# Layout shared')],ns)
existing=ns['P'];ns['P']=[]
page=ns['page'];msg=ns['msg'];note=ns['note'];frame=ns['frame'];otherwise=ns['otherwise'];end=ns['end']
page('01-review-finalize','Review and Finalize News Post',['Moderator / Administrator','Web Application\n(System)','Application Database','AI Service\nDraft Quality Review'],[
msg(0,1,'openDraft(draftId)'),msg(1,2,'load owned draft, version, sources and evaluations'),msg(2,1,'return draft and quality results',True),msg(1,0,'display draft editor, evidence and warnings',True),
frame('loop [changes required]'),msg(0,1,'saveChanges(content, category, image)'),msg(1,1,'validate ownership, editable status and fields'),msg(1,2,'transaction: save changes; increment version; clear reviewed_at'),msg(1,2,'store draft-version snapshot'),
frame('opt [AI draft with existing evaluations: content edit]'),msg(1,2,'create pending evaluation; read approved active sources'),msg(2,1,'return version and evidence',True),msg(1,3,'POST /news/review-draft (title, content, sources)'),msg(3,1,'return quality, claims and publish_blocked / failure',True),msg(1,1,'validate quality and evidence; block on missing support or failure'),msg(1,2,'lock draft; save evaluation only if version still current'),end(),msg(2,1,'return updated draft state',True),msg(1,0,'display revised version and quality warnings',True),end(),
msg(0,1,'confirmReview(currentDraft)'),msg(1,1,'verify owned draft is still editable'),msg(1,2,'update reviewed_at'),msg(2,1,'review recorded',True),msg(1,0,'show reviewed draft; publication is separate',True),
note('Content edits with evaluations trigger re-review. Image changes also increment version and clear reviewed_at. Marking reviewed or approving an eligible conflict does not override the publication endpoint’s publish_blocked check.')],
['app/Http/Controllers/Admin/NewsCreatorController.php:saveDraft/reviewDraft/uploadDraftImage','app/Services/DraftQualityReviewService.php'])
page('02-publish-news','Publishing News Post',['Moderator / Administrator','Web Application\n(System)','Application Database','Facebook / Instagram\nPublishing API'],[
msg(0,1,'openPublicationPreview(draftId, selectedPlatforms)'),msg(1,2,'load draft, media variants and connection context'),msg(2,1,'return publication data',True),msg(1,0,'display previews and platform issues',True),msg(0,1,'confirmPublish(platforms, version, previewToken)'),msg(1,1,'validate ownership, draft status, current review and quality gate'),
note('Validate applicable category and preview checks. An invalid/stale preview or blocked AI quality stops publishing; return errors for correction.'),
frame('loop [each selected platform]'),msg(1,2,'lock draft; check existing published platform ID'),msg(2,1,'return existing publication state',True),
frame('alt [already published on platform]'),msg(1,1,'reuse published ID; avoid duplicate creation'),
otherwise('[website not yet published]'),msg(1,2,'create active news; store published_news_id'),msg(2,1,'return news ID',True),
otherwise('[Facebook or Instagram not yet published]'),msg(1,3,'publish image + post text / caption'),msg(3,1,'return platform ID or publishing error',True),
frame('alt [provider success]'),msg(1,2,'store facebook_post_id / instagram_media_id'),
otherwise('[provider failure]'),msg(1,1,'record safe error for this platform; continue other targets'),end(),end(),end(),
msg(1,2,'merge publication_results; retain successful platform IDs'),
frame('opt [all stored publication results successful]'),msg(1,2,'set draft.status = published'),end(),msg(2,1,'return final per-platform state',True),msg(1,0,'display success or partial-failure summary',True),
frame('opt [retry failed targets]'),msg(0,1,'retry failed platforms after correcting issues'),msg(1,1,'repeat checks and publishing loop; reuse successful IDs'),end()],
['app/Http/Controllers/Admin/NewsWorkspaceController.php:publish','app/Services/FacebookPublishingService.php','app/Services/InstagramService.php'])
page('03-engagement-moderation','News Post Engagement and Moderation',['Reader / Villager','Web Application\n(System)','Application Database','Moderation API\n(OpenAI)','Moderator / Administrator'],[
msg(0,1,'openNewsArticle(newsId)'),msg(1,2,'load active news and published comments'),msg(2,1,'return public content',True),msg(1,0,'display article and engagement controls',True),
frame('opt [qualified view]'),msg(0,1,'request engagement token; submit after reading interval'),msg(1,1,'validate encrypted token, age and session'),msg(1,2,'transaction: deduplicate visit; record viewer; update counters'),msg(2,1,'return unique_views',True),msg(1,0,'update view count',True),end(),
frame('alt [like or unlike: login required]'),msg(0,1,'toggleLike(post or comment)'),msg(1,2,'lock target; insert/delete like; count likes'),msg(1,2,'update cached likes_count for news posts'),msg(2,1,'return liked and count',True),msg(1,0,'update Like button and count',True),
otherwise('[comment or reply]'),msg(0,1,'submitComment(content, parentId?, guestChallenge?)'),msg(1,1,'validate fields; check guest challenge when anonymous'),msg(1,2,'check guest quota if applicable, visibility and duplicate hash'),msg(2,1,'return eligibility',True),
note('Invalid input, duplicate content, or exhausted guest quota stops submission. Guests may submit up to three comments per day; replies require a published parent.'),
frame('opt [moderation API key configured]'),msg(1,3,'POST /v1/moderations (content)'),msg(3,1,'return flags/categories or service failure',True),end(),msg(1,1,'publish only clean valid result without suspicious links/promotion'),msg(1,2,'save comment + initial history; increment guest quota on success'),msg(2,1,'return published or pending_review',True),msg(1,0,'show publication / awaiting-review confirmation',True),
otherwise('[report published comment: login required]'),msg(0,1,'reportComment(category, details)'),msg(1,2,'insertOrIgnore comment_reports'),msg(2,1,'report accepted',True),msg(1,0,'display acknowledgement; do not auto-hide',True),end(),
frame('opt [human review: pending, reported or flagged comment]'),msg(4,1,'open moderation queue'),msg(1,2,'load comments, reports, flags and history'),msg(2,1,'return review records and revision',True),msg(1,4,'display review details',True),msg(4,1,'allow / hide (reason, expectedRevision?)'),msg(1,2,'transaction: lock comment; check current revision and transition'),
frame('alt [conflict]'),msg(1,4,'409: reload latest comment',True),
otherwise('[valid decision]'),msg(1,2,'set published / hidden; increment revision; append history'),msg(1,2,'resolve open reports and flags; commit'),msg(2,1,'decision saved',True),msg(1,4,'display saved decision',True),end(),end(),
note('This use case summarizes independent reader interactions. Human moderation happens later; no reader request waits for a moderator. Reviewers can create comment_flags separately. Unavailable AI moderation leaves comments pending_review.')],
['app/Http/Controllers/News/EngagementController.php','app/Http/Controllers/News/CommentController.php','app/Services/News/InteractionService.php','app/Services/News/CommentModeration.php','app/Services/News/ModerationDecisionService.php'])
page('04-monitor-analytics','Monitor News Analytics',['Administrator','Web Application\n(System)','Application Database','Background Worker\nMeta Insights Sync','Meta Graph API'],[
msg(0,1,'openAnalytics(filters)'),msg(1,1,'authorize administrator; validate date range and filters'),msg(1,2,'read analytics settings; aggregate news, audience and engagement'),msg(2,1,'return summary, trends and post performance',True),msg(1,2,'read saved Meta snapshots and synchronization status'),msg(2,1,'return social metrics',True),msg(1,0,'display dashboard, filters, charts and tables',True),
frame('opt [inspect or change filters]'),msg(0,1,'select post / date range / category / sort'),msg(1,2,'query filtered data and optional post inspection'),msg(2,1,'return filtered results',True),msg(1,0,'update analytics view',True),end(),
frame('opt [export report]'),msg(0,1,'export(scope, CSV or XLSX)'),msg(1,2,'read report data for selected scope and filters'),msg(2,1,'return export rows',True),msg(1,1,'build CSV / XLSX'),msg(1,0,'download report',True),end(),
frame('opt [synchronize social analytics]'),msg(0,1,'requestMetaSync()'),msg(1,3,'dispatch unique SyncMetaInsights job'),msg(1,0,'return to analytics',True),msg(3,2,'read selected connections and credentials'),msg(2,3,'return configured accounts',True),
frame('loop [each connected account]'),msg(3,4,'request daily metric series (last seven days)'),msg(4,3,'return points / provider error',True),
frame('alt [valid data and unchanged account]'),msg(3,2,'upsert snapshots; set ready and synced timestamp'),
otherwise('[failure or no data]'),msg(3,2,'set unavailable / no_data; preserve prior snapshots'),end(),end(),msg(0,1,'refreshAnalytics()'),msg(1,2,'read stored snapshots and status'),msg(2,1,'return updated saved metrics',True),msg(1,0,'display refreshed social analytics',True),end(),
note('Disconnected connections are skipped and marked disconnected. Queue execution depends on its configured driver. Reports read snapshots, not live Meta calls. PostPerformance supplies actual post statistics; the generic engagement widget remains a placeholder.')],
['app/Http/Controllers/Admin/AnalyticsController.php','app/Http/Controllers/Admin/MetaAnalyticsController.php','app/Services/Analytics/AnalyticsReport.php','app/Services/Analytics/PostPerformance.php','app/Services/Analytics/MetaInsights.php'])
# Reuse the proven editable lifeline renderer, writing only to this output folder.
renderer=base[base.index('# Layout shared'):]
renderer=renderer.replace('analytics-and-engagement-sequences.drawio','other-use-case-sequences.drawio').replace('Eight editable diagrams','Four editable diagrams').replace('all eight pages','all four pages').replace('analytics-and-engagement-sequences.drawio','other-use-case-sequences.drawio')
exec(renderer,ns)
# Include the supplied generation diagram as an unchanged first page in a companion file.
import xml.etree.ElementTree as E,zipfile
root=E.parse(O/'other-use-case-sequences.drawio').getroot()
original=E.parse('/Users/mrqin877/.codex/attachments/121447f2-5bae-4779-813c-51e7426b43e4/Pasted text.txt').getroot()
d=E.Element('diagram',id='provided-generation',name='News Generation - supplied sample');d.append(original);root.insert(0,d)
E.ElementTree(root).write(O/'all-five-use-case-sequences.drawio',encoding='utf-8',xml_declaration=True)
readme=O/'README.md';readme.write_text(readme.read_text()+'\n\n`all-five-use-case-sequences.drawio` includes your supplied News Generation model unchanged as page one, followed by the four new diagrams. `other-use-case-sequences.drawio` contains only the four newly requested use cases.\n')
for f in list(O.glob('*.drawio'))+list(O.glob('*.xml')):E.parse(f)
with zipfile.ZipFile(O/'use-case-sequences.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(O.iterdir()):
  if f.suffix in ['.drawio','.xml','.svg','.mmd','.md']:z.write(f,f.name)
print('Packaged four new use cases and a companion file including the original generation sample.')
