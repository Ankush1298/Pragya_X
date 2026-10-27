"""Provision/start this project's private local PostgreSQL cluster without displaying credentials."""
from pathlib import Path
import os
import secrets
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
STORAGE=ROOT/'.local/postgres'
PORT=55433


def main():
    pg_ctl=shutil.which('pg_ctl');initdb=shutil.which('initdb')
    if not pg_ctl or not initdb:
        raise SystemExit('Install PostgreSQL 17 and place pg_ctl/initdb on PATH, then retry.')
    STORAGE.mkdir(parents=True,mode=0o700,exist_ok=True)
    password=STORAGE/'password'
    if not password.exists():
        password.write_text(secrets.token_urlsafe(32));password.chmod(0o600)
    data=STORAGE/'data'
    if not (data/'PG_VERSION').exists():
        subprocess.run([initdb,'-D',str(data),'-U','pragyax_local','--auth=scram-sha-256','--pwfile',str(password)],check=True,stdout=subprocess.DEVNULL)
    if subprocess.run([pg_ctl,'-D',str(data),'status'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        subprocess.run([pg_ctl,'-D',str(data),'-l',str(STORAGE/'server.log'),'-o',f'-p {PORT} -h 127.0.0.1','start'],check=True,stdout=subprocess.DEVNULL)
    import psycopg
    from psycopg import sql
    url=f'postgresql://pragyax_local:{password.read_text().strip()}@127.0.0.1:{PORT}/postgres?sslmode=disable'
    with psycopg.connect(url,autocommit=True) as conn:
        for db in ('pragyax_dev','pragyax_test'):
            if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s',(db,)).fetchone():
                conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(db)))
    for name,db in [('dev.env','pragyax_dev'),('test.env','pragyax_test')]:
        path=STORAGE/name
        path.write_text('DATABASE_URL='+url.replace('/postgres?',f'/{db}?')+'\n');path.chmod(0o600)
    config=ROOT/'.env'
    if not config.exists():
        config.write_text((STORAGE/'dev.env').read_text()+'AI_PROVIDER=mock\nPUBLIC_BASE_URL=http://127.0.0.1:5174\nCORS_ORIGINS=http://127.0.0.1:5174\n');config.chmod(0o600)
    print(f'Private local PostgreSQL ready on 127.0.0.1:{PORT}. Development and test databases are separate.')


if __name__=='__main__':main()
