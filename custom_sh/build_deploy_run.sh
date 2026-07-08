#!/bin/bash
set -o errexit
set -o pipefail

cd dab/
echo "Current directory is: $(pwd)"

pants generate-lockfiles
pants package src/
databricks bundle validate
databricks bundle deploy
databricks bundle run manipulator_job