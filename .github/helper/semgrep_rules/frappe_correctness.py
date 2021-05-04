import frappe
from frappe import _, flt

from frappe.model.document import Document


def on_submit(self):
	if self.value_of_goods == 0:
		frappe.throw(_('Value of goods cannot be 0'))
	# ruleid: frappe-modifying-after-submit
	self.status = 'Submitted'

def on_submit(self):
	if flt(self.per_billed) < 100:
		self.update_billing_status()
	else:
		# todook: frappe-modifying-after-submit
		self.status = "Completed"
		self.db_set("status", "Completed")

class TestDoc(Document):
	pass

	def validate(self):
		#ruleid: frappe-modifying-child-tables-while-iterating
		for item in self.child_table:
			if item.value < 0:
				self.remove(item)
