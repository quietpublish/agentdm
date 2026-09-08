# Clean-history release snapshot

Prepared 2026-09-08 for `quiet-publish/agentdm`. This is a separate source export,
not a rewrite of the development repository. It starts a new Git history using
the publishing account's GitHub noreply identity. The original history is kept
locally and is not included in this export.

The starting tree is development candidate
`29976a1805cafda37a861868d1e150071347cfbc`. Runtime code, tests, license and
reviewed documentation are preserved. This note and its documentation-index
link are the only additions to that source snapshot.

Dated development records refer to revisions from the original repository;
those commits are provenance references, not ancestors available in this Git
history. Their test results apply to the revisions they name. Export verification
is recorded separately by the maintainer; no hosted CI or live acceptance is
implied by exporting the files.

The MIT copyright notice remains intact. A clean Git history removes old commit
metadata and historical file versions; it does not anonymize the copyright
holder or erase the reviewed development documents kept in this tree.

Creating this snapshot does not create a GitHub repository, publish a release,
activate hooks or satisfy the remaining [release gates](RELEASE_REVIEW.md).
