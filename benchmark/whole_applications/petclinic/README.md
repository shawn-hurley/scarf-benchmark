# PetClinic behavior contract

`behavior_test.py` is the single source for the three generated `test.sh` files. Each script embeds the complete test because ACB copies only the target's `test.sh` into a candidate. Regenerate and check the scripts with `bash sync_behavior_test.sh` and `bash sync_behavior_test.sh --check`.

The test checks that veterinarian records and their specialties are returned from the database, then checks owner lookup and the associated pets. It uses the existing Jakarta REST routes and the Spring/Quarkus routes explicitly; an unexpected route change fails verification. Jakarta has a different set of seeded owners and a JSF interface, so its owner assertion uses its REST detail endpoint. The Spring owner assertion exercises surname search; the Quarkus assertion uses owner detail.

Run `make test` from a target directory, or `make test DOCKER=podman`. Set `BASE_URL` only when running `test.sh` directly against a different host or port.
