# Updated ApaKhabar ERD

Open **apakhabar-erd.drawio** in draw.io / diagrams.net. Start with **00 Core overview**, then use the numbered pages for the full schema. All shapes and attribute rows are editable.

The current source defines **56 Laravel tables + 5 AI-service SQLite tables**, **553 attributes**, and **85 enforced foreign keys**. Chroma's two vector collection patterns are documented separately in the dictionary; engine-internal tables are not included. This describes the result of all current migrations, not the migration status of a deployed database.

## Improvements

- Added nine short-video tables, two guest-comment tables, and `comment_flags`.
- Replaced retired moderation assessment/feedback tables with their two archive tables.
- Removed obsolete moderator/assessment columns and report `reason` fields; included `category`, `explanation`, and moderation-history `action`.
- Added a compact core overview and smaller module-specific pages.
- Separated archives, legacy `two_factors`, Laravel infrastructure, and AI-service SQLite storage.
- Displayed PK/FK/UK markers, nullable fields, composite unique constraints, and parent/child cardinality on connectors.
- Preserved all 85 enforced FKs; references without database constraints are not silently promoted to FKs.

## Files

- `apakhabar-erd.drawio`: complete editable diagram, 15 pages.
- `database-dictionary.md`: all tables and attributes, constraints, vector collections, and reuse prompt.
- `apakhabar-erd.mmd`: Mermaid code for relational tables. Dashed Mermaid lines mean non-identifying relationships, not missing FK enforcement; logical links are explicitly labelled `no_FK`.
- `schema.json`: schema metadata for all 61 relational tables. AI and Laravel stores remain separate physically.
- `previews/*.svg`: static page previews. Numeric endpoint labels show cardinality; use draw.io for full edge labels and crow's-foot symbols.

SQL types are resolved through SQLite. JSON/enum/unsigned/length details can differ on MySQL; consult the original migrations for those native definitions. Table archives intentionally have no enforced parent FKs. Grey boxes are references to entities fully described on another page.

## Rebuild

Run from the AI-service repository:

```sh
php docs/erd/export_laravel_schema.php '../ApaKhabar-Intelligence-Information-News-Management-System' /tmp/apakhabar-erd-schema.json
python3 docs/erd/build_erd.py /tmp/apakhabar-erd-schema.json
```

The exporter forces an isolated in-memory SQLite test connection. It never applies migrations to the configured application database. The generator reads the AI service's CREATE TABLE statements and the installed LangGraph SQLite saver in `.venv`, so that environment must be available. If a new Laravel table appears, update the explicit page groups in `build_erd.py`; coverage validation intentionally fails rather than silently omitting it.

Validation covers entity coverage, all FK columns and targets, XML cell IDs and connector endpoints, key cleanup expectations, and overlapping entity boxes. SVG previews were rendered and representative dense pages visually inspected.
