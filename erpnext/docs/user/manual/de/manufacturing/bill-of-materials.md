# Stückliste
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Das Herz des Fertigungssystems bildet die Stückliste. Die **Stückliste** ist eine Auflistung aller Materialien (egal ob gekauft oder selbst hergestellt) und Arbeitsgänge die in das fertige Erzeugnis oder Untererzeugnis einfliessen. In ERPNext kann eine Komponente ihre eigene Stückliste haben, und formt somit eine mehrstufige Baumstruktur.

Um passende Einkaufsanfragen zu erstellen, müssen Sie Ihre Stücklisten immer auf dem aktuellen Stand halten. Um eine neue Stückliste anzulegen, gehen Sie zu:

>Fertigung > Dokumente > Stückliste > Neue Stückliste

<img class="screenshot" alt="Task" src="{{docs_base_url}}/assets/img/manufacturing/bom.png">

Um Arbeitsgänge hinzuzufügen, wählen Sie "Mit Arbeitsgängen". Die Übersicht der Arbeitsgänge erscheint.

<img class="screenshot" alt="Task" src="{{docs_base_url}}/assets/img/manufacturing/bom-operations.png">

* Wählen Sie den Artikel für den Sie eine Stückliste erstellen wollen.
* Fügen Sie die Arbeitsgänge, die Sie durchlaufen müssen, um diesen Artikel zu fertigen, in der Tabelle der Arbeitsgänge hinzu. Für jeden Arbeitsgang werden Sie nach einem Arbeitsplatz gefragt. Wenn nötig, müssen Sie neue Arbeitsplätze anlegen.
* Arbeitsplätze sind nur für die Produktkostenkalkulation und die Terminplanung der Arbeitsgänge des Fertigungsauftrags definiert, nicht für das Fertigungslager.
* Der Bestand an Erzeugnissen wird über das Lager nachverfolgt, nicht über die Arbeitsplätze.

### Kostenkalkulation einer Stückliste

* Der Bereich Kostenkalkulation der Stückliste gibt einen ungefähren Wert der Produktionskosten eines Artikels wieder
* Fügen Sie die Liste der Artikel, die Sie für jeden Arbeitsgang benötigen, mit der entsprechenden Menge hinzu. Bei dem Artikel kann es sich um einen Zukaufartikel oder um eine Unterfertigung mit eigener Stückliste handeln. Wenn der Artikel in der Zeile ein gefertigter Artikel ist und mehrere verschiedene Stücklisten hat, wählen Sie die passende Stückliste aus. Sie können auch festlegen, ob ein Teil des Artikels zu Ausschuss wird.

<img class="screenshot" alt="Kostenkalkulation" src="{{docs_base_url}}/assets/img/manufacturing/bom-costing.png">

* Diese Kosten können über die Schaltfläche "Kosten aktualisieren" aktualisiert werden.

<img class="screenshot" alt="Kosten aktualisieren" src="{{docs_base_url}}/assets/img/manufacturing/bom-update-cost.png">

### Benötigtes Material (aufgelöst)

Diese Tabelle listet alles Material auf, welches benötigt wird um den Artikel zu fertigen. Sie zieht weiterhin Unterbaugruppen mit Menge an.

<img class="screenshot" alt="Aufgelöste Ansicht" src="{{docs_base_url}}/assets/img/manufacturing/bom-exploded.png">

{next}
