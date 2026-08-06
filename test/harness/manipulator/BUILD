python_tests(
    name="tests",
    dependencies=["src:lib_test", ":unwrapper_res", ":loader_res"],
    resolve="py-reqs-dev",
    batch_compatibility_tag="shared_spark",
)

resources(
    name="unwrapper_res",
    sources=["res/nested.zip", "res/no_target.zip"],
)

resources(
    name="loader_res",
    sources=["res/parse_sheet_sample.xlsx", "res/parse_sheet_no_rows_sample.xlsx"],
)
