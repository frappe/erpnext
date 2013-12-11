# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes, os, subprocess, tempfile, json, datetime

@webnotes.whitelist()
def get():
	with open("../app/home/page/latest_updates/latest_updates.json", "r") as lufile:
		return json.loads(lufile.read())

def make():
	def add_to_logs(out, repo):
		out.seek(0)
		last_commit = None
		for l in out.readlines():
			l = l.decode('utf-8')
			if last_commit is not None:
				if l.startswith("Date:"):
					last_commit["date"] = l[8:-1]
					last_commit["datetime"] = datetime.datetime.strptime(last_commit["date"][:-6], "%a %b %d %H:%M:%S %Y")
				if l.startswith("Author:"):
					last_commit["author"] = l[8:-1]
				if l.startswith("    "):
					last_commit["message"] = l[4:-1]

			if l.startswith("commit"):
				last_commit = {
					"repo": repo,
					"commit": l.split(" ")[1][:-1]
				}
				logs.append(last_commit)

	os.chdir("lib")
	logs = []
	out_lib = tempfile.TemporaryFile()
	subprocess.call("git --no-pager log -n 200 --no-color", shell=True, stdout=out_lib)
	add_to_logs(out_lib, "lib")

	os.chdir("../app")
	out_app = tempfile.TemporaryFile()
	subprocess.call("git --no-pager log -n 200 --no-color", shell=True, stdout=out_app)
	add_to_logs(out_app, "app")
	
	logs.sort(key=lambda a: a["datetime"], reverse=True)
	for a in logs:
		del a["datetime"]
		
	for i in xrange(len(logs)):
		if i and logs[i]["message"]==logs[i-1]["message"]:
			logs[i]["delete"] = True
			
		if logs[i]["message"].startswith("Merge branch") or "[" not in logs[i]["message"]:
			logs[i]["delete"] = True
	
	logs = filter(lambda a: a if not a.get("delete") else None, logs)
	
	os.chdir("..")
	with open("app/home/page/latest_updates/latest_updates.json", "w") as lufile:
		lufile.write(json.dumps(logs, indent=1, sort_keys=True))
	
if __name__=="__main__":
	make()
