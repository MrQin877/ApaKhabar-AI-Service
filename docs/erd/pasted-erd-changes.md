# Corrections to your pasted ERD

The updated single-canvas diagram keeps the original rounded table shape, two-column PK/FK + attribute layout, and relative placement of the original entities. Coordinates are expanded and collisions resolved to accommodate corrected attributes. Exact physical table/column names replace conceptual aliases. The attachment is unchanged.

**Verified:** 56 Laravel tables, 526 attributes, 85 enforced foreign keys; all row-port endpoints exist and no table boxes overlap. Schema reconstructed from all 60 migrations in an isolated in-memory SQLite test database. Deployed migration status was not queried.

## Key corrections

- The second `Intelligent_News_Run_Events` box contains run fields: corrected to `intelligent_news_runs`.
- Removed the duplicate feedback shape. The remaining assessment/feedback shapes now represent `archived_comment_moderation_assessments` and `archived_comment_moderation_feedback`, with their actual archive attributes and no invented FKs.
- `Broadcast_Recipient` is replaced by the actual `broadcast_user` junction table. There is no recipient entity or broadcasts.recipientID column.
- The old `Broadcast_Channel` catalog shape becomes `channels`; added the separate `broadcast_channel` junction table.
- `View` becomes `news_viewers`, with exact `id` and `news_id` names.
- Added current user demographics and Fortify fields; retained `two_factors` labelled legacy.
- Corrected aliases and typos: the AI entities mostly use `id`, not documentID/draftID/etc.; corrected updated_at, deleted_at, unique_views, information_embedding_status, approval_note, and other mismatches.
- Removed deleted moderator/assessment attributes and obsolete report reason fields. Included report category/explanation and moderation-history action.
- Regenerated all foreign keys with row-level connectors; unique FKs show 0..1 children, and nullable FKs show 0..1 parents. Composite primary and unique keys are preserved.

## Added tables

- `analytics_setting_changes`
- `analytics_settings`
- `broadcast_channel`
- `comment_flags`
- `comment_likes`
- `comment_moderation_history`
- `comment_reports`
- `failed_jobs`
- `guest_comment_days`
- `guest_comment_identities`
- `jobs`
- `meta_insight_snapshots`
- `migrations`
- `news_visits`
- `short_video_comment_flags`
- `short_video_comment_history`
- `short_video_comment_likes`
- `short_video_comment_reports`
- `short_video_comments`
- `short_video_likes`
- `short_video_publications`
- `short_video_viewers`
- `short_videos`
- `social_connections`
- `villager_activity_hours`

## Original shape → current table

| Original shape | Current physical table |
|---|---|
| Intelligence_Document | `intelligence_documents` |
| User | `users` |
| Email | `emails` |
| Phone | `phones` |
| Two_Factor | `two_factors` |
| User_Role | `user_roles` |
| User Access Token | `personal_access_tokens` |
| Password Reset Token | `password_reset_tokens` |
| News | `news` |
| News Category | `news_categories` |
| Comment | `comments` |
| Like | `likes` |
| Broadcast | `broadcasts` |
| Broadcast_Category | `broadcast_categories` |
| Broadcast_Recipient | `broadcast_user` |
| Broadcast_Channel | `channels` |
| Notification | `notifications` |
| Intelligence_News_Draft | `intelligent_news_drafts` |
| Intelligence_Extraction_Requests | `intelligence_extraction_requests` |
| Intelligence_News_Draft_Sources | `intelligent_news_draft_sources` |
| Intelligence_News_Draft_Versions | `intelligent_news_draft_versions` |
| Intelligence_Information | `intelligence_information` |
| AI_Quality_Evaluations | `ai_quality_evaluations` |
| Intelligent_News_Sessions | `intelligent_news_sessions` |
| Intelligent_News_Run_Events | `intelligent_news_run_events` |
| Intelligent_News_Messages | `intelligent_news_messages` |
| Intelligent_News_Source_Selections | `intelligent_news_source_selections` |
| Intelligent_News_Run_Events | `intelligent_news_runs` |
| Comment_Moderation_Assessments | `archived_comment_moderation_assessments` |
| Comment_Moderation_Feedback | `archived_comment_moderation_feedback` |
| View | `news_viewers` |
| Comment_Moderation_Feedback (duplicate) | Removed duplicate shape |

## Scope

This preserves the scope of your Laravel ERD. The five AI-service SQLite tables and Chroma collections remain documented in the separate complete ERD/dictionary. JSON lists are not treated as foreign keys. `comment_moderation_history.moderator_id` is not connected to users because no FK is declared. Archive references are historical values, not enforced relationships.

Open `pasted-erd-updated.drawio` directly in draw.io. `pasted-erd-updated.xml` is the raw mxGraphModel if you prefer to paste XML.
