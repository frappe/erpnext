# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	# udpate sales cycle
	webnotes.conn.sql("""update `tabSales Invoice` set taxes_and_charges=charge""")
	webnotes.conn.sql("""update `tabSales Order` set taxes_and_charges=charge""")
	webnotes.conn.sql("""update `tabQuotation` set taxes_and_charges=charge""")
	webnotes.conn.sql("""update `tabDelivery Note` set taxes_and_charges=charge""")

	# udpate purchase cycle
	webnotes.conn.sql("""update `tabPurchase Invoice` set taxes_and_charges=purchase_other_charges""")
	webnotes.conn.sql("""update `tabPurchase Order` set taxes_and_charges=purchase_other_charges""")
	webnotes.conn.sql("""update `tabSupplier Quotation` set taxes_and_charges=purchase_other_charges""")
	webnotes.conn.sql("""update `tabPurchase Receipt` set taxes_and_charges=purchase_other_charges""")

	webnotes.conn.sql("""update `tabPurchase Taxes and Charges` set parentfield='other_charges'""")