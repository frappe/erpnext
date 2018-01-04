# Serial No

As we discussed in the **Item** section, if an **Item** is _serialized_, a
**Serial Number** (Serial No) record is maintained for each quantity of that
**Item**. This information is helpful in tracking the location of the Serial
No, its warranty and end-of-life (expiry) information.

**Serial Nos** are also useful to maintain fixed assets. **Maintenance Schedules** can also be created against serial numbers for planning and scheduling maintenance activity for these assets (if they require maintenance).

You can also track from which **Supplier** you purchased the **Serial No** and
to which **Customer** you have sold it. The **Serial No** status will tell you
its current inventory status.

If your Item is _serialized_ you will have to enter the Serial Nos in the
related column with each Serial No in a new line.
You can maintain single units of serialized items using Serial Number.

### Serial Nos and Inventory

Inventory of an Item can only be affected if the Serial No is transacted via a
Stock transaction (Stock Entry, Purchase Receipt, Delivery Note, Sales
Invoice). When a new Serial No is created directly, its warehouse cannot be
set.

<img class="screenshot" alt="Serial Number" src="/docs/assets/img/stock/serial-no.png">

* The Status is set based on Stock Entry.

* Only Serial Numbers with status 'Available' can be delivered.

* Serial Nos can automatically be created from a Stock Entry or Purchase Receipt. If you mention Serial No in the Serial Nos column, it will automatically create those serial Nos.

* If in the Item Master, the Serial No Series is mentioned, you can leave the Serial No column blank in a Stock Entry / Purchase Receipt and Serial Nos will automatically be set from that series.

{next}