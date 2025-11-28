import sqlite3
con = sqlite3.connect('db.sqlite3')
cur = con.cursor()
print('PRAGMA table_info(ideas_idea):')
for row in cur.execute("PRAGMA table_info('ideas_idea')"):
    print(row)
print('\nSample row count:')
print(cur.execute('SELECT COUNT(*) FROM ideas_idea').fetchone())
con.close()