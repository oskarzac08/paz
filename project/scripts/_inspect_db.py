import sqlite3
p='db.sqlite3'
con=sqlite3.connect(p)
c=con.cursor()
# show columns of auth_user
c.execute("PRAGMA table_info(auth_user);")
cols=c.fetchall()
print('columns in auth_user:')
for col in cols:
    print(col)
# show first 5 users password hashes (id, username, password length, prefix)
c.execute("SELECT id, username, password FROM auth_user LIMIT 5;")
rows=c.fetchall()
print('\nsample password hash info:')
for r in rows:
    id, username, pw = r
    print(id, username, 'hash_len=', len(pw), 'prefix=', pw[:20])
con.close()
