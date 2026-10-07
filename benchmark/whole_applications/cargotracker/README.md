# CargoTracker behavior test

`behavior_test.py` is the shared HTTP contract for the Jakarta, Quarkus, and Spring references. It requests route candidates for two origin and destination pairs and checks candidate counts, connected legs, known locations and voyages, and that each route reaches the requested destination. Quarkus wraps its route list in `transitPaths`; the test accepts that serialization difference.

Each target has an identical, generated, self-contained `test.sh`. ACB can copy only that file into a candidate. After editing the shared test, regenerate and check the scripts:

```bash
bash sync_behavior_test.sh
bash sync_behavior_test.sh --check
```

From a target directory, run `make test` (or `make test DOCKER=podman`). The Makefile builds the image, starts the app, runs `test.sh` inside the container, and removes the container. Set `BASE_URL` when invoking `test.sh` against another host or port.
