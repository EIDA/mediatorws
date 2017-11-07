#!/bin/bash

# start federator
python -m eidangservices.federator.server --port=5000 --routing='gfz' --tmpdir='/tmp'
