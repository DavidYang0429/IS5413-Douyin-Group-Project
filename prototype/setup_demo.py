"""Provision a fresh course database. Never resets or overwrites existing data."""
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='Actual Direct connection host from Supabase Connect')
    parser.add_argument('--database', default='postgres')
    parser.add_argument('--admin-user', default='postgres')
    args = parser.parse_args()
    target = ROOT / '.local/connection.json'
    if target.exists():
        raise SystemExit('Local credentials already exist. No passwords or database objects were changed.')
    password = getpass.getpass('Database administrator password (not saved): ')
    with psycopg.connect(host=args.host, dbname=args.database, user=args.admin_user,
                         password=password, sslmode='verify-full',
                         sslrootcert=str(ROOT / 'supabase-ca.crt'), autocommit=True) as conn:
        if conn.execute("SELECT 1 FROM pg_namespace WHERE nspname='douyin'").fetchone():
            raise SystemExit('The douyin schema already exists. Refusing to reset or overwrite it.')
        users = {str(i): {'user': f'douyin_demo_u{i}', 'password': secrets.token_urlsafe(28)}
                 for i in range(1, 6)}
        if conn.execute("SELECT 1 FROM pg_roles WHERE rolname LIKE 'douyin_demo_u%' LIMIT 1").fetchone():
            raise SystemExit('Demo roles already exist. Refusing to rotate their passwords.')
        for user in users.values():
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS')
                         .format(sql.Identifier(user['user']), sql.Literal(user['password'])))
            conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}')
                         .format(sql.Identifier(args.database), sql.Identifier(user['user'])))
        # Save provisioned credentials before DDL so a partial install is recoverable.
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps({'host': args.host, 'port': 5432, 'dbname': args.database,
                                      'users': users}, indent=2))
        os.chmod(target, 0o600)
        folder = ROOT.parent / 'sql/postgresql'
        for name in ['01_schema.sql', '02_final_snapshot.sql', '04_business_rules.sql',
                     '05_report_interface.sql', '06_guard_record_fix.sql']:
            conn.execute((folder / name).read_text(), prepare=False)
            print('Applied', name)
    print('Ready. Credentials are in .local/connection.json; never include them in a submission.')


if __name__ == '__main__':
    main()
