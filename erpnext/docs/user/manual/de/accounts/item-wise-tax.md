# Artikelbezogene Steuer
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Wenn Sie über die Einstellung "Steuern und andere Abgaben" Steuern auswählen, werden diese in Transaktionen auf alle Artikel angewendet. Wenn jedoch unterschiedliche Steuern auf bestimmte Artikel in Transaktionen angewendet werden sollen, sollten Sie die Stammdaten für Ihre Artikel und Steuern wie folgt einstellen.

#### Schritt 1: Geben Sie im Artikelstamm die Steuer an, die angewendet werden soll.

Die Artikelstammdaten beinhalten eine Tabelle, in der Sie Steuern, die angewendet werden sollen, auflisten können.

![Artikelbezogene Steuer](/docs/assets/old_images/erpnext/item-wise-tax.png)

Der im Artikelstamm angegebene Steuersatz hat gegenüber dem Steuersatz, der in Transaktionen angegeben wird, Vorrang.

Beispiel: Wenn Sie einen Umsatzsteuersatz von 10% für den Artikel ABC verwenden wollen, aber im Kundenauftrag/der Ausgangsrechnung ein Umsatzsteuersatz von 12% für den Artikel ABC angegeben ist, dann wird der Steuersatz von 10% verwendet, so wie es in den Artikelstammdaten hinterlegt ist.

#### Schritt 2: Steuern und andere Abgaben einrichten

In den Stammdaten für Steuern und andere Abgaben sollten Sie alle auf Artikel anwendbaren Steuern auswählen.

Beispiel: Wenn Sie Artikel mit 5% Umsatzsteuer haben, bei anderen eine Dienstleistungssteuer anfällt und bei wieder anderen eine Luxussteuer, dann sollten Ihre Steuerstammdaten auch alle drei Steuern enthalten.

![Vorlage für artikelbezogene Steuer](/docs/assets/old_images/erpnext/item-wise-tax-master.png)

#### Schritt 3: Steuersatz in den Stammdaten für Steuern und Abgaben auf 0 einstellen

In den Stammdaten für Steuern und andere Abgaben wird der Steuersatz mit 0% eingepflegt. Das heißt, dass der Steuersatz, der auf Artikel angewendet wird, aus den entsprechenden Artikelstammdaten gezogen wird. Für alle anderen Artikel wird ein Steuersatz von 0% verwendet, das heißt es werden keine weiteren Steuern verwendet.

Basierend auf den obigen Einstellungen werden Steuern also wie in den Artikelstammdaten angegeben angewendet. Probieren Sie beispielsweise Folgendes aus:

![Artikelbezogene Steuerkalkulation](/docs/assets/old_images/erpnext/item-wise-tax-calc.png)

{next}
