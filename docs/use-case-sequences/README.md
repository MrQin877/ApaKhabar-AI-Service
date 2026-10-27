# Analytics and engagement sequence diagrams

Four editable diagrams follow the supplied sample: actor/lifelines, activation bars, solid calls, dashed returns, and UML alternative/optional/loop frames. Each page is based on the current source, with domain-level grouping of controller and service calls for readability. Message labels describe behavior; not every label is a literal PHP method.

Open **other-use-case-sequences.drawio** for all four pages. Each numbered diagram is also provided as a standalone `.drawio`, raw `.xml` (mxGraphModel), `.svg` preview, and Mermaid `.mmd`.

## Diagrams and code references

### Review and Finalize News Post

Files: `01-review-finalize.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/Admin/NewsCreatorController.php:saveDraft/reviewDraft/uploadDraftImage`
- `app/Services/DraftQualityReviewService.php`

### Publishing News Post

Files: `02-publish-news.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/Admin/NewsWorkspaceController.php:publish`
- `app/Services/FacebookPublishingService.php`
- `app/Services/InstagramService.php`

### News Post Engagement and Moderation

Files: `03-engagement-moderation.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/News/EngagementController.php`
- `app/Http/Controllers/News/CommentController.php`
- `app/Services/News/InteractionService.php`
- `app/Services/News/CommentModeration.php`
- `app/Services/News/ModerationDecisionService.php`

### Monitor News Analytics

Files: `04-monitor-analytics.drawio`, `.xml`, `.svg`, `.mmd`.

- `app/Http/Controllers/Admin/AnalyticsController.php`
- `app/Http/Controllers/Admin/MetaAnalyticsController.php`
- `app/Services/Analytics/AnalyticsReport.php`
- `app/Services/Analytics/PostPerformance.php`
- `app/Services/Analytics/MetaInsights.php`

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


`all-five-use-case-sequences.drawio` includes your supplied News Generation model unchanged as page one, followed by the four new diagrams. `other-use-case-sequences.drawio` contains only the four newly requested use cases.
