# Loop 278: Shared Baseline Execution Deadline

## Evidence And Scope

The previous turn is verified progress: Loop 277 shipped faster owned HTTP
fixtures without removing checks or changing production policy. Current main
`edb1127` is clean, its seven CI jobs passed, and no open issue is present.
Remaining release-gate timing is the roadmap's explicit next-selection evidence.

The baseline currently checks the 600-second limit only before each check, then
gives every child a fresh 180 seconds. A check admitted near the suite deadline
can therefore exceed the advertised execution budget. `subprocess.run` also
terminates only its direct child on timeout; trusted checks can spawn services,
builds and other subprocesses that remain in the inherited group.

Use one monotonic execution deadline and pass the smaller of 180 seconds and
the remaining 600-second budget to each built-in command. An exhausted budget
must admit no new child, retain all 19 fixed verdict entries and report failure
through the existing timeout/skipped contract, not a partial pass.

On qualified POSIX hosts, launch each fixed check in a new session/process group.
On timeout or interruption while the direct child is still unreaped, kill only
that owned group and reap the direct child
before ordinary artifact cleanup. If cleanup cannot be confirmed, stop the
bundle and preserve its owner-only work directory instead of deleting artifacts
under potentially live writers. Unsupported supervision must fail before launch.
No caller-selected command, process group or new CLI flag is added.

The deadline governs check execution, including time spent starting a child.
OS scheduling/process creation, bounded reap handling and filesystem cleanup
are not a hard ten-minute wall-clock SLA. Document this distinction rather than
claiming an impossible bound over arbitrary OS stalls or detached descendants.
No arbitrary process-tree, container-escape or hostile-detachment guarantee.

## Verification

Write red tests for shared remaining budget, zero budget without launch, real
short timeouts, same-group descendant shutdown, bounded reap, cleanup refusal
and unchanged success/nonzero-exit semantics. Use only owned loopback listeners
and synthetic temporary files; ensure old-behavior reproduction cleans its own
orphan. Keep the evidence schema, 19 checks, 180/600 limits and legacy injected
test-runner signature unchanged. Run focused/full suites, editor regressions,
isolated wheel, seven CI jobs and complete release preflight. No product runtime,
DSL, release/tag, dependency or maturity change; keep the broad goal active.

## Implementation And Initial Evidence

Two regressions failed against the previous implementation: the next command
received no remaining-budget cap, and a real synthetic same-group child listener
survived its parent's timeout. The reproduction's finalizer explicitly stopped
that owned listener, so the red test itself did not leave a process behind.

The supervisor now creates an independent session for each fixed check, accounts
for process-start elapsed time, caps wait to the shared remaining budget, and
never signals an already reaped PID after a late exit. Late zero exits are failed
timeouts, not passes. Zero/nonfinite budgets launch nothing. Further regressions
first failed on nonfinite budget admission and late-success acceptance before
those branches were corrected.

Eleven new regressions also cover bounded reaping, interruption, unavailable
supervision, fixed CLI errors and preserved artifacts on unconfirmed cleanup.
The focused baseline/release suite passed 28 tests. Existing evidence fields,
19-check membership and injected test-runner signature are unchanged. The
documentation now separates the execution budget from OS/reap/filesystem wall
time, and explicitly scopes descendant handling to inherited POSIX groups.

A further regression exposed the relative-budget handoff window: a command
could otherwise rebase its allotted duration after preparation delay. Both the
remaining cap and the same absolute suite deadline now reach the supervisor;
an expired absolute deadline refuses before process creation. The initial full
run predates this final guard and is not treated as final-source qualification.

## Final Local Qualification

The final CLI production-baseline command passed all 19 checks under the new
supervisor, including the unchanged full unit-discovery command. Independent
discovery confirms 1,445 tests; all final deadline/release regressions passed
28 focused tests. Public evidence is
`/tmp/skill2workflow-production-baseline-loop278/production-baseline-evidence.json`.
The earlier standalone 1,445-test run passed in 99.719 seconds, but predates the
absolute-deadline handoff guard and is not substituted for the final CLI run.

All 30 editor regressions passed. Isolated-wheel qualification passed with 94
members, SHA-256
`56142fbb3aa7cd5f8b215db5cd1511ec238829ee2dc5e735f80007fd3b91c65a`,
at `/tmp/skill2workflow-package-loop278-final`. Every installed runtime Python
module matches source byte-for-byte; no runtime, web asset, package dependency or
Workflow DSL changed. The baseline supervisor remains a source-maintenance
script rather than a newly distributed runtime capability. Repository secret
hygiene and whitespace checks passed. Owned listeners/processes were closed;
only fixed public evidence and its safety marker remain in the baseline root.

## Remote Qualification

Qualified implementation: `e3be3c8ffb937fa4fd615d24dac8ab6173cb5355`.
[CI](https://github.com/pearjelly/skill2workflow/actions/runs/39786584218)
passed all seven jobs, including Python 3.9/3.14, installed wheel qualification,
real user journeys, editor regressions, Docker, systemd and recovery/state safety.
The Python 3.14 unit job explicitly records all 1,445 tests passing in 85.473
seconds, independently qualifying the final feature source rather than relying
on the earlier pre-guard local run.
[Release preflight](https://github.com/pearjelly/skill2workflow/actions/runs/39786621966)
passed on its first attempt in 4m49s with Python 3.9.25. The terminal job log
explicitly records `PASSED command:production_baseline` under the final supervisor.
This is qualification of the fixed execution/cleanup path, not an assertion of
an absolute wall-clock bound over OS or filesystem stalls.

Roadmap closure passed 120 focused feature/documentation tests in 0.870 seconds,
plus repository secret hygiene and whitespace checks. No tag, package release,
live-provider operation or maturity promotion was performed. The broad project
goal remains active.
