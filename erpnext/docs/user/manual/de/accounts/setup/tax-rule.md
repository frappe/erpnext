# Steuerregeln
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Sie können festlegen, welche [Steuervorlage]({{docs_base_url}}/user/manual/de/setting-up/setting-up-taxes.html) auf eine Verkaufs-/Einkaufstransaktion angewendet wird, wenn Sie die Funktion Steuerregel verwenden.

<img class="screenshot" alt="Steuerregel" src="{{docs_base_url}}/assets/img/accounts/tax-rule.png">

Sie können Steuerregeln für Umsatz- und für Vorsteuern erstellen. Wenn Sie eine Transaktion durchführen, wählt das System Steuervorlagen basierend auf den definierten Steuerregeln aus und wendet sie an. Das System filtert Steuerregeln nach der Anzahl der maximal zutreffenden Bedingungen.

Betrachten wir ein Szenario um Steuerregeln besser zu verstehen.

Angenommen wird haben zwei Steuerregeln wie unten abgebildet erstellt.

<img class="screenshot" alt="Steuerregel" src="{{docs_base_url}}/assets/img/accounts/tax-rule-1.png">

<img class="screenshot" alt="Steuerregel" src="{{docs_base_url}}/assets/img/accounts/tax-rule-2.png">

In unserem Beispiel gilt Regel 1 für Indien und Regel 2 für Großbritannien.

Wenn wir nun annehmen, dass wir einen Kundenauftrag für einen Kunden erstellen wollen, dessen Standard-Abrechnungsland Indien ist, dann sollte das System Regel 1 anwenden. Für den Fall, dass das Abrechnungsland des Kunden Großbritannien ist, wird Regel 2 ausgewählt.
