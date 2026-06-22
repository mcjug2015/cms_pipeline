python_sources(
    name="lib",
)
python_sources(
    name="lib_test",
    resolve="py-reqs-dev",
)
python_distribution(
    name="dist",
    dependencies=[":lib"],
    wheel=True,
    provides=setup_py(
        name="src",
        version="0.0.1",
        description="whl for test proj",
    ),
    entry_points={
        "console_scripts": {"manipulator": "src.harness.manipulator.manipulator:main"}
    },
)
