# Bar Code

A Barcode is a machine-readable code in the form of numbers and a pattern of
parallel lines of varying widths, printed on a commodity and used especially
for stock control.

When you purchase an item from any store, you will notice a label with thin,
black lines across it, along with a variation of different numbers. This label
is then scanned by the cashier, and the item's description and price
automatically comes up. This set of lines and numbers on the label are termed
as bar-code.

A bar-code machine scans the number from the label of an Item. To work with
ERPNext and the bar-code mechanism, connect the bar-code machine to your
operating hardware. Then go to ERPNext setup and activate bar-code by going to
tools and clicking on 'hide / unhide features'. Under Materials, feature
setup, check the box that says Item Barcode.

> Setup > Customize > Hide/ Unhide Features > Item Barcode.

#### Figure 1: Check the box 'Item Barcode'

<img class="screenshot" alt="Barcode" src="/docs/assets/img/setup/barcode-1.png">


To start scanning with a bar-code, go to  

> Accounts > Sales Invoice

Under Item, click on Add new row. The item row will expand to show new fields.
Place your cursor on the bar-code field and begin scanning. The bar-code will
be updated in the field. Once the bar-code is entered, all the Item details
will be fetched automatically by the system.

For more ease, activate the POS view in ERPnext. The activation process is
same as the bar-code activation. Go to Setup and click on 'hide/unhide
features'. Check the 'POS view' box.

Then go to Accounts and click on Sales Invoice. Check the box 'Is POS'

  
#### Figure 2: Check the box 'Is POS'

<img class="screenshot" alt="Barcode" src="/docs/assets/img/setup/barcode-2.png">


Go to Item and click on Add new row.  

The cursor will automatically be placed in the bar-code field. Thus you can
immediately scan the bar-code and proceed with your operations.

{next}
