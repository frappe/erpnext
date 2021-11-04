def pre_process(milestone):
	return {
		'title': milestone.title,
		'description': milestone.description,
		'state': milestone.state.title()
	}
