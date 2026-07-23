python_sources(
    name="lib",
    dependencies=[":migrations", ":dml_migrations"],
)

python_sources(
    name="lib_test",
    dependencies=[":migrations", ":dml_migrations"],
    resolve="py-reqs-dev",
)

resources(
    name="migrations",
    sources=["migrations/*.sql"],
)

resources(
    name="dml_migrations",
    sources=["dml_migrations/*.sql"],
)
