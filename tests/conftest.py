"""同步模块测试：在导入应用前切换到临时数据目录，不污染真实笔记。"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DATA = Path(tempfile.mkdtemp(prefix="rusin-note-local-test-"))

os.chdir(ROOT)
os.environ["RUSIN_DATA_DIR"] = str(TEST_DATA)
sys.path.insert(0, str(ROOT))


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TEST_DATA, ignore_errors=True)
