from __future__ import unicode_literals

def pre_process(milestone):
	return {
		'title': milestone.title,
		'description': milestone.description,
		'state': milestone.state.title()
	}
