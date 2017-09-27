import json

def pre_process(doc):
	return json.loads(doc['data'])

def post_process(remote_doc, local_doc):
	pass