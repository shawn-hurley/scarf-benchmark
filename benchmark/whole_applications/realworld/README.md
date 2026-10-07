# RealWorld behavior test

`behavior_test.py` is the shared HTTP contract for the Jakarta, Quarkus, and Spring references. It creates uniquely named users and articles, exercises authentication, article editing and discovery, pagination, follows, feed, favorites, comments, and permissions, then deletes its articles.

Each target has a generated, self-contained `test.sh`. This lets runners copy only `test.sh` into a candidate build context without losing the behavior test. After editing the root test, regenerate and check all three entry points:

```bash
bash sync_behavior_test.sh
bash sync_behavior_test.sh --check
```

The target's `test.sh` contains the generated test. When invoking the script directly, set `APP_ORIGIN` or `BASE_URL` to change the host or port. `make test` uses the default port 8080 inside the container. The test always requests `/api` paths and uses `Authorization: Token <jwt>` so changes to the application API are visible.

From a target directory, run `make test` (or `make test DOCKER=podman`). The target Makefile builds the image, starts it, runs the self-contained `test.sh`, and removes the temporary container. ACB can also copy that `test.sh` alone into a generated candidate because it does not need the root Python file at runtime.
