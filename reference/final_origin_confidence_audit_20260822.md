# Final origin-confidence audit

**Reviewed:** 22 August 2026; catalogue replacements checked 2 September 2026
**Scope:** final balanced 100-band catalogue  
**Result:** publication-ready with one disclosed medium-confidence assignment

## Technical summary

All 34 records selected for the original independent review passed through a
second-source origin check: the 30 bands contributing at least 10% of their
FUA's selected monthly-listener total, plus the four records that were still
medium-confidence before that audit. The 14 bands introduced during the final
catalogue comparison were then checked against the completed 1,000-band origin
fact-check. Every incoming band has a resolved FUA assignment. Chumbawamba
remains the catalogue's only medium-confidence case because credible accounts
disagree between Burnley and the Armley squat in Leeds.

The four pre-audit medium-confidence records are resolved. Editors is explicitly
recorded as formed in Birmingham. Happy Mondays, Joy Division and New Order have
Salford-area origins, and the frozen OECD crosswalk assigns Salford municipality
to Manchester FUA. The audit also made The 1975's locality explicit: Wilmslow is
in Cheshire East, which the crosswalk assigns to Manchester FUA.

No published rank changes. Under the revised catalogue, excluding Chumbawamba
as a conservative bound lowers Leeds's all-ten quotient from 8.989 to 7.459 and
its dominant-band-removed quotient from 6.348 to 4.817, but Leeds remains ninth
and eighth respectively. Excluding Editors leaves Birmingham fifth in both the
primary and dominant-band-removed rankings.

The machine-readable record of the original audit is
[`final_origin_confidence_audit_20260822.csv`](../data/processed/final_origin_confidence_audit_20260822.csv).
The replacement decisions are recorded in
[`top1000_origin_fact_check_decisions_20260902.csv`](top1000_origin_fact_check_decisions_20260902.csv)
and the current catalogue.

## Scope and method

A record entered the audit when either condition held:

1. its July 2026 monthly listeners were at least 10% of its FUA's selected
   ten-band total; or
2. its origin confidence was not `high` before the audit.

Each selected record was checked against a source independent of the catalogue's
MusicBrainz evidence. Localities outside the study-city label were then checked
against the frozen municipality-to-FUA crosswalk. The audit changed evidence
metadata and confidence only; it did not refresh Spotify measurements or alter
the selected ten-band catalogues.

## Catalogue-replacement addendum

The final comparison introduced 14 bands whose origins had already been checked
in the 1,000-band audit:

| FUA | Incoming bands | Origin decision |
|---|---|---|
| London | The Police; Pink Floyd | London confirmed. |
| Birmingham | Fine Young Cannibals; Steel Pulse | Birmingham confirmed; Steel Pulse's more specific Handsworth label remains inside the same FUA. |
| Manchester | The Verve | Wigan confirmed and mapped to Manchester FUA. |
| Glasgow | Stealers Wheel; Travis; Wet Wet Wet | Paisley, Glasgow and Clydebank respectively, all mapped to Glasgow FUA. |
| Liverpool | CamelPhat; Orchestral Manoeuvres in the Dark | Liverpool and Meols respectively, both mapped to Liverpool FUA. |
| Leeds | The Cult; Yard Act | Bradford and Leeds respectively, both mapped to Leeds FUA. The Cult's Bradford formation was retained after adjudicating MusicBrainz's later London association. |
| Sheffield | The Last Shadow Puppets; Ace | Sheffield confirmed. |

The 14 decisions affect catalogue composition and listener totals, but none
introduces an unresolved FUA mapping. The Cult's source variation and Steel
Pulse's city-versus-neighbourhood wording are retained in the evidence trail.

## Records requiring a decision

| Band | Finding | Decision |
|---|---|---|
| Editors | [AllMusic](https://www.allmusic.com/artist/editors-mn0000459860) records formation in Birmingham in 2002, while noting that the members met at Stafford University. | Upgrade to high. |
| Happy Mondays | [Official Charts](https://www.officialcharts.com/artist/26199/happy-mondays/) gives Salford; another history identifies Little Hulton. Salford maps to Manchester FUA. | Upgrade to high. |
| Joy Division | The [official band history](https://www.joydivisionofficial.com/aboutus.html) describes the group as formed by members from Salford and Macclesfield. Salford maps to Manchester FUA. | Upgrade to high. |
| New Order | [AllMusic](https://www.allmusic.com/artist/new-order-mn0000334193) gives Salford. Salford maps to Manchester FUA. | Upgrade to high. |
| The 1975 | [AllMusic](https://www.allmusic.com/artist/the-1975-mn0002986022) gives Wilmslow. Cheshire East maps to Manchester FUA. | Retain high; make the locality explicit. |
| Chumbawamba | [AllMusic](https://www.allmusic.com/artist/chumbawamba-mn0000781370) gives Burnley, while another published account describes formation in an [Armley squat in Leeds](https://towardfreedom.org/wp-content/uploads/2009/06/PM%202009%20Catalog%20Optimized.pdf). | Retain Leeds provisionally at medium confidence and disclose the exclusion bound. |

## Evidence coverage

- 34 of 34 originally targeted records have a recorded independent source.
- All 14 incoming replacement bands have a resolved origin in the 1,000-band
  fact-check.
- 33 audited assignments are high-confidence; one is medium-confidence.
- The full 100-band final catalogue is now 99 high-confidence and one
  medium-confidence, with no blank or `review_required` record.
- All 30 bands above the 10% influence threshold were reviewed.

## Limitations

This is an origin-assignment audit, not a test that the selected catalogues are
representative. Independent biographies can repeat one another, and a band's
formation can reasonably be associated with members' home town, first
rehearsal, communal base or first use of its final name. The Chumbawamba conflict
is therefore retained instead of being forced into false precision.

The ranking remains a comparative index of global Spotify attention in July
2026 divided by 2024 FUA population. This audit does not turn it into a local
listening rate or a historical productivity measure.

## Publication action

Item 5 is complete. The first article can use the audited catalogue, provided it
describes Chumbawamba's Leeds assignment as provisional or includes the
no-Chumbawamba sensitivity. A later article can revisit contested formation
geographies with archival or interview evidence; that extra research is not
needed to publish the current ranking because neither tested rank changes.

## Further questions

- Would a rule based on first public performance, rather than formation, resolve
  contested origins more consistently?
- Should future catalogues record multiple origin localities with explicit
  weights instead of forcing one FUA?
- Does repeating the audit at a 5% influence threshold surface any additional
  assignment that changes a rank?
