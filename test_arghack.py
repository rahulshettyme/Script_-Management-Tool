
import sys
# HACK INJECTED BY CONVERTER
sys.argv = [sys.argv[0]]

import argparse
import builtins

# Mimic user script structure
parser = argparse.ArgumentParser()
parser.add_argument('--foo', default='bar')

try:
    args = parser.parse_args()
    print(f"DEBUG: Parse Args Success! foo={args.foo}")
except SystemExit:
    print("DEBUG: Parse Args FAILED!")
    raise

def run(data, token, env_config):
    print("DEBUG: Inside Run Function!")
    return [{"status": "success", "message": "Hack worked"}]
