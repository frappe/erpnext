import frappe
from frappe.query_builder.terms import ParameterizedValueWrapper
from pypika.analytics import Min


class SerialBatchNumberLookup:
	"""Match inputs and group aliases using the physical column's database collation."""

	def __init__(self, identity, item_code, numbers):
		self.identity = identity
		self.item_code = item_code
		self.numbers = list(dict.fromkeys(numbers))
		self.ids = {}
		self.aliases = {}
		self.load()

	@property
	def missing(self):
		return [
			number for number in self.numbers if number not in self.ids and self.aliases[number] == number
		]

	def load(self):
		table = frappe.qb.DocType(self.identity.doctype)
		inputs = self.get_inputs(table)
		key = self.identity.number_key
		rows = (
			frappe.qb.from_(inputs)
			.left_join(table)
			.on(
				(table[self.identity.item_field] == self.item_code)
				& (key(table[self.identity.number_field]) == key(inputs.number))
			)
			.select(inputs.ordinal, table.name, Min(inputs.ordinal).over(key(inputs.number)))
		).run()
		for index, name, first_index in rows:
			number = self.numbers[index]
			self.aliases[number] = self.numbers[first_index]
			if name:
				self.ids[number] = name

	def get_inputs(self, table):
		# An empty column select preserves MariaDB's physical-number collation in the union.
		inputs = (
			frappe.qb.from_(table)
			.select(
				table[self.identity.number_field].as_("number"), ParameterizedValueWrapper(-1).as_("ordinal")
			)
			.where(table.name.isnull())
		)
		for index, number in enumerate(self.numbers):
			inputs = inputs.union_all(
				frappe.qb.select(
					ParameterizedValueWrapper(number).as_("number"),
					ParameterizedValueWrapper(index).as_("ordinal"),
				)
			)
		return inputs.as_("numbers")

	def assign(self, names):
		self.ids.update({number: names[alias] for number, alias in self.aliases.items() if alias in names})
