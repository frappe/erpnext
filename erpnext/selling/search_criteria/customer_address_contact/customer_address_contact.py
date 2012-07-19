from __future__ import unicode_literals
col_defs = [
	{'label': 'Id', 'type': 'Link', 'width': '', 'options': 'Customer'},
	{'label': 'Customer Name'},
	{'label': 'Address Line 1', 'width': '200px'},
	{'label': 'Address Line 2', 'width': '200px'},
	{'label': 'City'},
	{'label': 'State'},
	{'label': 'Pincode', 'width': '80px'},
	{'label': 'Country', 'width': '100px'},
	{'label': 'Contact First Name'},
	{'label': 'Contact Last Name'},
	{'label': 'Contact Phone', 'width': '100px'},
	{'label': 'Contact Mobile', 'width': '100px'},
	{'label': 'Contact Email'},
]
webnotes.msgprint(colnames)
for col in col_defs:
	colnames.append(col['label'])
	coltypes.append(col.get('type') or 'Data')
	colwidths.append(col.get('width') or '150px')
	coloptions.append(col.get('options') or '')
	col_idx[col['label']] = len(colnames) - 1