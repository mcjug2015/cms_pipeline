python_sources(
    name="lib",
    dependencies=[":migrations"],
)

python_sources(
    name="lib_test",
    dependencies=[":migrations"],
    resolve="py-reqs-dev",
)

resources(
    name="migrations",
    sources=["migrations/*.sql"],
)
