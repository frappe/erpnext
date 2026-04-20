PARENT_LINES = [
	{"line_code": "MX", "line_name": "Mono-Multi Line", "is_group": True},
	{"line_code": "L2", "line_name": "Calacatta Line", "is_group": True},
]

CHILD_LINES = [
	{"line_code": "1", "line_name": "Mono Line", "parent_line": "MX"},
	{"line_code": "2", "line_name": "Multi Line", "parent_line": "MX"},
	{"line_code": "L2M1", "line_name": "Calacatta Mixer 1", "parent_line": "L2"},
	{"line_code": "L2M2", "line_name": "Calacatta Mixer 2", "parent_line": "L2"},
	{"line_code": "L2M3", "line_name": "Calacatta Mixer 3", "parent_line": "L2"},
]
