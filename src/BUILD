python_requirements(
    name="reqs",
    source="requirements.txt",
    resolve="python-default",
    module_mapping={"databricks-connect": ["databricks", "pyspark"]},
)

python_sources(
    name="lib",
)

python_sources(
    name="lib_test",
    resolve="py-reqs-dev",
)

python_distribution(
    name="dist",
    dependencies=[
        "src/harness/manipulator/manipulator.py:lib",
        "src/harness/manipulator/loader.py:lib",
    ],
    wheel=True,
    provides=setup_py(
        name="src.harness.manipulator.manipulator",
        version="0.0.1",
        description="manipulates and profiles various sorts of spark",
    ),
    entry_points={
        "console_scripts": {
            "run_manipulator": "src.harness.manipulator.manipulator:main",
            "run_scratchpad": "src.harness.manipulator.loader:main",
        }
    },
)
