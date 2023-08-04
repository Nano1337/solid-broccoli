#!/bin/bash

# Generate a random seed from the current nanoseconds
SEED=883042574

# Run the Python script with the --seed flag set to the random number
python run_prune.py -c cfgs/deit_prune_rnt100.yaml --seed $SEED
