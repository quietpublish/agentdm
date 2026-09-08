# Release review — 2026-09-07 CDT

Status: local hardening candidate, **not approved for publication**. Installed
main remains `025863e`. The release branch is `test/public-readiness-contracts`.
No hook activation, remote creation or paid model use accompanies these tests.

## 2026-09-08 update: license and reader-facing documentation

The owner selected MIT; [LICENSE](../LICENSE) now carries the notice under
Matthew Wright, matching the repository author name. The license-choice gate
below is closed in this candidate. Public-history/privacy approval is not.

The README now introduces the tool and routes readers to separate setup, usage,
hook and trust guides. [The documentation index](README.md) classifies every
existing document by audience. Development records retain their paths and
dated evidence; personal filesystem examples are generalized in the current
tree only. Reachable historical paths/emails are unchanged. Older receipts
below describe the revisions actually scanned and tested, not the new tree.

Host instructions were checked against official Codex and Claude references;
universal timeout/environment/recovery claims were removed from the user path.
MIT covers this project's material; linked third-party sources retain their own
terms. No license rider or extra restriction has been added to the MIT grant.

Documentation tests were committed first at `4d194eb`: DOC-01/03/04 fail with
nine assertions/subcases at the old reader surface; existing local-link coverage
passes. `d61f172` adds exact hook-event wiring and a separately observed red
DOC-05 for personal paths. Implementation/documentation candidate `a93a31e`
changes no files under `agentdm/`, `hooks/` or `bin/` relative to `4f6bafb`.
Its complete suite passes all 64 tests on local Python 3.11.15, exit 0, 41.367s.
The prior runtime platform receipts remain historical; this is not a newly
executed full 64-test matrix on every platform. Host setup was not activated.

The five documentation scenarios also pass on local Python 3.9.6 (1.918s)
and 3.14.6 (0.915s). On Python 3.11.15, all sixteen selected mutations are
rejected by assertions, exit 0, none invalid/surviving; the two new mutations
break a reader link and a hook event. These checks do not execute host settings,
check remote URLs or validate Markdown anchors. Final journal/receipt additions
are documentation-only and receive another documentation check before handoff.

## Second tests-first slice

Executable candidate: `5a37e88ebbb0feea84cf174fccba0f05153a3b78`.
The [GWT contract](TEST_CONTRACT.md) names each scenario.

| Red commit / base | Observed red | Repair |
| --- | --- | --- |
| `38a7bbd` / `c76f841` | AC-12–15: four scenarios, ten failing assertions/subcases | `e38839f`: exact sender match, active-wait registration refusal, finite typed bounds, decoder recursion handling |
| `ed07983` / `e38839f` | PL-01/02: repeat close and fork callback close an unrelated reused descriptor | `0daa896`: retire the descriptor before close |
| `6fa692d` / `0daa896` | CL-01/02: invalid usage and non-Git errors; CL-03 positive control already passes | `5a37e88`: usage validation before store resolution, concise project error |

The initial CLI red test shared a state directory across invalid-argument
subcases. The final fixture gives each its own directory; the mutation control
must also fail with that corrected isolation. Already-green positive controls
are not represented as newly discovered bugs.

The presence bug is more than a duplicate-close nicety: the registered fork
callback outlives the open descriptor. Descriptor numbers are recycled, so a
callback that remembers a number without remembering closure can affect a
different resource. The test forks a real child and checks that resource there.

## Verification

Final executable source remained unchanged during these sequential full-suite
runs (`PYTHONDONTWRITEBYTECODE=1 <python> -m unittest discover -s tests -p 'test*.py'`):

| Platform | Python | Tests | Exit | Seconds |
| --- | --- | --- | --- | --- |
| Local macOS | 3.9.6 | 59 | 0 | 70.735 |
| Local macOS | 3.11.15 | 59 | 0 | 45.341 |
| Local macOS | 3.14.6 | 59 | 0 | 42.070 |
| Offline Linux container (amd64 emulation) | 3.14.7 | 59 | 0 | 77.207 |

`python3 tests/run_mutation_checks.py` on local Python 3.11.15 rejects all
fourteen deliberately broken implementations by assertion, exit 0, no survivors
or invalid mutations. The expanded set adds sender substring matching, wait
owner replacement, nonfinite bounds, decoder recursion, reused descriptors and
CLI usage side effects to the earlier eight cases. This is selected contract
coverage, not an overall mutation score.

Earlier intermediate `0daa896` ran 56 tests successfully on
local macOS Python 3.9.6 (55.045s) and offline Linux Python 3.14.7 (64.887s).
Those intermediate results are not substituted for final-candidate receipts.

Linux uses the existing `agent-gwt/base:local` image, ID
`sha256:78cca82201d06520dbd312bad5585f565d1d7953744e7af318ac4608a7480566`.
It is linux/amd64 under local Docker emulation, not a hosted CI runner or another
physical machine. The container is unprivileged, network-disabled and read-only,
with only the candidate mounted read-only and disposable writable temporary
state. No image download, credentials, installed host configuration or live
mailbox is needed. Hosted matrix remains unexecuted.

## Public-disclosure review

A read-only scan at `5a37e88` inspected all 24 reachable commits, 182 Git
objects and 87 unique blobs available in this local clone. It checked private
key headers, recognizable GitHub/OpenAI/npm/Supabase/AWS token formats and a
credential-assignment pattern. **No matches for those patterns.** This is not a
secret-free certification: opaque secrets, deleted/unreachable objects, external
logs and runtime stores are outside what these patterns establish.

Ten historical blobs contain personal absolute paths, across `README.md`,
`docs/PRIOR_ART_SYNTHESIS_2026_09_07.v1.md`, `docs/lane-3-native-cli.md` and
`docs/lane-4-substrates.md`; the last also contains a private scratch reference.
All 24 commits use non-noreply author emails. Values were not printed by the
scan. The owner must decide whether that history is intended for disclosure or
whether to prepare a reviewed clean-history export. No history was rewritten.

No LICENSE is tracked. License choice remains the owner's decision. The earlier
diagnostic credential exposure recorded in [PUBLIC_READINESS.md](PUBLIC_READINESS.md)
also remains an operator rotation action; never publish raw session logs.

## Remaining release gates

- Owner-selected license and an explicit public-history/privacy decision.
- Hosted Linux/macOS Python matrix on the publication candidate, when a staging
  push is authorized. A local Linux container is useful independent evidence,
  not that hosted receipt.
- Real darker launch-path hook silence with a positive control proving hooks
  dispatch; tool/marker pins and direct-hook tests remain narrower evidence.
- Approved two-step hook pilot and an ordinary working day of truthful roster
  state and claims-mediated collaboration; then a second-machine install/exchange.
- Final release diff/content review after license/history choices. There is no
  claim that this bounded review exhausts races or malformed-input cases. In
  particular, transport input has no byte-size limit; recursion handling is not
  a memory bound. Wait budgeting is per incarnation, not a hard authorization
  boundary across re-registration or reconnects.

The intended support scope remains single-user, same-machine local messaging on
Unix-like systems. No Windows, cross-user authentication, remote messaging,
Gemini or Cursor verification follows from these results. The public README
must retain the experimental and host-acceptance limitations until evidence
actually changes them.
