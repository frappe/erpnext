#Make Fields Visible In Print Format

Each transaction has Standard Print Format. In the Standard format, only certain fields are displayed by default. If  user needs field in the Standard format to be visible, it can be customized by using Customize Form tool.

Let's assume in the Sales order, we need to make Shipping Address field visible in the standard print format.

#### Step 1: Customize Form

Go to:

`Setup > Customize > Customize Form`

#### Step 2: Document Type

As per our scenario, Sales Order will be selected as Document Type.
field-visible-2.gif
<img alt="Document Type" class="screenshot" src="/docs/assets/img/articles/print-visible-1.png">

#### Step 3: Uncheck Print Hide

click to open field to be made visible in the Standard Print Format. Uncheck **Print Hide** field.

<img alt="Uncheck Print Hide " class="screenshot" src="/docs/assets/img/articles/print-visible-2.gif">

#### Step 4: Update

Update Customize Form to save changed. Reload your ERPNext account, and then check Print Format for confirmation.
