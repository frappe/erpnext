import frappe
from frappe import _

from frappe.model.document import Document


# ruleid: frappe-modifying-but-not-comitting
def on_submit(self):
	if self.value_of_goods == 0:
		frappe.throw(_('Value of goods cannot be 0'))
	self.status = 'Submitted'


# ok: frappe-modifying-but-not-comitting
def on_submit(self):
	if self.value_of_goods == 0:
		frappe.throw(_('Value of goods cannot be 0'))
	self.status = 'Submitted'
	self.db_set('status', 'Submitted')

# ok: frappe-modifying-but-not-comitting
def on_submit(self):
	if self.value_of_goods == 0:
		frappe.throw(_('Value of goods cannot be 0'))
	x = "y"
	self.status = x
	self.db_set('status', x)


# ok: frappe-modifying-but-not-comitting
def on_submit(self):
	x = "y"
	self.status = x
	self.save()

# ruleid: frappe-modifying-but-not-comitting-other-method
class DoctypeClass(Document):
	def on_submit(self):
		self.good_method()
		self.tainted_method()

	def tainted_method(self):
		self.status = "uptate"


# ok: frappe-modifying-but-not-comitting-other-method
class DoctypeClass(Document):
	def on_submit(self):
		self.good_method()
		self.tainted_method()

	def tainted_method(self):
		self.status = "update"
		self.db_set("status", "update")

# ok: frappe-modifying-but-not-comitting-other-method
class DoctypeClass(Document):
	def on_submit(self):
		self.good_method()
		self.tainted_method()
		self.save()

	def tainted_method(self):
		self.status = "uptate"
