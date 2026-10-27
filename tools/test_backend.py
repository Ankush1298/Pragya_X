"""Run all backend/provider tests on an explicitly isolated local PostgreSQL database."""
from pathlib import Path
import os
import subprocess
import sys

if __name__ == '__main__':
    root=Path(__file__).resolve().parents[1]
    env=os.environ.copy()
    if not env.get('TEST_DATABASE_URL'):
        config=root/'.local/postgres/test.env'
        if not config.exists():raise SystemExit('Run tools/local_postgres.py or set TEST_DATABASE_URL first.')
        env['TEST_DATABASE_URL']=config.read_text().strip().split('=',1)[1]
    (root/'docs/evidence').mkdir(parents=True,exist_ok=True)
    raise SystemExit(subprocess.call([sys.executable,'-m','pytest','backend/tests','ai/tests','-q','-ra',
                                      '--junitxml=docs/evidence/backend-tests.xml',*sys.argv[1:]],cwd=root,env=env))

