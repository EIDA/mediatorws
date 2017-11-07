#!/bin/bash

# start federator
python -m federator.server --port=5000 --routing='gfz' --tmpdir='/tmp'
