import json


def extract(fileobj, *args, **kwargs):
	"""
	Extract messages from a JSON file with standard UOM data. To be used by the Babel extractor.

	:param fileobj: the file-like object the messages should be extracted from
	:rtype: `iterator`
	"""
	uom_list = json.load(fileobj)

	if not isinstance(uom_list, list):
		return

	for uom_data in uom_list:
		yield None, "_", uom_data.get("uom_name"), ["Name of a UOM"]
