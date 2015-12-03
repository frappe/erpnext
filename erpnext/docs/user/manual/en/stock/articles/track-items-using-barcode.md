<h1>Track items using Barcode</h1>

A barcode, is a code using multiple lines and spaces of varying widths, designed to represent some alpha-numeric characters. For example, in retail, it generally represents item code / serial number. Most barcode scanners behave like an external keyboard. When it scans a barcode, the data appears in the computer screens at the point of cursor.

To enable barcode feature in ERPNext go to `Setup –> Customize –> Features Setup` and check "Item Barcode" option.
![Features Setup]({{docs_base_url}}/assets/img/articles/feature-setup-barcode.png)

Now, a new field "Barcode" will be appear in Item master, enter barcode while creating a new item. You can update barcode field for existing items using "Data Import Tool".

If you are creating your own barcode, then you should print those same barcodes and attach to your products.
![Item Barcode]({{docs_base_url}}/assets/img/articles/item-barcode.png)


Once you have updated barcode field in item master, you can fetch items using barcode in Delivery Note, Sales Invoice and Purchase Receipt document.

For example, in Delivery Note Item table, a new field "Barcode" will be appear and if you point your mouse cursor to that field and scan the barcode using Barcode Scanner, the code will appear in that field. At the same time, system will pull item details, based on the barcode.
![Delivery Note Barcode]({{docs_base_url}}/assets/img/articles/delivery-note-barcode.png)


<!-- markdown -->