from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.bean import Bean
	Bean("Website Settings", "Website Settings").save()