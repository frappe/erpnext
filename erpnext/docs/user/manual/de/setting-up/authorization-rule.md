# Autorisierungsregeln
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Mit Hilfe des Werkzeugs "Autorisierungsregeln" können Sie Regeln für Genehmigungen bestimmen, die an Bedingungen geknüpft sind.

Wenn eine Ihrer Vertriebs- oder Einkaufstransaktionen von höherem Wert oder mit höherem Rabatt eine Genehmigung durch eine Führungskraft benötigt, können Sie dafür eine Autorisierungsregel einrichten.

Um eine neue Autorisierungsregel zu erstellen, gehen Sie zu:

> Einstellungen > Anpassen > Autorisierungsregel

Lassen Sie uns ein Beispiel für eine Autorisierungsregel betrachten, um den Sachverhalt besser zu verstehen.

Nehmen wir an dass ein Vertriebsmitarbeiter Kundenbestellungen nur dann genehmigen lassen muss, wenn der Gesamtwert 10.000 Euro übersteigt. Wenn die Kundenbestellung 10.000 Euro nicht übersteigt, dann kann auch ein Vertriebsmitarbeiter diese Transaktion übertragen. Das bedeutet, dass die Berechtigung des Vertriebsmitarbeiters zum Übertragen auf Kundenaufträge mit einer Maximalsumme von 10.000 Euro beschränkt wird.

#### Schritt 1

Öffnen Sie eine neue Autorisierungsregel.

#### Schritt 2

Wählen Sie die Firma und die Transaktion aus, für die diese Autorisierungsregel angewendet werden soll. Diese Funktionalität ist nur für beschränkte Transaktionen verfügbar.

#### Schritt 3

Wählen Sie einen Wert für "Basiert auf" aus. Eine Autorisierungsregel wird auf Grundlage eines Wertes in diesem Feld angewendet.

#### Schritt 4

Wählen Sie eine Rolle, auf die die Autorisierungsregel angewendet werden soll. Für unser angenommenes Beispiel wird die Rolle "Nutzer Vertrieb" über "Anwenden auf (Rolle)" als Rolle ausgewählt. Um noch etwas genauer zu werden, können Sie auch über "Anwenden auf (Benutzer)" einen bestimmten Benutzer auswählen, wenn Sie eine Regel speziell auf einen Mitarbeiter anwenden wollen, und nicht auf alle Mitarbeiter aus dem Vertrieb. Es ist auch in Ordnung, keinen Benutzer aus dem Vertrieb anzugeben, weil es nicht zwingend erforderlich ist.

#### Schritt 5

Wählen Sie die Rolle des Genehmigers aus. Das könnte z. B. die Rolle des Vertriebsleiters sein, die Kundenaufträge über 10.000 Euro übertragen darf. Sie können auch hier einen bestimmten Vertriebsleiter auswählen, und dann die Regel so gestalten, dass Sie nur auf diesen Benutzer anwendbar ist. Einen genehmigenden Benutzer anzugeben ist nicht zwingend erfoderlich.

#### Schritt 6

Geben Sie "Autorisierter Wert" ein. Im Beispiel stellen wir das auf 10.000 Euro ein.

<img class="screenshot" alt="Autorisierungsregel" src="/docs/assets/img/setup/auth-rule.png">

Wenn ein Benutzer aus dem Vertrieb versucht eine Kundenbestellung mit einem Wert über 10.000 Euro zu übertragen, dann bekommt er eine Fehlermeldung.

>Wenn Sie den Vertriebsmitarbeiter generall davon ausschliessen wollen, Kundenaufträge zu übertragen, dann sollten Sie keine Autorisierungsregel erstellen, sondern die Berechtigung zum Übertragen über den Rollenberchtigungs-Manager für die Rolle Vertriebsmitarbeiter entfernen.

{next}
