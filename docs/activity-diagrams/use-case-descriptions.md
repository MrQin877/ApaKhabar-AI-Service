# News use-case activity diagrams

These are UML swimlane activity diagrams for the five requested use cases, matching the supplied sample (not actor/ellipse use-case diagrams). Each includes an initial node, actions, decisions, labelled alternatives, retry paths and final nodes.

Open `news-use-case-activities.drawio` for all five pages. Individual draw.io files, raw mxGraphModel XML and SVG previews are also included.

## News Generation

**Actors / lanes:** Moderator / Administrator, System, AI Service

**Precondition:** Signed-in, verified moderator or administrator; source access is checked.

**Postcondition / scope:** Draft and supporting information saved. Generation does not publish news.

## Review and Finalize News Post

**Actors / lanes:** Moderator / Administrator, System, AI Quality Review

**Precondition:** User owns a draft that is still editable.

**Postcondition / scope:** Current version reviewed; publication remains a separate operation. Review alone does not override a quality block.

## Publishing News Post

**Actors / lanes:** Moderator / Administrator, System, Facebook / Instagram

**Precondition:** Owned draft; current-version review or supported review confirmation; applicable category, quality and preview checks.

**Postcondition / scope:** Per-platform results retained. Existing published IDs prevent repeated creation. Some targets may succeed while others fail.

## News Post Engagement and Moderation

**Actors / lanes:** Reader / Villager, System, Moderator / Administrator

**Precondition:** Active article. Guests can comment subject to challenge and daily quota; likes/reports require authentication.

**Postcondition / scope:** Engagement persisted. Unavailable/flagged/suspicious moderation stays pending. Reports alone do not hide comments. View tracking is automatic and token-validated.

## Monitor News Analytics

**Actors / lanes:** Administrator, System, Meta / Background Sync

**Precondition:** Authenticated and verified administrator. Analytics report access is distinct from the moderator operational dashboard.

**Postcondition / scope:** Filtered report displayed or exported. Meta snapshots refresh separately; lifetime views are not date-period view counts.

## Source and modeling notes

Source-traced from the current Laravel controllers/services: NewsCreatorController, NewsWorkspaceController, NewsGenerationService, InteractionService, CommentModeration, ModerationDecisionService, GuestCommentIdentity, AnalyticsController, AnalyticsReport and MetaInsights. AI generation is summarized at the use-case level rather than exposing every internal tool call.

Publication gates are represented together: ownership, editable draft, reviewed current version, quality block, category where applicable, and preview validity/issues when supplied. Review does not guarantee publication eligibility. Eligible conflict approval does not automatically bypass the existing publish_blocked check.

The engagement diagram presents alternative reader actions. Published comments can later be reported in a separate interaction; the reporting path is not required after every comment. Human review is asynchronous. Automatic news view tracking is described in the postcondition rather than expanded into a separate lane.

Analytics uses saved social snapshots; a sync request dispatches background work (or runs inline with a sync queue driver). Failed/disconnected/no-data states are distinguished in notes; no unimplemented live refresh is assumed.

Authorization failures, unexpected service exceptions, and all UI navigation options are not expanded at every step; these are report-level activity diagrams. No application code or database was changed.

Validation: all nodes reachable, connector IDs/endpoints valid, XML parsed; representative SVG layouts rendered for visual inspection.