#!/usr/bin/env python3
"""Weekly refresh entrypoint: fresh catalog, exact area prices, validated publish data."""
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
def main():
    result=subprocess.run([sys.executable,str(HERE/'collect_catalog.py')],check=False)
    if result.returncode:
        print('Catalog refresh failed; published type snapshot preserved.',file=sys.stderr)
        return result.returncode
    return subprocess.call([sys.executable,str(HERE/'collect_types.py'),'--publish-data',*sys.argv[1:]])
if __name__=='__main__':
    raise SystemExit(main())
