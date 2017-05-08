#LetterHead

Each company has default LetterHead for their company. This LetterHead values are generally set as Header and Footer in the documents. In ERPNext, you can capture the these details in the LetterHead master.

In the LetterHead master, you can track Header and Footer details of the company. These details will appear in the Print Format of the transactions like Sales Order, Sales Invoice, Salary Slip, Purchase Order etc.

####Step 1: Go to Setup

`Explore > Setup > Printing > LetterHead > New LetterHead`

####Step 2: LetterHead Name

In one ERPNext account, you can enter multiple LetterHead, hence name LetterHead so that you can identify it easily. For example, if your LetterHead also contains office address, then you should create separate LetterHead for each office location.

####Step 3: Enter Details

Following is how you can enter details in the LetterHead.

  * Logo Image: You can insert the image in your LetterHead record by clicking on image icon. Once image is inserted, HTML for it will be generated automatically.
  * Other information (like Address, tax ID etc.) that you want to put on your LetterHead.

<img class="screenshot" alt="Print Heading" src="{{docs_base_url}}/assets/img/setup/print/letter-head.png">
  
> If you want to make this the default LetterHead, click on “Is Default”.

####Step 4: Save

After enter values in the Header and Footer section, Save LetterHead.

####LetterHead in the Print Format

This is how the LetterHead looks in a document's print.

<img class="screenshot" alt="Print Heading" src="{{docs_base_url}}/assets/img/setup/print/letter-head-1.png">

> Please note that Footer will be visible only when document's print is seen in the PDF. Footer will not be visible in the HTML based print preview.

{next}