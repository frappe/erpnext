import os, sys

path_to_file = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-1] + ['print_formats'])

def prepare_pf_dict(args_list):
	"""

	"""
	pf_list = []
	for a in args_list:
		for pf_type in ['Classic', 'Modern', 'Spartan']:
			pf = {}
			pf['name'] = " ".join([a['name'], pf_type])
			pf['file'] = os.sep.join([path_to_file, "".join(pf['name'].split(" ")) + ".html"])
			pf['module'] = a['module']
			pf['doc_type'] = a['doc_type']
			pf['standard'] = 'Yes'
			pf_list += [pf]
	return pf_list


pf_to_install = prepare_pf_dict([
	{
		'name' : 'Sales Invoice',
		'doc_type' : 'Receivable Voucher',
		'module' : 'Accounts'
	},
	{
		'name' : 'Sales Order',
		'doc_type' : 'Sales Order',
		'module' : 'Selling'
	},
	{
		'name' : 'Quotation',
		'doc_type' : 'Quotation',
		'module' : 'Selling'
	},
	{
		'name' : 'Delivery Note',
		'doc_type' : 'Delivery Note',
		'module' : 'Stock'
	},
	{
		'name' : 'Purchase Order',
		'doc_type' : 'Purchase Order',
		'module' : 'Buying'
	}
])

def execute():
	"""
		Install print formats
	"""
	global pf_to_install
	print pf_to_install
	for pf in pf_to_install:
		install_print_format(pf)
		print "Installed PF: " + pf['name']


def install_print_format(args):
	"""
		Installs print format
		args is a dict consisting of following keys:
			* name
			* module
			* doctype
			* standard = "Yes"/"No"
			* file
	"""
	from webnotes.model.doc import Document
	d = Document('Print Format')
	d.name = args.name
	f = open(args.file)
	d.html = f.read()
	f.close()
	d.module = args.module
	d.doc_type = args.doc_type
	d.standard = args.standard
	d.save(1)
