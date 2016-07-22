# Lieferschein
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Ein Lieferschein wird dann erstellt, wenn ein Versand vom Lager der Firma statt findet.

Normalerweise wird eine Kopie des Lieferscheins der Sendung beigelegt. Der Lieferschein beinhaltet die Auflistung der Artikel, die versendet werden, und aktualisiert den Lagerbestand.

Die Buchung zum Lieferschein ist derjenigen zum Kaufbeleg sehr ähnlich. Sie können einen neuen Lieferschein erstellen über:  

> Lagerbestand > Dokumente > Lieferschein > Neu

oder aber über eine "übertragene" Kundenbestellung (die noch nicht versandt wurde) indem Sie auf "Lieferschein erstellen" klicken.

<img class="screenshot" alt="Lieferschein" src="{{docs_base_url}}/assets/img/stock/delivery-note.png">

Sie können die Details auch aus einer noch nicht gelieferten Kundenbestellung "herausziehen".

Sie werden bemerken, dass alle Informationen über nicht gelieferte Artikel und andere Details aus der Kundenbestellung übernommen werden.

### Pakete oder Artikel mit Produkt-Bundles versenden

Wenn Sie Artikel, die ein [Produkt-Bundle]({{docs_base_url}}/user/manual/de/selling/setup/product-bundle.html), ERPNext will automatically beinhalten, versenden, erstellt Ihnen ERPNext automatisch eine Tabelle "Packliste" basierend auf den Unterartikeln dieses Artikels.

Wenn Ihre Artikel serialisiert sind, dann müssen Sie für Artikel vom Typ Produkt-Bundle die Seriennummer in der Tabelle "Packliste" aktualisieren.

### Artikel für Containerversand verpacken

Wenn Sie per Containerversand oder nach Gewicht versenden, können Sie die Packliste verwenden um Ihren Lieferschein in kleinere Einheiten aufzuteilen. Um eine Packliste zu erstellen gehen Sie zu:

> Lagerbestand > Werkzeuge > Packzettel > Neu

Sie können für Ihren Lieferschein mehrere Packlisten erstellen und ERPNext stellt sicher dass die Mengenangaben in der Packliste  nicht die Mengen im Lieferschein übersteigen.

---

### Frage: Wie druckt man ohne die Angabe der Stückzahl/Menge aus?

Wenn Sie Ihre Lieferscheine ohne Mengenangabe ausdrucken wollen (das ist dann sinnvoll, wenn Sie Artikel mit hohem Wert versenden), kreuzen Sie "Ohne Mengenangabe ausdrucken" im Bereich "Weitere Informationen" an.

### Frage: Was passiert, wenn der Lieferschein "übertragen" wurde?

Für jeden Artikel wird eine Buchung im Lagerhauptbuch erstellt und der Lagerbestand wird aktualisiert. Ebenfalls wird die Ausstehende Menge im Kundenauftrag (sofern zutreffend) aktualisiert.

{next}
