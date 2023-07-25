import frappe

jinja = {
    "methods": [
        "erpnext.jinja.trip_items",
    ],
}

# METHODS
@frappe.whitelist()
def trip_items(doc=None):
    values = {'sales_invoices': doc}
    res=frappe.db.sql("""
                select i.item_name, i.stock_uom, 
                min(conv.conversion_factor) as conversion_factor,
                conv.uom as bulk_uom,
                sum(i.stock_qty) as qty from `tabSales Invoice Item` as i
                left join `tabUOM Conversion Detail` as conv
                on conv.parent = i.item_code
                where i.parent in %(sales_invoices)s 
                and 
                    (
                        conv.conversion_factor > 1
                        OR conv.parent in
                           (select parent from `tabUOM Conversion Detail` group by parent having count(*) = 1)
                    )
                and conv.uom != 'M/Ctn'
                group by i.item_name 
                """,values=values ,as_dict=True)
    return res