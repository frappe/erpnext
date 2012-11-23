from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.wrapper import ModelWrapper
	ModelWrapper("Website Settings", "Website Settings").save()