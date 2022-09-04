"""
Created on Tue Jun 26 15:42:07 2012

Borrowed from https://github.com/timotheus/ebaysdk-python

@author: pierre
"""

import re
import xml.etree.ElementTree as ET


class object_dict(dict):
	"""object view of dict, you can
	>>> a = object_dict()
	>>> a.fish = 'fish'
	>>> a['fish']
	'fish'
	>>> a['water'] = 'water'
	>>> a.water
	'water'
	>>> a.test = {'value': 1}
	>>> a.test2 = object_dict({'name': 'test2', 'value': 2})
	>>> a.test, a.test2.name, a.test2.value
	(1, 'test2', 2)
	"""

	def __init__(self, initd=None):
		if initd is None:
			initd = {}
		dict.__init__(self, initd)

	def __getattr__(self, item):

		try:
			d = self.__getitem__(item)
		except KeyError:
			return None

		if isinstance(d, dict) and "value" in d and len(d) == 1:
			return d["value"]
		else:
			return d

	# if value is the only key in object, you can omit it
	def __setstate__(self, item):
		return False

	def __setattr__(self, item, value):
		self.__setitem__(item, value)

	def getvalue(self, item, value=None):
		return self.get(item, {}).get("value", value)


class xml2dict(object):
	def __init__(self):
		pass

	def _parse_node(self, node):
		node_tree = object_dict()
		# Save attrs and text, hope there will not be a child with same name
		if node.text:
			node_tree.value = node.text
		for (k, v) in node.attrib.items():
			k, v = self._namespace_split(k, object_dict({"value": v}))
			node_tree[k] = v
		# Save childrens
		for child in node.getchildren():
			tag, tree = self._namespace_split(child.tag, self._parse_node(child))
			if tag not in node_tree:  # the first time, so store it in dict
				node_tree[tag] = tree
				continue
			old = node_tree[tag]
			if not isinstance(old, list):
				node_tree.pop(tag)
				node_tree[tag] = [old]  # multi times, so change old dict to a list
			node_tree[tag].append(tree)  # add the new one

		return node_tree

	def _namespace_split(self, tag, value):
		"""
		Split the tag '{http://cs.sfsu.edu/csc867/myscheduler}patients'
		ns = http://cs.sfsu.edu/csc867/myscheduler
		name = patients
		"""
		result = re.compile(r"\{(.*)\}(.*)").search(tag)
		if result:
			value.namespace, tag = result.groups()

		return (tag, value)

	def parse(self, file):
		"""parse a xml file to a dict"""
		f = open(file, "r")
		return self.fromstring(f.read())

	def fromstring(self, s):
		"""parse a string"""
		t = ET.fromstring(s)
		root_tag, root_tree = self._namespace_split(t.tag, self._parse_node(t))
		return object_dict({root_tag: root_tree})
