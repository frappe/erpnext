from __future__ import unicode_literals
import webnotes
sql = webnotes.conn.sql
from webnotes.model import delete_doc

def execute():
	del_rec = {
		'DocType'	:	['Update Series', 'File', 'File Browser Control', 'File Group',
			'Tag Detail', 'DocType Property Setter', 'Company Group', 'Widget Control', 
			'Update Delivery Date Detail', 'Update Delivery	Date',
			'Tag Detail', 'Supplier rating', 'Stylesheet', 'Question Tag',
			'PRO PP Detail', 'PRO Detail', 'PPW Detail', 'PF Detail',
			'Personalize', 'Patch Util', 'Page Template', 'Module Def Role',
			'Module Def Item', 'File Group', 'File Browser Control', 'File',
			'Educational Qualifications', 'Earn Deduction Detail',
			'DocType Property Setter', 'Contact Detail', 'BOM Report Detail', 
			'BOM Replace Utility Detail', 'BOM Replace Utility', 
			'Absent Days Detail', 'Activity Dashboard Control', 'Raw Materials Supplied',
			'Setup Wizard Control', 'Company Group', 'Lease Agreement', 'Lease Installment',
			'Terms and Conditions', 'Time Sheet', 'Time Sheet Detail', 'Naming Series Options',
			'Invest 80 Declaration Detail', 'IT Checklist', 'Chapter VI A Detail', 'Declaration Detail',
			'Personalize', 'Salary Slip Control Panel', 'Question Control'
			],
		'Page'		:	['File Browser', 'Bill of Materials', 'question-view'],
		'DocType Mapper': ['Production Forecast-Production Planning Tool', 'Production Forecast-Production Plan', 'Sales Order-Production Plan'],
	}

	for d in del_rec:
		for r in del_rec[d]:
			print 'Deleted', d, ' - ', r
			if d=='DocType':
				sql("delete from tabFeed where doc_type=%s", r)
			delete_doc(d, r)

	sql("delete from tabDocField where label='Repair Purchase Request' and parent = 'Purchase Request'")

	drop_tables()


def drop_tables():
	webnotes.conn.commit()
	from webnotes.model.db_schema import remove_all_foreign_keys
	remove_all_foreign_keys()
	count = 0
	tab_list = sql("SHOW TABLES")
	for tab in tab_list:
		if tab[0].startswith('_') or tab[0] in ('tabSingles', 'tabSessions', 'tabSeries'): continue
		res = sql("SELECT COUNT(*) FROM `tabDocType` WHERE name = %s", tab[0][3:])
		if not res[0][0]:
			count += 1
			print tab[0]
			sql("DROP TABLE `%s`" % tab[0])
	print count
	webnotes.conn.begin()
