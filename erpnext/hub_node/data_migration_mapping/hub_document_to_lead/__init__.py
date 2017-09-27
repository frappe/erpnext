import json

def pre_process(doc):
	return json.loads(doc.data)