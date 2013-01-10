from __future__ import unicode_literals
import webnotes


@webnotes.whitelist()
def get_children():
	ctype = webnotes.form_dict.get('ctype')
	webnotes.form_dict['parent_field'] = 'parent_' + ctype.lower().replace(' ', '_')
	if not webnotes.form_dict.get('parent'):
		webnotes.form_dict['parent'] = ''
		
	return webnotes.conn.sql("""select name as value, 
		if(is_group='Yes', 1, 0) as expandable
		from `tab%(ctype)s`
		where docstatus < 2
		and ifnull(%(parent_field)s,'') = "%(parent)s"
		order by name""" % webnotes.form_dict, as_dict=1)
		
@webnotes.whitelist()
def add_node():
	from webnotes.model.doc import Document
	ctype = webnotes.form_dict.get('ctype')
	parent_field = 'parent_' + ctype.lower().replace(' ', '_')

	d = Document(ctype)
	d.fields[ctype.lower().replace(' ', '_') + '_name'] = webnotes.form_dict['name_field']
	d.fields[parent_field] = webnotes.form_dict['parent']
	d.is_group = webnotes.form_dict['is_group']
	d.save()