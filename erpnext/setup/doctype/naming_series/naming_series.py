# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint, throw
from frappe.core.doctype.doctype.doctype import validate_series
from frappe.model.document import Document
from frappe.model.naming import make_autoname, parse_naming_series
from frappe.permissions import get_doctypes_with_read
from frappe.utils import cint, cstr


class NamingSeriesNotSetError(frappe.ValidationError):
	pass


class NamingSeries(Document):
	@frappe.whitelist()
	def get_transactions(self, arg=None):
		doctypes = list(
			set(
				frappe.db.sql_list(
					"""select parent
				from `tabDocField` df where fieldname='naming_series'"""
				)
				+ frappe.db.sql_list(
					"""select dt from `tabCustom Field`
				where fieldname='naming_series'"""
				)
			)
		)

		doctypes = list(set(get_doctypes_with_read()).intersection(set(doctypes)))
		prefixes = ""
		for d in doctypes:
			options = ""
			try:
				options = self.get_options(d)
			except frappe.DoesNotExistError:
				frappe.msgprint(_("Unable to find DocType {0}").format(d))
				# frappe.pass_does_not_exist_error()
				continue

			if options:
				prefixes = prefixes + "\n" + options
		prefixes.replace("\n\n", "\n")
		prefixes = prefixes.split("\n")

		custom_prefixes = frappe.get_all(
			"DocType",
			fields=["autoname"],
			filters={
				"name": ("not in", doctypes),
				"autoname": ("like", "%.#%"),
				"module": ("not in", ["Core"]),
			},
		)
		if custom_prefixes:
			prefixes = prefixes + [d.autoname.rsplit(".", 1)[0] for d in custom_prefixes]

		prefixes = "\n".join(sorted(prefixes))

		return {"transactions": "\n".join([""] + sorted(doctypes)), "prefixes": prefixes}

	def scrub_options_list(self, ol):
		options = list(filter(lambda x: x, [cstr(n).strip() for n in ol]))
		return options

	@frappe.whitelist()
	def update_series(self, arg=None):
		"""update series list"""
		self.validate_series_set()
		self.check_duplicate()
		series_list = self.set_options.split("\n")

		# set in doctype
		self.set_series_for(self.select_doc_for_series, series_list)

		# create series
		map(self.insert_series, [d.split(".")[0] for d in series_list if d.strip()])

		msgprint(_("Series Updated"))

		return self.get_transactions()

	def validate_series_set(self):
		if self.select_doc_for_series and not self.set_options:
			frappe.throw(_("Please set the series to be used."))

	def set_series_for(self, doctype, ol):
		options = self.scrub_options_list(ol)

		# validate names
		for i in options:
			self.validate_series_name(i)

		if options and self.user_must_always_select:
			options = [""] + options

		default = options[0] if options else ""

		# update in property setter
		prop_dict = {"options": "\n".join(options), "default": default}

		for prop in prop_dict:
			ps_exists = frappe.db.get_value(
				"Property Setter", {"field_name": "naming_series", "doc_type": doctype, "property": prop}
			)

			if ps_exists:
				ps = frappe.get_doc("Property Setter", ps_exists)
				ps.value = prop_dict[prop]
				ps.save()
			else:
				ps = frappe.get_doc(
					{
						"doctype": "Property Setter",
						"doctype_or_field": "DocField",
						"doc_type": doctype,
						"field_name": "naming_series",
						"property": prop,
						"value": prop_dict[prop],
						"property_type": "Text",
						"__islocal": 1,
					}
				)
				ps.save()

		self.set_options = "\n".join(options)

		frappe.clear_cache(doctype=doctype)

	def check_duplicate(self):
		parent = list(
			set(
				frappe.db.sql_list(
					"""select dt.name
				from `tabDocField` df, `tabDocType` dt
				where dt.name = df.parent and df.fieldname='naming_series' and dt.name != %s""",
					self.select_doc_for_series,
				)
				+ frappe.db.sql_list(
					"""select dt.name
				from `tabCustom Field` df, `tabDocType` dt
				where dt.name = df.dt and df.fieldname='naming_series' and dt.name != %s""",
					self.select_doc_for_series,
				)
			)
		)
		sr = [[frappe.get_meta(p).get_field("naming_series").options, p] for p in parent]
		dt = frappe.get_doc("DocType", self.select_doc_for_series)
		options = self.scrub_options_list(self.set_options.split("\n"))
		for series in options:
			validate_series(dt, series)
			for i in sr:
				if i[0]:
					existing_series = [d.split(".")[0] for d in i[0].split("\n")]
					if series.split(".")[0] in existing_series:
						frappe.throw(_("Series {0} already used in {1}").format(series, i[1]))

	def validate_series_name(self, n):
		import re

		if not re.match(r"^[\w\- \/.#{}]+$", n, re.UNICODE):
			throw(
				_('Special Characters except "-", "#", ".", "/", "{" and "}" not allowed in naming series')
			)

	@frappe.whitelist()
	def get_options(self, arg=None):
		if frappe.get_meta(arg or self.select_doc_for_series).get_field("naming_series"):
			return frappe.get_meta(arg or self.select_doc_for_series).get_field("naming_series").options

	@frappe.whitelist()
	def get_current(self, arg=None):
		"""get series current"""
		if self.prefix:
			prefix = self.parse_naming_series()
			self.current_value = frappe.db.get_value("Series", prefix, "current", order_by="name")

	def insert_series(self, series):
		"""insert series if missing"""
		if frappe.db.get_value("Series", series, "name", order_by="name") == None:
			frappe.db.sql("insert into tabSeries (name, current) values (%s, 0)", (series))

	@frappe.whitelist()
	def update_series_start(self):
		if self.prefix:
			prefix = self.parse_naming_series()
			self.insert_series(prefix)
			frappe.db.sql(
				"update `tabSeries` set current = %s where name = %s", (cint(self.current_value), prefix)
			)
			msgprint(_("Series Updated Successfully"))
		else:
			msgprint(_("Please select prefix first"))

	def parse_naming_series(self):
		parts = self.prefix.split(".")

		# Remove ### from the end of series
		if parts[-1] == "#" * len(parts[-1]):
			del parts[-1]

		prefix = parse_naming_series(parts)
		return prefix

	@frappe.whitelist()
	def preview_series(self) -> str:
		"""Preview what the naming series will generate."""

		generated_names = []
		series = self.naming_series_to_check
		if not series:
			return ""

		try:
			doc = self._fetch_last_doc_if_available()
			for _count in range(3):
				generated_names.append(make_autoname(series, doc=doc))
		except Exception as e:
			if frappe.message_log:
				frappe.message_log.pop()
			return _("Failed to generate names from the series") + f"\n{str(e)}"

		# Explcitly rollback in case any changes were made to series table.
		frappe.db.rollback()  # nosemgrep
		return "\n".join(generated_names)

	def _fetch_last_doc_if_available(self):
		"""Fetch last doc for evaluating naming series with fields."""
		try:
			return frappe.get_last_doc(self.select_doc_for_series)
		except Exception:
			return None


def set_by_naming_series(
	doctype, fieldname, naming_series, hide_name_field=True, make_mandatory=1
):
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	if naming_series:
		make_property_setter(
			doctype, "naming_series", "hidden", 0, "Check", validate_fields_for_doctype=False
		)
		make_property_setter(
			doctype, "naming_series", "reqd", make_mandatory, "Check", validate_fields_for_doctype=False
		)

		# set values for mandatory
		try:
			frappe.db.sql(
				"""update `tab{doctype}` set naming_series={s} where
				ifnull(naming_series, '')=''""".format(
					doctype=doctype, s="%s"
				),
				get_default_naming_series(doctype),
			)
		except NamingSeriesNotSetError:
			pass

		if hide_name_field:
			make_property_setter(doctype, fieldname, "reqd", 0, "Check", validate_fields_for_doctype=False)
			make_property_setter(
				doctype, fieldname, "hidden", 1, "Check", validate_fields_for_doctype=False
			)
	else:
		make_property_setter(
			doctype, "naming_series", "reqd", 0, "Check", validate_fields_for_doctype=False
		)
		make_property_setter(
			doctype, "naming_series", "hidden", 1, "Check", validate_fields_for_doctype=False
		)

		if hide_name_field:
			make_property_setter(
				doctype, fieldname, "hidden", 0, "Check", validate_fields_for_doctype=False
			)
			make_property_setter(doctype, fieldname, "reqd", 1, "Check", validate_fields_for_doctype=False)

			# set values for mandatory
			frappe.db.sql(
				"""update `tab{doctype}` set `{fieldname}`=`name` where
				ifnull({fieldname}, '')=''""".format(
					doctype=doctype, fieldname=fieldname
				)
			)


def get_default_naming_series(doctype):
	naming_series = frappe.get_meta(doctype).get_field("naming_series").options or ""
	naming_series = naming_series.split("\n")
	out = naming_series[0] or (naming_series[1] if len(naming_series) > 1 else None)

	if not out:
		frappe.throw(
			_("Please set Naming Series for {0} via Setup > Settings > Naming Series").format(doctype),
			NamingSeriesNotSetError,
		)
	else:
		return out
