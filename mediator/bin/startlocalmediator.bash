#!/bin/bash

# start federator
python -m federator.server --port=5000 --routing='gfz' --tmpdir='/tmp'

# start mediator
python -m mediator.server --port=5001 --tmpdir='/tmp'
