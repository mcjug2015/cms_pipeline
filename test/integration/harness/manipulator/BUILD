python_tests(
    name="tests",
    dependencies=["src:lib_test", ":loader_res"],
    resolve="py-reqs-dev",
    batch_compatibility_tag="shared_spark",
)

resources(
    name="loader_res",
    sources=["res/nested_total_enroll.zip"],
)
