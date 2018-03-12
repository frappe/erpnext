#Managing Fractions in UoM

UoM stands for Unit of Measurement. Few examples of UoM are Numbers (Nos), Kgs, Litre, Meter, Box, Carton etc.

There are few UoMs which cannot have value in decimal places. For example, if we have television for an item, with Nos as its UoM, we cannot have 1.5 Nos. of television, or 3.7 Nos. of computer sets. The value of quantity for these items must be whole number.

You can configure if particular UoM can have value in decimal place or no. By default, value in decimal places will be allowed for all the UoMs. To restrict decimal places or value in fraction for any UoM, you should follow these steps.

####UoM List

For UoM list, go to:

`Stock > Setup > UoM`

From the list of UoM, select UoM for which value in decimal place is to be restricted. Let's assume that UoM is Nos.

####Configure

In the UoM master, you will find a field called "Must be whole number". Check this field to restrict user from enter value in decimal places in quantity field, for item having this UoM.

<img alt="UoM Must be Whole No" class="screenshot" src="{{docs_base_url}}/assets/img/articles/uom-fraction-1.png">

####Validation

While creating transaction, if you enter value in fraction for item whos UoM has "Must be whole number" checked, you will get error message stating:

`Quantity cannot be a fraction at row #`

<img alt="UoM Validation Message" class="screenshot" src="{{docs_base_url}}/assets/img/articles/uom-fraction-2.png">


<!-- markdown -->