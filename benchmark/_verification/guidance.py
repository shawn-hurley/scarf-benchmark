"""Describe the benchmark-owned verification contract to migrating agents."""


def migration_guidance(target, policy):
    if target != 'quarkus':
        return 'The benchmark will validate with its target-framework Dockerfile and test script. '
    behavior = {
        'target': 'run the target-framework test script',
        'source': 'run the unchanged source-framework behavior test',
        'either': 'accept a complete pass of either the unchanged source-framework or target-framework behavior test',
    }[policy]
    return ('The benchmark will build the root Maven project and launch its packaged '
            f'Quarkus JVM application, then {behavior}. '
            'Modules may be added, renamed, or removed; retain a root pom.xml and '
            'produce one runnable Quarkus application. ')
