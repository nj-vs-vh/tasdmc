# from fabric import Connection

# with Connection("astrocomp") as c:
#     print(hash(c))
#     result = c.run('uname -s', pty=True)


# from io import StringIO
# from tempfile import NamedTemporaryFile
# from time import sleep

# contents = StringIO("123456")

# with NamedTemporaryFile(mode='w') as local_tmp:
#     local_tmp.write(contents.read())
#     local_tmp.flush()
#     print(local_tmp.name)
#     sleep(15)
