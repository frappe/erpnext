# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re
from collections import Counter, defaultdict

import frappe
from frappe import _

PRODUCT_ENTITY = re.compile(
	r"#(\d+)\s*=\s*(PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE|PRODUCT_DEFINITION_FORMATION"
	r"|PRODUCT_DEFINITION|NEXT_ASSEMBLY_USAGE_OCCURRENCE|PRODUCT)\s*\("
)
REFERENCE = re.compile(r"#(\d+)")
TOKEN = re.compile(r"[^,()]+")
UNICODE_ESCAPE = re.compile(r"\\X2\\((?:[0-9A-F]{4})+)\\X0\\")
LATIN_ESCAPE = re.compile(r"\\X\\([0-9A-F]{2})")


def read_step_file(content: str) -> dict:
	try:
		roots = StepProductStructure(content).get_tree()
	except (IndexError, KeyError, ValueError):
		frappe.throw(_("The STEP file is incomplete or damaged."), title=_("Invalid Design File"))

	if len(roots) == 1:
		root = roots[0]
		return {
			"design_name": root["part_name"],
			"part_number": root["part_number"],
			"parts": root["children"],
		}

	return {"design_name": None, "part_number": None, "parts": roots}


class StepArguments:
	def __init__(self, content: str, position: int):
		self.content = content
		self.position = position

	def read_list(self) -> list:
		values = []
		while True:
			self.skip_spaces()
			character = self.content[self.position]
			if character == ")":
				self.position += 1
				return values

			if character == ",":
				self.position += 1
				continue

			values.append(self.read_value())

	def read_value(self):
		character = self.content[self.position]
		if character == "'":
			return self.read_string()

		if character == "(":
			self.position += 1
			return self.read_list()

		if character == "#":
			return self.read_reference()

		return self.read_token()

	def read_string(self) -> str:
		start = self.position + 1
		end = start
		while True:
			end = self.content.index("'", end)
			if self.content[end + 1 : end + 2] != "'":
				break
			end += 2

		self.position = end + 1
		return decode_step_string(self.content[start:end].replace("''", "'"))

	def read_reference(self) -> int:
		match = REFERENCE.match(self.content, self.position)
		self.position = match.end()
		return int(match.group(1))

	def read_token(self):
		match = TOKEN.match(self.content, self.position)
		self.position = match.end()
		token = match.group(0).strip()
		if self.content[self.position] == "(":
			self.position += 1
			return self.read_list()

		return None if token in ("$", "*") else token

	def skip_spaces(self):
		while self.content[self.position].isspace():
			self.position += 1


def decode_step_string(value: str) -> str:
	value = UNICODE_ESCAPE.sub(lambda match: bytes.fromhex(match.group(1)).decode("utf-16-be"), value)
	value = LATIN_ESCAPE.sub(lambda match: bytes.fromhex(match.group(1)).decode("latin-1"), value)
	return value.replace("\\\\", "\\")


class StepProductStructure:
	def __init__(self, content: str):
		self.entities = {}
		for match in PRODUCT_ENTITY.finditer(content):
			arguments = StepArguments(content, match.end()).read_list()
			self.entities[int(match.group(1))] = (match.group(2), arguments)

		self.children = defaultdict(Counter)
		self.used_definitions = set()
		for entity_type, arguments in self.entities.values():
			if entity_type == "NEXT_ASSEMBLY_USAGE_OCCURRENCE":
				self.children[arguments[3]][arguments[4]] += 1
				self.used_definitions.add(arguments[4])

	@property
	def root_definitions(self) -> list[int]:
		definitions = [
			entity_id
			for entity_id, (entity_type, _arguments) in self.entities.items()
			if entity_type == "PRODUCT_DEFINITION"
		]
		if not self.children:
			return definitions

		return [
			definition
			for definition in definitions
			if definition in self.children and definition not in self.used_definitions
		]

	def get_tree(self) -> list[dict]:
		roots = self.root_definitions
		if not roots:
			frappe.throw(_("The STEP file has no product structure."), title=_("Invalid Design File"))

		return [self.get_node(definition, 1, set()) for definition in roots]

	def get_node(self, definition: int, quantity: int, ancestors: set) -> dict:
		if definition in ancestors:
			frappe.throw(
				_("The STEP file has an assembly that contains itself."), title=_("Invalid Design File")
			)

		node = self.get_product(definition)
		node["quantity"] = quantity
		node["children"] = [
			self.get_node(child, child_quantity, ancestors | {definition})
			for child, child_quantity in self.children[definition].items()
		]
		return node

	def get_product(self, definition: int) -> dict:
		formation = self.get_arguments(definition, "PRODUCT_DEFINITION")[2]
		product = self.get_arguments(
			formation, "PRODUCT_DEFINITION_FORMATION", "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE"
		)[2]
		part_number, part_name, description = self.get_arguments(product, "PRODUCT")[:3]
		return {
			"part_number": part_number or part_name,
			"part_name": part_name or part_number,
			"description": description,
		}

	def get_arguments(self, entity_id: int, *entity_types: str) -> list:
		entity = self.entities.get(entity_id)
		if not entity or entity[0] not in entity_types:
			frappe.throw(
				_("The STEP file refers to a missing {0} #{1}.").format(entity_types[0], entity_id),
				title=_("Invalid Design File"),
			)

		return entity[1]
