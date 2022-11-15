# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cstr
from frappe.model.document import Document
from collections import defaultdict
import json
from six import string_types


class UOMConversionFactor(Document):
	def validate(self):
		clear_conversion_factor_cache()
		if not frappe.flags.in_install and not frappe.flags.in_patch:
			make_conversion_map(validate_multiple_conversion=[self.from_uom, self.to_uom])


# Modified version of https://www.geeksforgeeks.org/find-paths-given-source-destination/
class UOMConversionGraph:
	def __init__(self, copy_from=None):
		if copy_from:
			self.graph = copy_from['graph']
			self.uoms = copy_from['uoms']
		else:
			self.graph = defaultdict(list)
			self.uoms = []

	def add_conversion(self, from_uom, to_uom, conversion_factor):
		conversion_factor = flt(conversion_factor)
		if not conversion_factor:
			frappe.throw(_("{0} -> {1}: Conversion Factor cannot be 0").format(from_uom, to_uom))

		self._add_edge(from_uom, to_uom, conversion_factor)
		self._add_edge(to_uom, from_uom, 1/conversion_factor)

		if from_uom not in self.uoms:
			self.uoms.append(from_uom)
		if to_uom not in self.uoms:
			self.uoms.append(to_uom)

	def _add_edge(self, src, dest, weight):
		self.graph[src].append((dest, weight))

	def get_conversion_factor(self, from_uom, to_uom,
			validate_not_convertible=False, validate_multiple_conversion=False, raise_exception=False):
		if from_uom == to_uom:
			return 1

		paths = self.get_all_paths(from_uom, to_uom)
		if not paths:
			if validate_not_convertible:
				frappe.msgprint(_("No Conversion Factor found for {0} -> {1}")
					.format(frappe.bold(from_uom), frappe.bold(to_uom)),
					raise_exception=raise_exception)
			return 0

		# calculate the net conversion factor for each uom considering all paths
		weights = [1] * len(paths)
		for path_idx, path in enumerate(paths):
			for d in path:
				weights[path_idx] *= d[1]

		conversion_factor = weights[0]

		# if there are multiple paths, validate their conversion_factors are consistent
		if validate_multiple_conversion:
			self.validate_multiple_conversions(from_uom, to_uom, weights, paths,
				for_uoms=validate_multiple_conversion, raise_exception=raise_exception)

		return conversion_factor

	def validate_multiple_conversions(self, from_uom, to_uom, weights, paths, for_uoms=None, raise_exception=False):
		precision = frappe.get_precision('UOM Conversion Factor', 'value')

		if isinstance(for_uoms, string_types):
			for_uoms = [for_uoms]

		all_conversion_factors = []
		all_paths = []
		for path_idx, w in enumerate(weights):
			rounded_weight = flt(w, precision)
			if rounded_weight not in all_conversion_factors:
				all_conversion_factors.append(rounded_weight)
				all_paths.append([p[0] for p in paths[path_idx]])

		if len(all_conversion_factors) > 1:
			warn = False if isinstance(for_uoms, list) else True

			path_list = []
			for cf, path in zip(all_conversion_factors, all_paths):
				if not warn and isinstance(for_uoms, list):
					for for_uom in for_uoms:
						if for_uom in path:
							warn = True
							break

				path_list.append("{0}: {1}".format(" -> ".join(path), cstr(cf)))

			path_list = "<br>".join(path_list)

			if warn:
				frappe.msgprint(_("Multiple Conversion Factors found for {0} -> {1}:<br>{2}")
					.format(frappe.bold(from_uom), frappe.bold(to_uom), path_list),
					raise_exception=raise_exception)

	def get_all_paths(self, from_uom, to_uom):
		visited = {k: False for k in self.uoms}
		all_paths = []
		current_path = []
		self._get_paths(from_uom, to_uom, visited, current_path, all_paths, 1.0)

		# sort by smallest path first
		all_paths = sorted(all_paths, key=lambda p: len(p))

		return all_paths

	def _get_paths(self, from_uom, to_uom, visited, current_path, all_paths, previous_cf):
		# Mark the current node as visited and store in path
		visited[from_uom] = True
		current_path.append((from_uom, previous_cf))

		# If current vertex is same as destination, then print current path[]
		if from_uom == to_uom:
			all_paths.append(current_path.copy())
		else:
			# If current vertex is not destination Recur for all the vertices adjacent to this vertex
			for intermediate_uom, next_cf in self.graph[from_uom]:
				if not visited[intermediate_uom]:
					self._get_paths(intermediate_uom, to_uom, visited, current_path, all_paths, next_cf)

		# Remove current vertex from path[] and mark it as unvisited
		current_path.pop()
		visited[from_uom] = False


def get_conversion_map():
	def generator():
		return make_conversion_map()

	return frappe.cache().get_value('uom_conversion_factor_map', generator)


def clear_conversion_factor_cache():
	frappe.cache().delete_value('uom_conversion_factor_map')


def make_conversion_map(validate_not_convertible=False, validate_multiple_conversion=False, raise_exception=False):
	precision = frappe.get_precision('UOM Conversion Factor', 'value')
	conversion_map = {}

	graph = make_conversion_graph()

	# add direct conversions first
	for from_uom, paths in graph.graph.items():
		for to_uom, conversion_factor in paths:
			conversion_map.setdefault(from_uom, {})[to_uom] = conversion_factor

	# then add indirect conversions
	for from_uom in graph.uoms:
		for to_uom in graph.uoms:
			if from_uom == to_uom:
				continue
			if conversion_map.get(from_uom, {}).get(to_uom):
				continue

			conversion_factor = graph.get_conversion_factor(from_uom, to_uom,
				validate_not_convertible=validate_not_convertible,
				validate_multiple_conversion=validate_multiple_conversion,
				raise_exception=raise_exception)

			conversion_factor = flt(conversion_factor, precision)
			if conversion_factor:
				conversion_map.setdefault(from_uom, {})[to_uom] = conversion_factor

	return conversion_map


def make_conversion_graph():
	conversions = frappe.get_all("UOM Conversion Factor", fields=['from_uom', 'to_uom', 'value'])

	graph = UOMConversionGraph()
	for c in conversions:
		if flt(c.value):
			graph.add_conversion(c.from_uom, c.to_uom, flt(c.value))

	return graph


@frappe.whitelist()
def get_uom_conv_factor(from_uom, to_uom):
	conversion_map = get_conversion_map()
	conversion_factor = flt(conversion_map.get(from_uom, {}).get(to_uom))

	if not conversion_factor:
		conversion_factor = flt(conversion_map.get(to_uom, {}).get(from_uom))
		if conversion_factor:
			conversion_factor = 1/conversion_factor

	return conversion_factor
