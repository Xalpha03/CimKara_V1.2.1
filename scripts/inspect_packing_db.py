import os
import django
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings')
django.setup()
from django.db import connection
c = connection.cursor()
print('PRAGMA table_info:')
for row in c.execute("PRAGMA table_info('packing_packing')"):
    print(row)
print('\nCOUNT NULL created:')
try:
    c.execute("SELECT COUNT(*) FROM packing_packing WHERE created IS NULL")
    print(c.fetchone())
except Exception as e:
    print('ERROR:', e)
print('\nSAMPLE ROWS:')
try:
    c.execute("SELECT id, title, date, slug, created FROM packing_packing LIMIT 5")
    for r in c.fetchall():
        print(r)
except Exception as e:
    print('ERROR SELECT:', e)
