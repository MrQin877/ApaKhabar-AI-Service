# Analytics and engagement sequence diagrams

Eight editable diagrams follow the supplied sample: actor/lifelines, activation bars, solid calls, dashed returns, and UML alternative/optional/loop frames. Each page is based on the current source, with domain-level grouping of controller and service calls for readability. Message labels describe behavior; not every label is a literal PHP method.

Open **analytics-and-engagement-sequences.drawio** for all eight pages. Each numbered diagram is also provided as a standalone `.drawio`, raw `.xml` (mxGraphModel), `.svg` preview, and Mermaid `.mmd`.

## Diagrams and code references

### View analytics and export reports

Files: `01-view-analytics.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/Admin/AnalyticsController.php:index`
- `app/Services/Analytics/AnalyticsReport.php:build`
- `app/Services/Analytics/PostPerformance.php`
- `app/Services/Analytics/MetaInsights.php:report`
- `app/Services/Analytics/AnalyticsExport.php`

### Synchronize social-media analytics

Files: `02-sync-social-analytics.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/Admin/MetaAnalyticsController.php`
- `app/Jobs/SyncMetaInsights.php`
- `app/Services/Analytics/MetaInsights.php:sync`

### Record a news view

Files: `03-record-news-view.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/News/EngagementController.php:context/view`
- `resources/js/components/news-engagement.tsx`

### Record a short-video view

Files: `04-record-short-view.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/Home/ShortViewerController.php:token/view`
- `resources/js/pages/short-viewer.tsx`

### Like or unlike news and comments

Files: `05-like-unlike.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Services/News/InteractionService.php:likeNews/likeComment`
- `app/Http/Controllers/News/PostLikeController.php`
- `app/Http/Controllers/News/CommentController.php:like`
- `app/Http/Controllers/Home/ShortEngagementController.php:likeVideo/likeComment`
- `routes/web.php`

### Submit a comment or reply with moderation

Files: `06-comment-reply.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/News/CommentController.php`
- `app/Services/GuestCommentIdentity.php`
- `app/Services/News/InteractionService.php:addComment/addReply`
- `app/Services/News/CommentModeration.php`
- `app/Services/Shorts/ShortCommentService.php`

### Report or flag a comment

Files: `07-report-flag.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/News/EngagementController.php:report`
- `app/Http/Controllers/Admin/CommentFlagController.php:flag`
- `app/Models/Comment.php:scopeAwaitingReview`
- `app/Http/Controllers/Home/ShortEngagementController.php:report/flag`

### Review comments and apply a moderation decision

Files: `08-moderation-decision.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/Admin/CommentModerationController.php:index/decide`
- `app/Services/News/ModerationDecisionService.php`
- `app/Services/Shorts/ShortCommentDecisionService.php`

## Scope and important details

- Diagrams model the web routes. Mobile API middleware and response details can differ.
- Analytics is administrator-only; the separate operational dashboard also permits moderators.
- Date-filtered likes/comments and lifetime view counters are not interchangeable. The generic engagement widget remains a placeholder; PostPerformance supplies actual post engagement statistics.
- Meta reads are snapshot-based. Dispatch timing depends on the queue driver; no unimplemented live updates are assumed.
- Guest comments have a three-per-day limit using Asia/Jakarta in the implementation. Both signed-in and guest content goes through moderation.
- Reports and flags do not automatically change comment visibility. Allow/hide decisions do, with optional revision conflict checks.
- Stored fields use the latest moderation schema: comment_flags, category/explanation on reports, and history action. No new legacy assessment/feedback writes are shown.
- News and short-video view counters have different deduplication rules, so they are diagrammed separately.
- News comment/like flows are detailed; short-video equivalents are called out where they share the same structure. No content or requests were sent to external APIs while producing these diagrams.

## Validation

All XML files were parsed; message endpoints, participant references, frame nesting and unique IDs were checked. SVG previews were rendered for layout inspection. These are source-traced diagrams, not runtime tracing captures.

Rebuild from this folder or repository with `python3 docs/sequence-diagrams/build_sequences.py`.
