from __future__ import unicode_literals

def get_context(context):
	context.no_cache = True
	context.parents = [dict(label='View All ',
		route='grant-application', title='View All')]


