# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _, msgprint

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.validate_to_value_of_shipping_rule_conditions()
		self.validate_overlapping_shipping_rule_conditions()
		
		
	def validate_to_value_of_shipping_rule_conditions(self):
		"""check if more than two or more rows has To Value = 0"""
		shipping_rule_conditions_with_0_to_value = self.doclist.get({
			"parentfield": "shipping_rule_conditions", "to_value": ["in", [0, None]]})
		if len(shipping_rule_conditions_with_0_to_value) >= 2:
			msgprint(_('''There can only be one shipping rule with 0 or blank value for "To Value"'''),
				raise_exception=True)
				
	def validate_overlapping_shipping_rule_conditions(self):
		pass