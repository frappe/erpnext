# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe import _
from frappe.utils.bot import BotParser


class FindItemBot(BotParser):
	def get_reply(self):
		if self.startswith("where is", "find item", "locate"):
			if not frappe.has_permission("Warehouse"):
				raise frappe.PermissionError

			item = "%{0}%".format(self.strip_words(self.query, "where is", "find item", "locate"))
			items = frappe.db.sql(
				"""select name from `tabItem` where item_code like %(txt)s
				or item_name like %(txt)s or description like %(txt)s""",
				dict(txt=item),
			)

			if items:
				out = []
				warehouses = frappe.get_all("Warehouse")
				for item in items:
					found = False
					for warehouse in warehouses:
						qty = frappe.db.get_value(
							"Bin", {"item_code": item[0], "warehouse": warehouse.name}, "actual_qty"
						)
						if qty:
							out.append(
								_("{0} units of [{1}](/app/Form/Item/{1}) found in [{2}](/app/Form/Warehouse/{2})").format(
									qty, item[0], warehouse.name
								)
							)
							found = True

					if not found:
						out.append(_("[{0}](/app/Form/Item/{0}) is out of stock").format(item[0]))

				return "\n\n".join(out)

			else:
				return _("Did not find any item called {0}").format(item)
