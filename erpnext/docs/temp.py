import os, re

for basepath, folders, files in os.walk("."):
	for f in files:
		if f.endswith(".html") or f.endswith(".md"):
			with open(os.path.join(basepath, f), "r") as c:
				content = c.read()

			for path in re.findall("""{{.?docs_base_url.?}}([^'"\)]*)""", content):
				print path
