#!/bin/bash
set -o errexit
set -o pipefail

echo "begin directory is: $(pwd)"
pants generate-lockfiles
pants package src/
cd dab/
echo "begin dab directory is: $(pwd)"
databricks bundle validate
databricks bundle deploy
databricks bundle run manipulator_job