# News logic-flow diagrams

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
