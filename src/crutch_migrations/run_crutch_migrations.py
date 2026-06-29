"""
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYTHONPATH"] = ":".join(sys.path)
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-21-openjdk-amd64/"
os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
"""

import argparse
import datetime
import os
import shutil

from jinja2 import Environment, PackageLoader, select_autoescape

from src import custom_logging
from src.spark_utils import get_spark, is_dbr

logger = custom_logging.setup_logging().getLogger(__name__)


def apply_template(output_dir, template, cat: str, schema: str):
    result_sql = template.render(cat=cat, schema=schema)
    with open(
        os.path.join(output_dir, template.name.replace(".sql", "_primed.sql")), "w"
    ) as file_handle:
        file_handle.write(result_sql)
    return result_sql


def get_ascending_letters_within_minute():
    micros_since_minute = datetime.datetime.now() - datetime.datetime.now().replace(
        second=0, microsecond=0
    )
    result = str(micros_since_minute.microseconds).translate(
        str.maketrans("0123456789", "ABCDEFGHIJ")
    )
    return result


def get_output_folder(output_parent_path):
    folder_name = f"{datetime.datetime.today().strftime('%Y%m%d_%H%M')}_{get_ascending_letters_within_minute()}"
    return os.path.join(output_parent_path, folder_name)


def use_migration_file(fname):
    if fname.endswith("all.sql"):
        return True
    elif is_dbr() and fname.endswith("dbr_only.sql"):
        return True
    return False


def migrate(spark, output_folder, cat: str, schema: str):
    env = Environment(
        loader=PackageLoader(
            package_name="src.crutch_migrations", package_path="migrations"
        ),
        autoescape=select_autoescape(),
    )
    all_templates = env.list_templates(filter_func=use_migration_file)
    logger.info(
        f"found {len(all_templates)} migrations; first five are {all_templates[:5]};"
    )
    for template_name in all_templates:
        result_sql = apply_template(
            output_folder,
            env.get_template(template_name, globals),
            cat=cat,
            schema=schema,
        )
        spark.sql(result_sql)
    logger.info(f"invoked spark on {len(all_templates)} migrations;")


def run_migrations(spark, cat, schema, output_folder=None):
    if not output_folder:
        output_folder = get_output_folder(
            os.path.join(os.path.dirname(__file__), "migrations_out")
        )
    os.makedirs(output_folder)
    migrate(spark, output_folder, cat, schema)


def main(cat, schema):
    shutil.rmtree(
        os.path.join(os.path.dirname(__file__), "..", "..", "spark-warehouse"),
        ignore_errors=True,
    )
    run_migrations(get_spark(), cat, schema)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="manipulator params")
    parser.add_argument(
        "--cat",
        help="catalog name to use",
        default="spark_catalog",
    )
    parser.add_argument(
        "--schema",
        help="schema name to use",
        default="default",
    )
    args = parser.parse_args()
    main(cat=args.cat, schema=args.schema)
