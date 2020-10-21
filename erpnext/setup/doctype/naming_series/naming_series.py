# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cstr, cint
from frappe import msgprint, throw, _

from frappe.model.document import Document
from frappe.permissions import get_doctypes_with_read

class NamingSeriesNotSetError(frappe.ValidationError): pass

class NamingSeries(Document):
	def get_transactions(self, arg=None):
		doctypes = list(set(frappe.db.sql_list("""select parent
				from `tabDocField` df where fieldname='naming_series'""")
			+ frappe.db.sql_list("""select dt from `tabCustom Field`
				where fieldname='naming_series'""")))
		
		prefixes = frappe.db.sql_list("""select name from `tabSeries`""")

		return {
			"transactions": "\n".join([''] + sorted(doctypes)),
			"prefixes": prefixes
		}

	def scrub_options_list(self, ol):
		options = list(filter(lambda x: x, [cstr(n).strip() for n in ol]))
		return options

	def update_series(self, arg=None):
		"""update series list"""
		self.validate_series_set()
		self.check_duplicate()
		series_list = self.set_options.split("\n")

		# set in doctype
		self.set_series_for(self.select_doc_for_series, series_list)

		# create series
		map(self.insert_series, [d.split('.')[0] for d in series_list if d.strip()])

		msgprint(_("Series Updated"))

		return self.get_transactions()

	def validate_series_set(self):
		if self.select_doc_for_series and not self.set_options:
			frappe.throw(_("Please set the series to be used."))

	def set_series_for(self, doctype, ol):
		options = self.scrub_options_list(ol)

		# validate names
		for i in options: self.validate_series_name(i)

		if options and self.user_must_always_select:
			options = [''] + options

		default = options[0] if options else ''

		# update in property setter
		prop_dict = {'options': "\n".join(options), 'default': default}

		for prop in prop_dict:
			ps_exists = frappe.db.get_value("Property Setter",
				{"field_name": 'naming_series', 'doc_type': doctype, 'property': prop})

			if ps_exists:
				ps = frappe.get_doc('Property Setter', ps_exists)
				ps.value = prop_dict[prop]
				ps.save()
			else:
				ps = frappe.get_doc({
					'doctype': 'Property Setter',
					'doctype_or_field': 'DocField',
					'doc_type': doctype,
					'field_name': 'naming_series',
					'property': prop,
					'value': prop_dict[prop],
					'property_type': 'Text',
					'__islocal': 1
				})
				ps.save()

		self.set_options = "\n".join(options)

		frappe.clear_cache(doctype=doctype)

	def check_duplicate(self):
		parent = list(set(
			frappe.db.sql_list("""select dt.name
				from `tabDocField` df, `tabDocType` dt
				where dt.name = df.parent and df.fieldname='naming_series' and dt.name != %s""",
				self.select_doc_for_series)
			+ frappe.db.sql_list("""select dt.name
				from `tabCustom Field` df, `tabDocType` dt
				where dt.name = df.dt and df.fieldname='naming_series' and dt.name != %s""",
				self.select_doc_for_series)
			))
		sr = [[frappe.get_meta(p).get_field("naming_series").options, p] for p in parent]
		dt = frappe.get_doc("DocType", self.select_doc_for_series)
		options = self.scrub_options_list(self.set_options.split("\n"))
		for series in options:
			dt.validate_series(series)
			for i in sr:
				if i[0]:
					existing_series = [d.split('.')[0] for d in i[0].split("\n")]
					if series.split(".")[0] in existing_series:
						frappe.throw(_("Series {0} already used in {1}").format(series,i[1]))

	def validate_series_name(self, n):
		import re
		if not re.match("^[\w\- /.#{}]*$", n, re.UNICODE):
			throw(_('Special Characters except "-", "#", ".", "/", "{" and "}" not allowed in naming series'))

	def get_options(self, arg=None):
		dt = arg or self.select_doc_for_series
		if dt:
			if frappe.get_meta(dt).get_field("naming_series"):
				return frappe.get_meta(dt).get_field("naming_series").options

	def get_prefix(self):
		return self.prefix or self.new_prefix

	def get_current(self, arg=None):
		"""get series current"""
		prefix = self.get_prefix()
		if prefix:
			self.current_value = frappe.db.get_value("Series",
				prefix, "current", order_by = "name")
			self.last_current_value = self.current_value
		else:
			self.current_value = 0
			self.last_current_value = 0

	def insert_series(self, series):
		"""insert series if missing"""
		if frappe.db.get_value('Series', series, 'name', order_by="name") == None:
			frappe.db.sql("insert into tabSeries (name, current) values (%s, 0)", (series))

	def update_series_start(self):
		prefix = self.get_prefix()
		if prefix:
			self.insert_series(prefix)
			db_current_value = frappe.db.sql("select current from `tabSeries` where name = %s for update", prefix)
			db_current_value = cint(db_current_value[0][0] if db_current_value else 0)

			if cint(self.last_current_value) != db_current_value:
				frappe.msgprint(_("Current value for {0} changed. Please reload and update again").format(prefix))
				return 0

			frappe.db.sql("update `tabSeries` set current = %s where name = %s",
				(self.current_value, prefix))
			msgprint(_("Series Updated Successfully"))
			return 1
		else:
			msgprint(_("Please select prefix first"))
			return 1

def set_by_naming_series(doctype, fieldname, naming_series, hide_name_field=True):
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter
	if naming_series:
		make_property_setter(doctype, "naming_series", "hidden", 0, "Check")
		make_property_setter(doctype, "naming_series", "reqd", 1, "Check")
		make_property_setter(doctype, fieldname, "depends_on", "", "Text")

		# set values for mandatory
		try:
			frappe.db.sql("""update `tab{doctype}` set naming_series={s} where
				ifnull(naming_series, '')=''""".format(doctype=doctype, s="%s"),
				get_default_naming_series(doctype))
		except NamingSeriesNotSetError:
			pass

		if hide_name_field:
			make_property_setter(doctype, fieldname, "reqd", 0, "Check")
			make_property_setter(doctype, fieldname, "hidden", 1, "Check")
	else:
		make_property_setter(doctype, "naming_series", "reqd", 0, "Check")
		make_property_setter(doctype, "naming_series", "hidden", 1, "Check")
		make_property_setter(doctype, fieldname, "depends_on", "eval:doc.__islocal", "Text")

		if hide_name_field:
			make_property_setter(doctype, fieldname, "hidden", 0, "Check")
			make_property_setter(doctype, fieldname, "reqd", 1, "Check")

			# set values for mandatory
			frappe.db.sql("""update `tab{doctype}` set `{fieldname}`=`name` where
				ifnull({fieldname}, '')=''""".format(doctype=doctype, fieldname=fieldname))

def get_default_naming_series(doctype):
	naming_series = frappe.get_meta(doctype).get_field("naming_series").options or ""
	naming_series = naming_series.split("\n")
	out = naming_series[0] or (naming_series[1] if len(naming_series) > 1 else None)

	if not out:
		frappe.throw(_("Please set Naming Series for {0} via Setup > Settings > Naming Series").format(doctype),
			NamingSeriesNotSetError)
	else:
		return out
