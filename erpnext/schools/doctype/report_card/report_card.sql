SELECT
  `tabProduction Order`.name as "Production Order:Link/Production Order:200",
  `tabProduction Order`.creation as "Date:Date:120",
  `tabProduction Order`.production_item as "Item:Link/Item:150",
  `tabProduction Order`.qty as "To Produce:Int:100",
  `tabProduction Order`.produced_qty as "Produced:Int:100"
FROM
  `tabProduction Order`
WHERE
  `tabProduction Order`.docstatus=1
  AND ifnull(`tabProduction Order`.produced_qty,0) &lt; `tabProduction Order`.qty
  AND EXISTS (SELECT name from `tabStock Entry` where production_order =`tabProduction Order`.name)