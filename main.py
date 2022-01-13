import fabric

conn = fabric.Connection('cluster56')

conn.run("cd fabric-test && python run.py one")
