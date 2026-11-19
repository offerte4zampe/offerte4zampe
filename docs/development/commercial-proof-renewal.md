# P0 — Renew exact commercial contradictions before expiry

The audit previously skipped every fingerprint-matching observation younger than
24 hours. That also skipped missing-variant and price/stock contradictions, so a
scheduled run just before expiry could not renew the proof. After expiry, those
rows shared priority with unverified weight conflicts; never-checked rows with
an empty timestamp could precede an older exact contradiction.

The selector now makes previously verified, exact, source-bound missing-variant
and price/stock contradictions eligible after 12 hours. It reuses the existing
suppression proof validation at the historical observation time solely to rank
rechecks. The live publication gate still requires a matching, freshly verified
proof within 24 hours: no expiry extension or persistent quarantine is added.

Renewals precede weight conflicts and ordinary rotating checks. The existing
four-offer budget per merchant is unchanged. Oldest critical observations are
checked first; a successful recheck moves that observation behind other due
critical rows. No product or merchant offer ID is hardcoded in selection.

Current revalidation (19 November): the original 16 November seed is expired
and is not carried forward. The current feed price changed to EUR18.90, so its
fingerprint also differs. Rechecking through the normal robots-aware Checker
returned robots_unverified_or_disallowed; there is no fresh suppression proof.
The branch preserves the complete current main cache without renewal or edits.
This scheduling change alone does not certify the current affected offer and
must not be described as having removed it from production.

Limits: more than four due critical rows, unavailable network, inconclusive
merchant responses or failed scheduled runs can still leave a row without a
fresh proof. Such observations remain unknown and cannot be suppressed by an
expired proof. No source fields are inferred or replaced from a default variant.
The 16 November post-build snapshot showed the target eligible at the 22:00 audit;
that does not establish why the actual pre-audit run did not choose it. The
specific cause of that selection remains unverified without its input snapshot
or candidate log.

Validation: selector regression tests cover the 12h boundary, exact proof binding,
unchanged four-row budget, fairness among due critical rows, expired publication
proofs and ordinary rotation. A historical frozen replay on 16 November with its then-valid observation
withheld only the selected missing variant. That replay does not apply to the
changed current price and does not establish a current exclusion.
No merge or deployment is authorized by this change. Rollback: revert the
scheduling change; the current main cache is unchanged by this branch.
