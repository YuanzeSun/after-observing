"""Shared paths for a normal clone, CI and optional local SDK overrides."""
import os,re
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
WORK=Path(os.environ.get('AO_WORK',PROJECT/'.build')).resolve()
SDK=Path(os.environ.get('RENPY_SDK',WORK/'sdk/renpy-8.6.0-sdkarm')).resolve()
DIST=Path(os.environ.get('AO_DIST',PROJECT/'dist')).resolve()

VERSION=re.search(r'define config.version = "([^"]+)"',(PROJECT/"game/core.rpy").read_text())[1]
PACKAGE="AfterObserving-"+VERSION
