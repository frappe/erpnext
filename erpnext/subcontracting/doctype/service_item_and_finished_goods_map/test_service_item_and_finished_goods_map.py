# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestServiceItemandFinishedGoodsMap(FrappeTestCase):
	pass


def create_service_item_and_finished_goods_map(service_item, fg_items: str | list[dict]):
	doc = frappe.new_doc("Service Item and Finished Goods Map")
	doc.service_item = service_item
	doc.service_item_qty = 1
	doc.service_item_uom = "Nos"

	if isinstance(fg_items, str):
		doc.append(
			"finished_goods_detail",
			{
				"finished_good_item": fg_items,
				"finished_good_qty": 1,
			},
		)
	else:
		for fg_item in fg_items:
			doc.append("finished_goods_detail", fg_item)

	doc.save()
	return doc.name
