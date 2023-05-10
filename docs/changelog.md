---
title: Change log
summary: Version history, including for legacy versions.
authors:
  - Gavin Chait
date: 2023-05-03
tags: wrangling, crosswalks, versions
---
# Change log

## Version 1.0.0 (2023-05-10)

This version shares some features with the previous version, but is a complete refactoring and conceptual redesign. It is
not backwardly compatible. Future versions will maintain compatability with this one.

- Separated data models from schema models so that crosswalks are schema-to-schema.
- Complete revision of the API into four discrete `Definition` classes, `SchemaDefinition`, `DataSourceDefinition`,
  `CrosswalkDefinition` and `TransformDefinition`.
- Removed `filters` and `actions` that are no longer relevant (including `REBASE`, and `MERGE`).
- Simplified `CATEGORISE` since it no longer requires deriving terms as part of the crosswalk.
- Crosswalks are designed to support continuous integration.
- Pydantic models are more transparent via each `Definition`'s `.get` property.
- Refactored Pandas to support Modin and Ray for data >1 million rows.
- Mime type support for data sources in `Parquet` and `Feather`.
- Rewrote documentation in MKDocs from Sphinx.
- Revised all tutorials and documentation.

## Legacy version history

- 0.6.2: Fix for parsing ambiguity errors, plus Excel row-count exceeded on save.
- 0.6.1: Minor correction for row count.
- 0.6.0: Ensuring consistent optional column 'name' change for header row, plus new row-count in input and working data.
- 0.5.0: Breaking API changes, including a complete rebuild to support Pydantic and type annotations.
- 0.3.1: Minor documentation corrections & updated Manifest.
- 0.3.0: Introduced `Morph` table restructuring functions.
- 0.2.0: Refactored `Action` wrangling functions to support new drop-in actions.
- 0.1.1: Minor bug fixes.
- 0.1.0: Initial release.