def execute():
	import webnotes
	from webnotes.model.doclist import DocList
	DocList("Website Settings", "Website Settings").save()