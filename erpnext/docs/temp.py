from __future__ import unicode_literals

import os

for basepath, folders, files in os.walk("user"):
	if "index.txt" in files:
		with open(os.path.join(basepath, "index.txt"), "r") as i:
			in_index = i.read().splitlines()

		missing = []

		for f in files:
			name = f.rsplit(".", 1)[0]
			if name not in in_index and name != "index":
				missing.append(f)

		if missing:
			print missing
			with open(os.path.join(basepath, "index.txt"), "w") as i:
				i.write("\n".join(in_index + missing))

