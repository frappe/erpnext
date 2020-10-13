import sys
import requests
from urllib.parse import urlparse


docs_repos = [
	"frappe_docs",
	"erpnext_documentation",
	"erpnext_com",
	"frappe_io",
]


def uri_validator(x):
	result = urlparse(x)
	return all([result.scheme, result.netloc, result.path])

def docs_link_exists(body):
	for line in body.splitlines():
		for word in line.split():
			if word.startswith('http') and uri_validator(word):
				parsed_url = urlparse(word)
				if parsed_url.netloc == "github.com":
					_, org, repo, _type, ref = parsed_url.path.split('/')
					if org == "frappe" and repo in docs_repos:
						return True


if __name__ == "__main__":
	pr = sys.argv[1]
	response = requests.get("https://api.github.com/repos/frappe/frappe/pulls/{}".format(pr))

	if response.ok:
		payload = response.json()
		title = payload.get("title", "").lower()
		head_sha = payload.get("head", {}).get("sha")
		body = payload.get("body", "").lower()

		if title.startswith("feat") and head_sha and "no-docs" not in body:
			if docs_link_exists(body):
				print("Documentation Link Found. You're Awesome! 🎉")

			else:
				print("Documentation Link Not Found! ⚠️")
				sys.exit(1)

		else:
			print("Skipping documentation checks... 🏃")
