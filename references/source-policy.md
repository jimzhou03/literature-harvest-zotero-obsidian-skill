# Source Policy

## Preferred Sources

- arXiv: use the official API for metadata and open PDF URLs. Respect rate limits and paginate conservatively.
- ACL Anthology: use official paper pages and PDFs for ACL, EMNLP, NAACL, COLING, Findings, and related ACL venues.
- OpenReview: use official paper/forum pages for venues such as ICLR and some NeurIPS workshops.
- PMLR: use official PMLR pages and PDFs for ICML/AISTATS/COLT-style proceedings.
- CVF OpenAccess: use official CVPR/ICCV/ECCV open-access paper pages and PDFs.
- DBLP, Crossref, OpenAlex, Semantic Scholar: use for metadata discovery, venue/year validation, DOI lookup, and deduplication.
- Author/project pages: use only when the PDF is clearly public and attributable.

## Venue Handling

- `ACL`: include ACL main, Findings of ACL, ACL Rolling Review outputs when they map to official paper pages.
- `EMNLP` or user typo `EINLP`: include EMNLP main, Findings of EMNLP, and official ACL Anthology pages.
- `CCL`: search official CCL proceedings pages, CNKI/open proceedings only when access is legitimate, and use DBLP/Semantic Scholar for metadata when no stable public API exists. Do not assume every CCL paper has an open PDF.
- `top journals`: prefer metadata first. Download PDFs only from arXiv, open-access publisher pages, institutional repositories, or author pages.

## Safety Boundaries

- Do not bypass paywalls, CAPTCHA, login walls, rate limits, or robots restrictions.
- Do not mass-download from publisher pages. Use conservative batch sizes and delays.
- Do not fabricate missing BibTeX keys, DOIs, venues, abstracts, datasets, code links, or PDF URLs.
- If only metadata is available, keep the record but mark the analysis as `metadata-only`, `evidence_level: metadata_only`, and `analysis_confidence: low`.

## Ranking Guidance

Score candidates by:

1. Exact phrase match in title or abstract.
2. Synonym match in title or abstract.
3. Venue/year fit.
4. Open PDF availability.
5. Abstract relevance to the user's research intent.
6. Deduplication confidence and metadata completeness.
