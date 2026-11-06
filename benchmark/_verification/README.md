# Migration verification

This verifier belongs to the benchmark and works without an agent harness.
It builds the submitted root Maven reactor and launches exactly one packaged
Quarkus JVM application, regardless of module names. Removed or renamed modules
are allowed; zero or multiple runnable applications fail explicitly. Reference
database and broker startup commands are retained. HTTP ports and database
credentials come from the trusted benchmark deployment contract.

The behavior policy defaults to `target`. For Jakarta-to-Quarkus, `source` runs
the unchanged assertion script from the frozen conversion's `input/test.sh`.
`either` first tries the complete target-reference contract and, if the Quarkus
build succeeds but behavior fails, tries the complete source contract. Individual
assertions are never mixed between contracts. The source framework's test
selector and listener are set explicitly while the application runs on Quarkus.
Candidate-provided tests cannot substitute for frozen assertions.

Verify a saved native conversion (containing `input/`, `output/`, and
`metadata.json`) with the Scarf CLI and Docker available:

```sh
python3 benchmark/_verification/verify.py \
  --conversion /path/to/saved/run_1 \
  --validations-dir benchmark \
  --artifacts /path/to/new/verification \
  --policy either
```

The artifact directory must be fresh. This command makes disposable copies;
it does not modify the saved submission or call a model. Podman users can put
their Docker-compatible CLI shim on `PATH`.

`verification-contract.json` records the matched contract and every attempt.
`quarkus-verifier.json` records the trusted recipe hashes, listener, and deployment
environment keys. Different behavior policies represent different grading rules.

Harness integrations may call `grade_contracts` with their native grading callback
and `prepare_profile` on a private validation tree. Freeze this entire directory
with each task, alongside the reference tests, to make verification reproducible.

Run the verifier checks with:

```sh
python3 -m pytest benchmark/_verification/tests -q
```
