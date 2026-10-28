<script setup>
import { computed, nextTick, ref } from "vue";
import { ChartCard, LineChart } from "frappe-ui/charts";

import BudgetChart from "./BudgetChart.vue";
import KpiCards from "./KpiCards.vue";
import LedgerEntries from "./LedgerEntries.vue";
import { accountKpis, toAccountsView } from "../accounts.js";
import { useFormat } from "../format.js";

const props = defineProps({
	payload: { type: Object, required: true },
	// From the Project view: no customer, order or billing, and whether the project is closed.
	internal: { type: Boolean, default: false },
	closed: { type: Boolean, default: false },
});

const __ = window.__;
const format = useFormat();

const accounts = computed(() => toAccountsView(props.payload));
const kpis = computed(() => accountKpis(accounts.value, format, { internal: props.internal }));
const months = computed(() =>
	accounts.value.monthly.map((row) => ({ ...row, label: format.month(row.month) }))
);

const account = ref(null);
function select(name) {
	account.value = name;
	nextTick(() =>
		document.getElementById("ledger-entries")?.scrollIntoView({ behavior: "smooth", block: "start" })
	);
}
</script>

<template>
	<div class="space-y-5">
		<KpiCards :items="kpis" />
		<BudgetChart v-if="accounts.expense.length" :accounts="accounts" :closed="closed" @select="select" />
		<ChartCard v-if="accounts.has_entries || accounts.budget_count" class="h-80">
			<LineChart
				:title="__('Spend against budget')"
				:data="months"
				x="label"
				:y="accounts.budget_count ? ['actual', 'budget'] : ['actual']"
				:series-config="{
					actual: { label: __('Actual') },
					budget: { label: __('Budget to date'), dashed: true },
				}"
				:y-axis="{ format: format.short, min: 0 }"
			/>
		</ChartCard>
		<LedgerEntries v-model:account="account" :accounts="accounts" />
	</div>
</template>
