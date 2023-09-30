#!/bin/bash
poetry install --only lambda --sync
poetry lock
poetry export -f requirements.txt --output lambda_requirements.txt --only lambda
pip install -r lambda_requirements.txt -t lambda_out --upgrade