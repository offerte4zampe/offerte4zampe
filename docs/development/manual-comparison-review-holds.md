# P0 — Unverified commercial identities leave comparison groups

The independent 100-case review has two commercially uncertain relations. This
change records an explicit manual review decision, rather than inventing a new
price/stock contradiction or extending a dated suppression proof:

- Bauzaar56961508409669 / Isola000154414 PetUp black lead: the 16 November
  missing-variant proof is historical. The price/fingerprint changed; the normal
  20 November robots-aware recheck is inconclusive. Isola's exact black item is
  independently readable, but the Bauzaar counterpart is not currently verified.
- WebPet52569197674836 / Isola000166136 Askoll Robofood: current selected WebPet
  W01980/EAN8050683000387 still declares "2 sacchetti / 200 ml" in its pack section.
  Isola describes Robofood3; the manufacturer page confirms AA600001 and compatible
  features, but does not explicitly bind its EAN/version to that selling offer.

`comparison-review-holds.json` is a mandatory reviewed manifest. A hold is bound
to an exact merchant and offer ID. It means **unverified for comparison**, not
"different product", unavailable, discounted or wrongly priced. It does not
remove a merchant offer or modify its title, GTIN, quantity, price, availability,
original merchant URL or affiliate URL. Existing feed quantities are preserved;
the hold does not certify an accessory's disputed commercial pack.

Before canonical identity assignment, held offers receive their own unattached
identity. They are excluded from characteristic resolution as both sources and
targets, so name-based matching cannot rejoin them or use them to attach peers.
Derived comparison-review metadata is carried in the model and compact index.
Browser grouping rejects held rows before canonical, characteristic or GTIN/weight
fallback matching. Catalog identity shortcuts, equivalence notes and static
comparison/guide grouping also honor the hold; offers remain searchable. No automatic image
or text-similarity fusion is introduced. No Amazon offer is covered by the
manifest or enabled by this change; tracking flags and merchant programs stay
unchanged.

The review due date is a reminder, never an expiry that silently enables a join.
A changed feed price also cannot authorize equivalence. Release requires an
explicit reviewed removal from the manifest; rebuilding then clears old derived
hold metadata. Missing, malformed, duplicated or improperly bound configuration
aborts the build rather than treating the hold as absent. This prevents invalid
configuration from automatically restoring uncertain comparisons.

The two counterpart canonical groups remain as single-store products. Their old
routes are retained; they no longer meet the existing two-verified-shop indexing
rule. The two held standalone products are also noindex. Other identity groups
remain unchanged; related links may legitimately reflect the split. A canonical
relation can change without rewriting observed price history or original offers.

Validation includes exact two-hold isolation, old peer groups and independent
relations, name-resolver bypass prevention, due/changed-price persistence,
malformed-manifest failure and explicit release/metadata cleanup. Frozen replay
uses a real snapshot and the actual post-review UTC time, not a historical time
before the review decision. Every original offer ID and all price/stock/GTIN/
quantity/merchant and affiliate target values remain identical.

Rollback: revert this PR to remove the scheduling-independent comparison-review
feature, or explicitly remove a resolved hold through a reviewed manifest change.
The former restores the previous grouping, so it is only appropriate after
reassessment. A release still requires successful CI and public catalog/SSR,
SEO/noindex, affiliate HEAD, mobile/desktop and post-deployment checks. Preparing
this branch alone does not certify deployment or P0 closure.
