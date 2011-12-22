def execute():
    import webnotes
    sql = webnotes.conn.sql
    from webnotes.model.code import get_obj
    from webnotes.utils import flt

    # update incoming rate in serial nos
    sr = sql("""select name, item_code, purchase_document_no from `tabSerial No`
            where docstatus = 1 and purchase_document_type = 'Purchase Receipt'""")
    for d in sr:
        val_rate = sql("""select valuation_rate from `tabPurchase Receipt Detail`
            where item_code = %s and parent = %s""", (d[1], d[2]))
        sql("""update `tabSerial No` set purchase_rate = %s where name = %s""",
           (val_rate and flt(val_rate[0][0]) or 0, d[0]))
    
    
    # repost for all serialized item
    bin = sql("""select t1.name from `tabBin` t1, tabItem t2 where t1.item_code = t2.name and ifnull(has_serial_no, 'No') = 'Yes'""")
    for d in bin:
        get_obj('Bin', d[0]).update_entries_after(posting_date = '2000-01-01', posting_time = '12:00')
        sql("commit")
        sql("start transaction")

