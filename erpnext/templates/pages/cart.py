# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1


from erpnext.shopping_cart.cart import get_cart_quotation


def get_context(context):
	context.update(get_cart_quotation())
