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
        "src/cms_pipeline/manipulator.py:lib",
        "src/cms_pipeline/loader.py:lib",
    ],
    wheel=True,
    provides=setup_py(
        name="src.cms_pipeline.manipulator",
        version="0.0.1",
        description="manipulates and profiles various sorts of spark",
    ),
    entry_points={
        "console_scripts": {
            "run_manipulator": "src.cms_pipeline.manipulator:main",
            "run_scratchpad": "src.cms_pipeline.loader:main",
        }
    },
)
