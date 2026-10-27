# ApaKhabar database dictionary and ERD

Generated 26 October 2026 from the current working-tree source in both repositories. This is the **code-defined schema**, not a verification of a deployed database. All 60 Laravel migrations were executed in a disposable in-memory SQLite database in testing mode; no application database was modified. The bundled database/database.sqlite contains an older starter schema and was not used as the schema authority.

There are **56 Laravel tables** (50 operational tables, 2 archives, 1 legacy two_factors table, and jobs, failed_jobs and migrations), **5 AI-service SQLite tables**, and **2 code-defined Chroma collection patterns**. Chroma engine internals are excluded. SQL types below are SQLite-resolved types: Laravel JSON, enum, unsigned sizes and string lengths may be represented differently on MySQL. Consult the original migrations for engine-specific types and enum/check constraints.

PK = primary key; FK = enforced foreign key; UK = single-column unique key. Composite keys and unique constraints are listed after each table. Nullable reflects SQLite introspection; a primary key remains an identity constraint. Diagram pages repeat external referenced tables as key-only reference boxes. Solid connectors are enforced FKs; dashed connectors are explicitly identified logical links. Relationship labels give both endpoint ranges: parent 1 or 0..1, child 0..1 or 0..N. Unique foreign keys correctly produce one-to-one relationships. Solid versus dashed distinguishes enforced from logical relationships in draw.io; Mermaid uses its own identifying/non-identifying line convention. No inferred user-ID relationships are presented as enforced FKs.

## Files

- `apakhabar-erd.drawio`: editable, uncompressed draw.io XML; open it in diagrams.net/draw.io.
- `apakhabar-erd.mmd`: Mermaid ER code for all relational tables.
- `schema.json`: machine-readable schema metadata.

## Table inventory


- **01 Accounts:** `user_roles`, `users`, `emails`, `phones`, `password_reset_tokens`, `personal_access_tokens`

- **02 Broadcasts:** `broadcast_categories`, `channels`, `broadcasts`, `broadcast_channel`, `broadcast_user`

- **03 News:** `news_categories`, `news`, `likes`, `news_viewers`, `news_visits`

- **04 News moderation:** `comments`, `comment_likes`, `comment_reports`, `comment_flags`, `comment_moderation_history`

- **05 Short videos:** `short_videos`, `short_video_publications`, `short_video_viewers`, `short_video_likes`

- **06 Video moderation:** `short_video_comments`, `short_video_comment_likes`, `short_video_comment_reports`, `short_video_comment_flags`, `short_video_comment_history`

- **07 Guests and notifications:** `guest_comment_identities`, `guest_comment_days`, `notifications`

- **08 Intelligence:** `intelligence_documents`, `intelligence_extraction_requests`, `intelligence_information`

- **09 Drafting and review:** `intelligent_news_drafts`, `intelligent_news_draft_sources`, `intelligent_news_draft_versions`, `ai_quality_evaluations`

- **10 AI conversations:** `intelligent_news_sessions`, `intelligent_news_messages`, `intelligent_news_runs`, `intelligent_news_run_events`, `intelligent_news_source_selections`

- **11 Social and analytics:** `social_connections`, `meta_insight_snapshots`, `analytics_settings`, `analytics_setting_changes`, `villager_activity_hours`

- **12 Archives and legacy:** `archived_comment_moderation_assessments`, `archived_comment_moderation_feedback`, `two_factors`

- **13 Laravel infrastructure:** `jobs`, `failed_jobs`, `migrations`

- **14 AI service SQLite:** `runs`, `events`, `progress`, `checkpoints`, `writes`


## 01 Accounts


### `user_roles`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| roleID | integer | PK | No | — |
| name | varchar | — | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `roleID`.

### `users`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| userID | integer | PK | No | — |
| name | varchar | — | No | — |
| password | varchar | — | No | — |
| push_token | varchar | — | Yes | — |
| remember_token | varchar | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| roleID | integer | FK | No | — |
| two_factor_secret | text | — | Yes | — |
| two_factor_recovery_codes | text | — | Yes | — |
| two_factor_confirmed_at | datetime | — | Yes | — |
| date_of_birth | date | — | Yes | — |
| citizenship | varchar | — | Yes | — |
| gender | varchar | — | Yes | — |
| ethnicity | varchar | — | Yes | — |

Primary key: `userID`.

FK: `roleID` → `user_roles.roleID`; on delete: restrict.

### `emails`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| email | varchar | PK | No | — |
| email_verified_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| userID | integer | FK,UK | No | — |

Unique: `userID`.

Primary key: `email`.

FK: `userID` → `users.userID`; on delete: cascade.

### `phones`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| phone | varchar | PK | No | — |
| phone_otp | varchar | — | Yes | — |
| phone_otp_expires_at | datetime | — | Yes | — |
| phone_verified_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| userID | integer | FK,UK | No | — |

Unique: `userID`.

Primary key: `phone`.

FK: `userID` → `users.userID`; on delete: cascade.

### `password_reset_tokens`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| passwordID | integer | PK | No | — |
| email | varchar | — | No | — |
| token | varchar | — | No | — |
| created_at | datetime | — | Yes | — |

Primary key: `passwordID`.

### `personal_access_tokens`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| tokenID | integer | PK | No | — |
| tokenable_id | integer | FK | No | — |
| tokenable_type | varchar | — | No | — |
| name | varchar | — | No | — |
| token | varchar | UK | No | — |
| abilities | text | — | Yes | — |
| expires_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Unique: `token`.

Primary key: `tokenID`.

FK: `tokenable_id` → `users.userID`; on delete: restrict.

## 02 Broadcasts


### `broadcast_categories`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| categoryID | integer | PK | No | — |
| name | varchar | — | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `categoryID`.

### `channels`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| channelID | integer | PK | No | — |
| name | varchar | — | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `channelID`.

### `broadcasts`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| alertID | integer | PK | No | — |
| title | varchar | — | No | — |
| message | text | — | No | — |
| send_mode | varchar | — | No | 'now' |
| status | varchar | — | No | 'tertunda' |
| sent_at | datetime | — | Yes | — |
| scheduled_at | datetime | — | Yes | — |
| archived_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| created_by | integer | FK | No | — |
| categoryID | integer | FK | Yes | — |

Primary key: `alertID`.

FK: `categoryID` → `broadcast_categories.categoryID`; on delete: set null.

FK: `created_by` → `users.userID`; on delete: cascade.

### `broadcast_channel`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| broadcast_id | integer | PK,FK | No | — |
| channel_id | integer | PK,FK | No | — |

Primary key: `broadcast_id, channel_id`.

FK: `channel_id` → `channels.channelID`; on delete: cascade.

FK: `broadcast_id` → `broadcasts.alertID`; on delete: cascade.

### `broadcast_user`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| broadcast_id | integer | PK,FK | No | — |
| user_id | integer | PK,FK | No | — |

Primary key: `broadcast_id, user_id`.

FK: `user_id` → `users.userID`; on delete: cascade.

FK: `broadcast_id` → `broadcasts.alertID`; on delete: cascade.

## 03 News


### `news_categories`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| categoryID | integer | PK | No | — |
| name | varchar | — | No | — |
| description | text | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| slug | varchar | UK | Yes | — |
| status | varchar | — | No | 'active' |
| display_order | integer | — | No | '0' |
| is_default | tinyint(1) | — | No | '0' |
| created_by | integer | FK | Yes | — |
| is_active | tinyint(1) | — | No | '1' |
| deleted_at | datetime | — | Yes | — |

Unique: `slug`.

Primary key: `categoryID`.

FK: `created_by` → `users.userID`; on delete: set null.

### `news`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| postID | integer | PK | No | — |
| title | varchar | — | No | — |
| content | text | — | No | — |
| image | varchar | — | Yes | — |
| likes_count | integer | — | No | '0' |
| view | integer | — | No | '0' |
| excerpt | text | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| category_id | integer | FK | Yes | — |
| status | varchar | — | No | 'active' |
| creation_method | varchar | — | No | 'manual' |
| created_by | integer | FK | Yes | — |
| show_on_homepage | tinyint(1) | — | No | '1' |
| unique_views | integer | — | No | '0' |

Primary key: `postID`.

FK: `created_by` → `users.userID`; on delete: set null.

FK: `category_id` → `news_categories.categoryID`; on delete: set null.

### `likes`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| likeID | integer | PK | No | — |
| created_at | datetime | — | No | CURRENT_TIMESTAMP |
| postID | integer | FK | No | — |
| userID | integer | FK | No | — |

Unique: `postID, userID`.

Primary key: `likeID`.

FK: `userID` → `users.userID`; on delete: cascade.

FK: `postID` → `news.postID`; on delete: cascade.

### `news_viewers`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| news_id | integer | FK | No | — |
| viewer_key | varchar | — | No | — |
| expires_at | datetime | — | Yes | — |

Unique: `news_id, viewer_key`.

Primary key: `id`.

FK: `news_id` → `news.postID`; on delete: cascade.

### `news_visits`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | varchar | PK | No | — |
| expires_at | datetime | — | No | — |

Primary key: `id`.

## 04 News moderation


### `comments`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| commentID | integer | PK | No | — |
| content | text | — | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| newsID | integer | FK | No | — |
| userID | integer | FK | Yes | — |
| parentID | integer | FK | Yes | — |
| guest_name | varchar | — | Yes | — |
| status | varchar | — | No | 'pending_review' |
| ai_flagged | tinyint(1) | — | Yes | — |
| moderation_categories | text | — | Yes | — |
| moderation_reason | varchar | — | Yes | — |
| moderated_at | datetime | — | Yes | — |
| submission_hash | varchar | UK | Yes | — |
| moderation_revision | integer | — | No | '0' |

Unique: `submission_hash`.

Primary key: `commentID`.

FK: `newsID` → `news.postID`; on delete: cascade.

FK: `userID` → `users.userID`; on delete: cascade.

FK: `parentID` → `comments.commentID`; on delete: set null.

### `comment_likes`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| comment_id | integer | PK,FK | No | — |
| user_id | integer | PK,FK | No | — |

Primary key: `comment_id, user_id`.

FK: `user_id` → `users.userID`; on delete: cascade.

FK: `comment_id` → `comments.commentID`; on delete: cascade.

### `comment_reports`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| comment_id | integer | FK | No | — |
| user_id | integer | FK | No | — |
| created_at | datetime | — | No | — |
| resolved_at | datetime | — | Yes | — |
| category | varchar | — | Yes | — |
| explanation | varchar | — | Yes | — |

Unique: `comment_id, user_id`.

Primary key: `id`.

FK: `user_id` → `users.userID`; on delete: cascade.

FK: `comment_id` → `comments.commentID`; on delete: cascade.

### `comment_flags`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| comment_id | integer | FK | No | — |
| moderator_id | integer | FK | No | — |
| category | varchar | — | No | — |
| explanation | varchar | — | Yes | — |
| created_at | datetime | — | No | — |
| resolved_at | datetime | — | Yes | — |

Primary key: `id`.

FK: `moderator_id` → `users.userID`; on delete: cascade.

FK: `comment_id` → `comments.commentID`; on delete: cascade.

### `comment_moderation_history`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| comment_id | integer | FK | No | — |
| moderator_id | integer | — | Yes | — |
| from_status | varchar | — | Yes | — |
| to_status | varchar | — | No | — |
| reason | varchar | — | No | — |
| created_at | datetime | — | No | CURRENT_TIMESTAMP |
| action | varchar | — | Yes | — |

Primary key: `id`.

FK: `comment_id` → `comments.commentID`; on delete: cascade.

## 05 Short videos


### `short_videos`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| created_by | integer | FK | No | — |
| title | varchar | — | Yes | — |
| description | text | — | Yes | — |
| video_url | text | — | No | — |
| video_public_id | varchar | — | No | — |
| thumbnail_url | text | — | No | — |
| thumbnail_public_id | varchar | — | Yes | — |
| frame_offset | numeric | — | No | '0' |
| metadata | text | — | No | — |
| status | varchar | — | No | 'draft' |
| published_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| deleted_at | datetime | — | Yes | — |
| view_count | integer | — | No | '0' |
| likes_count | integer | — | No | '0' |

Primary key: `id`.

FK: `created_by` → `users.userID`; on delete: no action.

### `short_video_publications`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| short_video_id | integer | FK | No | — |
| platform | varchar | — | No | — |
| connection_id | integer | FK | Yes | — |
| account_id | varchar | — | Yes | — |
| account_name | varchar | — | Yes | — |
| graph_host | varchar | — | Yes | — |
| graph_version | varchar | — | Yes | — |
| credential | text | — | Yes | — |
| credential_expires_at | datetime | — | Yes | — |
| container_id | varchar | — | Yes | — |
| media_id | varchar | — | Yes | — |
| permalink | text | — | Yes | — |
| status | varchar | — | No | 'queued' |
| stage | varchar | — | No | 'create' |
| locked_until | datetime | — | Yes | — |
| attempts | integer | — | No | '0' |
| polls | integer | — | No | '0' |
| error_summary | text | — | Yes | — |
| next_attempt_at | datetime | — | Yes | — |
| published_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `id`.

Unique: `short_video_id, platform`.

FK: `connection_id` → `social_connections.id`; on delete: set null.

FK: `short_video_id` → `short_videos.id`; on delete: cascade.

### `short_video_viewers`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| short_video_id | integer | PK,FK | No | — |
| viewer_key | varchar | PK | No | — |
| viewed_at | datetime | — | No | — |

Primary key: `short_video_id, viewer_key`.

FK: `short_video_id` → `short_videos.id`; on delete: cascade.

### `short_video_likes`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| short_video_id | integer | PK,FK | No | — |
| user_id | integer | PK,FK | No | — |

Primary key: `short_video_id, user_id`.

FK: `user_id` → `users.userID`; on delete: cascade.

FK: `short_video_id` → `short_videos.id`; on delete: cascade.

## 06 Video moderation


### `short_video_comments`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| short_video_id | integer | FK | No | — |
| user_id | integer | FK | Yes | — |
| parent_id | integer | FK | Yes | — |
| root_id | integer | FK | Yes | — |
| guest_name | varchar | — | Yes | — |
| content | text | — | No | — |
| status | varchar | — | No | 'pending_review' |
| ai_flagged | tinyint(1) | — | Yes | — |
| moderation_categories | text | — | Yes | — |
| moderation_reason | varchar | — | Yes | — |
| moderated_at | datetime | — | Yes | — |
| moderation_revision | integer | — | No | '0' |
| submission_hash | varchar | UK | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `id`.

Unique: `submission_hash`.

FK: `short_video_id` → `short_videos.id`; on delete: cascade.

FK: `user_id` → `users.userID`; on delete: set null.

FK: `parent_id` → `short_video_comments.id`; on delete: cascade.

FK: `root_id` → `short_video_comments.id`; on delete: cascade.

### `short_video_comment_likes`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| comment_id | integer | PK,FK | No | — |
| user_id | integer | PK,FK | No | — |

Primary key: `comment_id, user_id`.

FK: `user_id` → `users.userID`; on delete: cascade.

FK: `comment_id` → `short_video_comments.id`; on delete: cascade.

### `short_video_comment_reports`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| comment_id | integer | FK | No | — |
| user_id | integer | FK | No | — |
| created_at | datetime | — | No | — |
| resolved_at | datetime | — | Yes | — |
| category | varchar | — | Yes | — |
| explanation | varchar | — | Yes | — |

Primary key: `id`.

Unique: `comment_id, user_id`.

FK: `user_id` → `users.userID`; on delete: cascade.

FK: `comment_id` → `short_video_comments.id`; on delete: cascade.

### `short_video_comment_flags`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| comment_id | integer | FK | No | — |
| moderator_id | integer | FK | No | — |
| category | varchar | — | No | — |
| explanation | varchar | — | Yes | — |
| created_at | datetime | — | No | — |
| resolved_at | datetime | — | Yes | — |

Primary key: `id`.

FK: `moderator_id` → `users.userID`; on delete: cascade.

FK: `comment_id` → `short_video_comments.id`; on delete: cascade.

### `short_video_comment_history`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| comment_id | integer | FK | No | — |
| moderator_id | integer | FK | Yes | — |
| from_status | varchar | — | Yes | — |
| to_status | varchar | — | No | — |
| reason | varchar | — | No | — |
| created_at | datetime | — | No | — |
| action | varchar | — | Yes | — |

Primary key: `id`.

FK: `moderator_id` → `users.userID`; on delete: set null.

FK: `comment_id` → `short_video_comments.id`; on delete: cascade.

## 07 Guests and notifications


### `guest_comment_identities`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| token_hash | varchar | UK | No | — |
| username | varchar | UK | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Unique: `token_hash`.

Unique: `username`.

Primary key: `id`.

### `guest_comment_days`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| guest_id | integer | PK,FK | No | — |
| day | date | PK | No | — |
| comment_count | integer | — | No | — |

Primary key: `guest_id, day`.

FK: `guest_id` → `guest_comment_identities.id`; on delete: cascade.

### `notifications`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| notificationID | integer | PK | No | — |
| type | varchar | — | No | — |
| data | text | — | Yes | — |
| read_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| notifiable_id | integer | FK | No | — |
| notifiable_type | varchar | — | No | 'App\Models\User' |
| alertID | integer | FK | Yes | — |
| postID | integer | FK | Yes | — |
| commentID | integer | FK | Yes | — |

Primary key: `notificationID`.

FK: `commentID` → `comments.commentID`; on delete: set null.

FK: `postID` → `news.postID`; on delete: set null.

FK: `alertID` → `broadcasts.alertID`; on delete: set null.

FK: `notifiable_id` → `users.userID`; on delete: cascade.

## 08 Intelligence


### `intelligence_documents`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| uploaded_by | integer | FK | No | — |
| ai_document_id | varchar | UK | Yes | — |
| original_name | varchar | — | No | — |
| storage_disk | varchar | — | No | 'local' |
| storage_path | varchar | — | No | — |
| mime_type | varchar | — | Yes | — |
| file_size | integer | — | No | — |
| sha256 | varchar | — | No | — |
| status | varchar | — | No | 'processing' |
| embedding_status | varchar | — | No | 'pending' |
| character_count | integer | — | Yes | — |
| error_message | text | — | Yes | — |
| processed_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| processing_attempts | integer | — | No | '0' |
| last_attempted_at | datetime | — | Yes | — |
| archive_after | datetime | — | Yes | — |
| archived_at | datetime | — | Yes | — |
| deleted_at | datetime | — | Yes | — |

Unique: `ai_document_id`.

Primary key: `id`.

FK: `uploaded_by` → `users.userID`; on delete: cascade.

### `intelligence_extraction_requests`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| document_id | integer | FK | No | — |
| requested_by | integer | FK | No | — |
| mode | varchar | — | No | 'general' |
| original_prompt | text | — | Yes | — |
| normalized_query | text | — | Yes | — |
| keywords | text | — | No | — |
| model_name | varchar | — | Yes | — |
| prompt_version | varchar | — | No | 'extraction-v2' |
| status | varchar | — | No | 'pending' |
| error_message | text | — | Yes | — |
| started_at | datetime | — | Yes | — |
| completed_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `id`.

FK: `requested_by` → `users.userID`; on delete: cascade.

FK: `document_id` → `intelligence_documents.id`; on delete: cascade.

### `intelligence_information`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| document_id | integer | FK | No | — |
| item_index | integer | — | No | — |
| type | varchar | — | No | — |
| title | varchar | — | No | — |
| summary | text | — | No | — |
| labels | text | — | No | — |
| fields | text | — | No | — |
| evidence | text | — | No | — |
| confidence | numeric | — | Yes | — |
| search_text | text | — | No | — |
| is_active | tinyint(1) | — | No | '1' |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| extraction_request_id | integer | FK | Yes | — |
| review_status | varchar | — | No | 'approved' |
| quality_score | numeric | — | Yes | — |
| quality_breakdown | text | — | Yes | — |
| information_embedding_status | varchar | — | No | 'pending' |
| reviewed_by | integer | FK | Yes | — |
| reviewed_at | datetime | — | Yes | — |
| deleted_at | datetime | — | Yes | — |

Unique: `extraction_request_id, item_index`.

Primary key: `id`.

FK: `reviewed_by` → `users.userID`; on delete: set null.

FK: `extraction_request_id` → `intelligence_extraction_requests.id`; on delete: set null.

FK: `document_id` → `intelligence_documents.id`; on delete: cascade.

## 09 Drafting and review


### `intelligent_news_drafts`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| created_by | integer | FK | No | — |
| title | varchar | — | No | — |
| excerpt | text | — | No | — |
| labels | text | — | No | — |
| sources_used | text | — | No | — |
| warnings | text | — | No | — |
| user_prompt | text | — | Yes | — |
| status | varchar | — | No | 'draft' |
| published_news_id | integer | FK | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| creation_method | varchar | — | No | 'ai' |
| category_id | integer | FK | Yes | — |
| image | varchar | — | Yes | — |
| version | integer | — | No | '1' |
| reviewed_at | datetime | — | Yes | — |
| show_on_homepage | tinyint(1) | — | No | '1' |
| instagram_media_id | varchar | — | Yes | — |
| facebook_post_id | varchar | — | Yes | — |
| publication_results | text | — | Yes | — |
| publication_started_at | datetime | — | Yes | — |
| image_crops | text | — | Yes | — |
| image_variants | text | — | Yes | — |
| content | text | — | No | — |
| deleted_at | datetime | — | Yes | — |

Primary key: `id`.

FK: `published_news_id` → `news.postID`; on delete: set null.

FK: `created_by` → `users.userID`; on delete: cascade.

FK: `category_id` → `news_categories.categoryID`; on delete: set null.

### `intelligent_news_draft_sources`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| draft_id | integer | FK | No | — |
| information_id | integer | FK | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Unique: `draft_id, information_id`.

Primary key: `id`.

FK: `information_id` → `intelligence_information.id`; on delete: restrict.

FK: `draft_id` → `intelligent_news_drafts.id`; on delete: cascade.

### `intelligent_news_draft_versions`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| draft_id | integer | FK | No | — |
| version | integer | — | No | — |
| change_type | varchar | — | No | — |
| snapshot | text | — | No | — |
| created_by | integer | FK | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| revision_source | varchar | — | No | 'manual' |
| revision_instruction | text | — | Yes | — |

Unique: `draft_id, version`.

Primary key: `id`.

FK: `created_by` → `users.userID`; on delete: cascade.

FK: `draft_id` → `intelligent_news_drafts.id`; on delete: cascade.

### `ai_quality_evaluations`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| draft_id | integer | FK | No | — |
| draft_version_id | integer | FK | Yes | — |
| evaluation_version | varchar | — | No | — |
| evaluator_model | varchar | — | Yes | — |
| overall_score | numeric | — | No | — |
| quality_label | varchar | — | No | — |
| publish_blocked | tinyint(1) | — | No | '0' |
| dimensions | text | — | No | — |
| claim_checks | text | — | No | — |
| warnings | text | — | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| approved_by | integer | FK | Yes | — |
| approved_at | datetime | — | Yes | — |
| approval_note | text | — | Yes | — |
| approved_version | integer | — | Yes | — |

Primary key: `id`.

FK: `approved_by` → `users.userID`; on delete: no action.

FK: `draft_id` → `intelligent_news_drafts.id`; on delete: cascade.

FK: `draft_version_id` → `intelligent_news_draft_versions.id`; on delete: set null.

## 10 AI conversations


### `intelligent_news_sessions`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| created_by | integer | FK | No | — |
| status | varchar | — | No | 'collecting_sources' |
| prompt | text | — | Yes | — |
| selected_document_ids | text | — | No | — |
| selected_information_ids | text | — | No | — |
| user_facts | text | — | No | — |
| pending_questions | text | — | No | — |
| conflicts | text | — | No | — |
| draft_id | integer | FK | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| archived_at | datetime | — | Yes | — |
| clarification_rounds | integer | — | No | '0' |
| title | varchar | — | Yes | — |
| context_summary | text | — | Yes | — |
| current_intent | varchar | — | Yes | — |
| last_message_at | datetime | — | Yes | — |
| deleted_at | datetime | — | Yes | — |

Primary key: `id`.

FK: `draft_id` → `intelligent_news_drafts.id`; on delete: set null.

FK: `created_by` → `users.userID`; on delete: cascade.

### `intelligent_news_messages`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| session_id | integer | FK | No | — |
| role | varchar | — | No | — |
| intent | varchar | — | Yes | — |
| content | text | — | Yes | — |
| tool_name | varchar | — | Yes | — |
| payload | text | — | Yes | — |
| draft_version_id | integer | FK | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| reply_to_id | integer | FK | Yes | — |
| status | varchar | — | No | 'completed' |
| sequence | integer | — | No | '0' |

Primary key: `id`.

FK: `reply_to_id` → `intelligent_news_messages.id`; on delete: set null.

FK: `session_id` → `intelligent_news_sessions.id`; on delete: cascade.

FK: `draft_version_id` → `intelligent_news_draft_versions.id`; on delete: set null.

### `intelligent_news_runs`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| session_id | integer | FK | No | — |
| user_message_id | integer | FK | Yes | — |
| intent | varchar | — | No | — |
| status | varchar | — | No | 'queued' |
| current_stage | varchar | — | Yes | — |
| error_message | text | — | Yes | — |
| started_at | datetime | — | Yes | — |
| completed_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `id`.

FK: `user_message_id` → `intelligent_news_messages.id`; on delete: set null.

FK: `session_id` → `intelligent_news_sessions.id`; on delete: cascade.

### `intelligent_news_run_events`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| run_id | integer | FK | No | — |
| sequence | integer | — | No | — |
| event_type | varchar | — | No | — |
| tool_name | varchar | — | Yes | — |
| label | varchar | — | Yes | — |
| content | text | — | Yes | — |
| payload | text | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Unique: `run_id, sequence`.

Primary key: `id`.

FK: `run_id` → `intelligent_news_runs.id`; on delete: cascade.

### `intelligent_news_source_selections`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| session_id | integer | FK | No | — |
| message_id | integer | FK | Yes | — |
| run_id | integer | FK | Yes | — |
| source_type | varchar | — | No | — |
| information_id | integer | FK | Yes | — |
| document_id | integer | FK | Yes | — |
| url | text | — | Yes | — |
| title | varchar | — | No | — |
| source_snapshot | text | — | Yes | — |
| decision | varchar | — | No | 'pending' |
| decided_by | integer | FK | Yes | — |
| decided_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `id`.

FK: `decided_by` → `users.userID`; on delete: set null.

FK: `document_id` → `intelligence_documents.id`; on delete: set null.

FK: `information_id` → `intelligence_information.id`; on delete: set null.

FK: `run_id` → `intelligent_news_runs.id`; on delete: set null.

FK: `message_id` → `intelligent_news_messages.id`; on delete: set null.

FK: `session_id` → `intelligent_news_sessions.id`; on delete: cascade.

## 11 Social and analytics


### `social_connections`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| user_id | integer | FK | No | — |
| platform | varchar | — | No | — |
| account_id | varchar | — | No | — |
| account_name | varchar | — | No | — |
| access_token | text | — | No | — |
| expires_at | datetime | — | Yes | — |
| invalidated_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| auth_source | varchar | — | Yes | — |
| insights_status | varchar | — | Yes | — |
| insights_synced_at | datetime | — | Yes | — |

Primary key: `id`.

Unique: `user_id, platform`.

FK: `user_id` → `users.userID`; on delete: cascade.

### `meta_insight_snapshots`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| connection_id | integer | FK | No | — |
| account_id | varchar | — | No | — |
| metric | varchar | — | No | — |
| period | varchar | — | No | 'day' |
| period_end | datetime | — | No | — |
| value | integer | — | No | — |
| synced_at | datetime | — | No | — |

Unique: `connection_id, account_id, metric, period_end`.

Primary key: `id`.

FK: `connection_id` → `social_connections.id`; on delete: cascade.

### `analytics_settings`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| widgets | text | — | No | — |
| layout | text | — | Yes | — |
| meta_connection_ids | text | — | Yes | — |
| period_days | integer | — | No | '30' |
| updated_by | integer | FK | Yes | — |
| tracking_started_at | datetime | — | No | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |

Primary key: `id`.

FK: `updated_by` → `users.userID`; on delete: set null.

### `analytics_setting_changes`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| user_id | integer | FK | Yes | — |
| configuration | text | — | No | — |
| created_at | datetime | — | No | — |

Primary key: `id`.

FK: `user_id` → `users.userID`; on delete: set null.

### `villager_activity_hours`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| user_id | integer | FK | No | — |
| hour | datetime | — | No | — |
| platform | varchar | — | No | — |

Primary key: `id`.

Unique: `user_id, hour, platform`.

FK: `user_id` → `users.userID`; on delete: cascade.

## 12 Archives and legacy


### `archived_comment_moderation_assessments`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| comment_id | integer | — | No | — |
| classification | varchar | — | No | — |
| ai_flagged | tinyint(1) | — | Yes | — |
| categories | text | — | Yes | — |
| category_scores | text | — | Yes | — |
| reason | varchar | — | Yes | — |
| initial_status | varchar | — | Yes | — |
| requested_model | varchar | — | Yes | — |
| returned_model | varchar | — | Yes | — |
| source | varchar | — | No | — |
| assessed_at | datetime | — | Yes | — |
| created_at | datetime | — | No | CURRENT_TIMESTAMP |
| comment_snapshot | text | — | Yes | — |
| source_sha256 | varchar | — | No | — |
| archived_at | datetime | — | No | CURRENT_TIMESTAMP |

Primary key: `id`.

### `archived_comment_moderation_feedback`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| comment_id | integer | — | No | — |
| assessment_id | integer | — | No | — |
| history_id | integer | UK | No | — |
| administrator_id | integer | — | Yes | — |
| classification | varchar | — | No | — |
| category | varchar | — | No | — |
| explanation | varchar | — | Yes | — |
| verification_status | varchar | — | No | — |
| request_id | varchar | UK | No | — |
| expected_revision | integer | — | No | — |
| created_at | datetime | — | No | CURRENT_TIMESTAMP |
| comment_snapshot | text | — | Yes | — |
| history_snapshot | text | — | Yes | — |
| administrator_snapshot | text | — | Yes | — |
| source_sha256 | varchar | — | No | — |
| archived_at | datetime | — | No | CURRENT_TIMESTAMP |

Unique: `history_id`.

Unique: `request_id`.

Primary key: `id`.

### `two_factors`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| two_factor_secret | varchar | PK | No | — |
| two_factor_recovery_codes | text | — | Yes | — |
| two_factor_confirmed_at | datetime | — | Yes | — |
| created_at | datetime | — | Yes | — |
| updated_at | datetime | — | Yes | — |
| userID | integer | FK,UK | No | — |

Primary key: `two_factor_secret`.

Unique: `userID`.

FK: `userID` → `users.userID`; on delete: cascade.

## 13 Laravel infrastructure


### `jobs`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| queue | varchar | — | No | — |
| payload | text | — | No | — |
| attempts | integer | — | No | — |
| reserved_at | integer | — | Yes | — |
| available_at | integer | — | No | — |
| created_at | integer | — | No | — |

Primary key: `id`.

### `failed_jobs`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| uuid | varchar | UK | No | — |
| connection | text | — | No | — |
| queue | text | — | No | — |
| payload | text | — | No | — |
| exception | text | — | No | — |
| failed_at | datetime | — | No | CURRENT_TIMESTAMP |

Unique: `uuid`.

Primary key: `id`.

### `migrations`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | integer | PK | No | — |
| migration | varchar | — | No | — |
| batch | integer | — | No | — |

Primary key: `id`.

## 14 AI service SQLite


### `runs`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | TEXT | PK | Yes | — |
| owner | TEXT | — | No | — |
| request_hash | TEXT | — | No | — |
| status | TEXT | — | No | — |
| response | TEXT | — | Yes | — |
| lease | REAL | — | No | 0 |

Primary key: `id`.

### `events`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | INTEGER | PK | Yes | — |
| run_id | TEXT | — | No | — |
| data | TEXT | — | No | — |

Primary key: `id`.

### `progress`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| id | TEXT | PK | Yes | — |
| updated | REAL | — | Yes | — |
| data | TEXT | — | Yes | — |

Primary key: `id`.

### `checkpoints`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| thread_id | TEXT | PK | No | — |
| checkpoint_ns | TEXT | PK | No | '' |
| checkpoint_id | TEXT | PK | No | — |
| parent_checkpoint_id | TEXT | — | Yes | — |
| type | TEXT | — | Yes | — |
| checkpoint | BLOB | — | Yes | — |
| metadata | BLOB | — | Yes | — |

Primary key: `thread_id, checkpoint_ns, checkpoint_id`.

### `writes`

| Attribute | Type | Key | Nullable | Default |
|---|---|---|---|---|
| thread_id | TEXT | PK | No | — |
| checkpoint_ns | TEXT | PK | No | '' |
| checkpoint_id | TEXT | PK | No | — |
| task_id | TEXT | PK | No | — |
| idx | INTEGER | PK | No | — |
| channel | TEXT | — | No | — |
| type | TEXT | — | Yes | — |
| value | BLOB | — | Yes | — |

Primary key: `thread_id, checkpoint_ns, checkpoint_id, task_id, idx`.

## AI persistence notes

`runs` and `events` live in `agent_db_path + '.runs'`; `progress` lives in `agent_db_path + '.extractions'`. `checkpoints` and `writes` live at `agent_db_path` and are library-managed by the installed LangGraph SQLite saver. The default base path is `./data/agent/checkpoints.sqlite`.

`events.run_id` logically references `runs.id`, but SQLite does not enforce an FK. `writes` logically associates with `checkpoints` using `(thread_id, checkpoint_ns, checkpoint_id)`; no FK is declared. `parent_checkpoint_id` records checkpoint ancestry within the same thread and namespace. `runs.id` is a hash of owner and external run ID, so it must not be drawn as an FK to Laravel `intelligent_news_runs.id`. SQLite permits NULL in some non-integer primary key declarations here; application code supplies IDs.

## Chroma vector collections

| Collection | Stored attributes |
|---|---|
| `approved_information_<embedding fingerprint>` | id (SHA-256 of owner_id:information_id), embedding, document (serialized KnowledgeItem), metadata: owner_id, information_id, document_id, review_status, is_active, archived |
| `apakhabar_documents` | id (document_id:chunk_index), embedding, document (chunk text), metadata: document_id, filename, source, chunk_index |

KnowledgeItem document fields: `information_id`, `document_id`, `owner_id`, `title`, `summary`, `labels`, `fields`, `evidence`, `source`, `review_status`, `is_active`, `archived`. These are vector-store records, not relational SQL tables. References to Laravel records are application-level only. Raw-document collection code is present; this inventory does not claim it is populated or used by the approved-evidence agent flow.

## Schema details to preserve in your report

- Drafts now use `title`, `excerpt`, and `content`; the old `headline`, `subheadline`, `lead`, and `body` columns are not in the final schema.
- `two_factors` is retained as a legacy table. Its enrollment data is copied into `users` by the Fortify migration; active authentication uses `users`.
- The latest cleanup removes `comments.moderator_id`, `short_video_comments.moderator_id`, and `short_video_comments.moderation_assessment`. `comment_moderation_history.moderator_id` remains without an enforced FK.
- Both report tables now store `category` and `explanation`; their old `reason` columns are removed.
- `comment_moderation_assessments` and `comment_moderation_feedback` are retired; their `archived_...` replacements preserve snapshots without foreign keys. `comment_flags` is the active moderator flag table.
- Guest identity tables are present, but comments have no guest_id FK; no link is invented.
- The overview is deliberately selective. Every relational table and column appears on its detailed page.
- JSON arrays such as selected document/information IDs and meta connection IDs are attributes, not normalized junction tables or enforced FKs.
- `news_visits` has only `id` and `expires_at`; do not invent a news_id relationship.

## Reusable diagram prompt

Create an editable crow's-foot ERD from the attached schema.json and database dictionary. Preserve every exact table and attribute name. Display PK, FK, single-column unique keys, composite constraints, and nullable parent relationships. Group tables into Accounts, Broadcasts and notifications, News and moderation, Intelligence and drafting, AI conversations, Social and analytics, Laravel infrastructure, and AI service SQLite. Use separate pages and key-only reference boxes for cross-page entities. Draw solid lines only for foreign_keys in schema.json. Draw the documented AI logical relationships as dashed lines explicitly marked 'logical; no FK'. Keep Chroma collections in a separate non-relational section. Do not infer foreign keys from column names or JSON arrays, and do not restore removed legacy draft columns.

## Sources

- Laravel: `database/migrations/*.php` in ApaKhabar-Intelligence-Information-News-Management-System.
- AI service: `app/services/agent_service.py`, `app/services/extraction_progress.py`, `app/services/knowledge_service.py`, `app/services/rag_service.py`, `app/schemas/knowledge.py`.
- Installed LangGraph schema: `.venv/lib/python3.12/site-packages/langgraph/checkpoint/sqlite/__init__.py`.
