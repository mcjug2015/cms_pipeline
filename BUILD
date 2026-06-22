python_requirements(name="reqs", source="requirements.txt", resolve="python-default", module_mapping={"databricks-connect": ["databricks", "pyspark"]})
python_requirements(
    name="reqs-dev", source="requirements-dev.txt", resolve="py-reqs-dev"
)
python_sources(
    name="lib",
)
python_sources(
    name="lib_test",
    resolve="py-reqs-dev",
)
