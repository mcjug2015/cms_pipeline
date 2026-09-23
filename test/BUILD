python_requirements(name="reqs-dev", source="requirements-dev.txt", resolve="py-reqs-dev")

python_sources(
    name="lib_test",
    resolve="py-reqs-dev",
)

python_tests(
    name="tests",
    dependencies=["src:lib_test"],
    resolve="py-reqs-dev",
    batch_compatibility_tag="shared_spark",
)

python_test_utils(
    name="test_utils",
    # conftest.py points spark_sql_migrations at these by path, not by import.
    dependencies=["src/crutch_migrations:all_spark_migrations"],
    resolve="py-reqs-dev",
)
