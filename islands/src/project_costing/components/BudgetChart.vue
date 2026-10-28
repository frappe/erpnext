<script setup>
import { computed, ref } from "vue";
import { Button, Dialog, Tooltip } from "frappe-ui";
import { BarChart, ChartCard } from "frappe-ui/charts";
import { useHost } from "@framework/ui/island";

import AccountTable from "./AccountTable.vue";
import { newBudgetRoute } from "../accounts.js";
import { useFormat } from "../format.js";

const props = defineProps({
	accounts: { type: Object, required: true },
	closed: { type: Boolean, default: false },
});
const emit = defineEmits(["select"]);

const __ = window.__;
const format = useFormat();
const host = useHost();
const show_table = ref(false);

/**
 * One bar per expense account: actual, then committed, then what is left of its budget, so a
 * budgeted bar is as long as its budget. An account past its budget has nothing left and runs
 * longer; one without a budget is actual and committed only.
 */
const rows = computed(() =>
	props.accounts.expense.map((row) => ({
		label: row.account_name,
		account: row.account,
		actual: row.actual,
		committed: row.committed,
		left: row.budget ? Math.max(row.budget.amount - row.actual - row.committed, 0) : 0,
	}))
);
const series = computed(() => [
	"actual",
	...(props.accounts.committed ? ["committed"] : []),
	...(props.accounts.budget_count ? ["left"] : []),
]);
const series_config = {
	actual: { label: __("Actual") },
	committed: { label: __("Committed") },
	left: { label: __("Budget left") },
};
const can_add = computed(() => props.accounts.access.manage_budgets && !props.closed);

function select_from_table(account) {
	show_table.value = false;
	emit("select", account);
}
</script>

<template>
	<ChartCard class="h-80">
		<BarChart
			:title="__('Budget vs actual by account')"
			:subtitle="accounts.fiscal_year"
			:data="rows"
			x="label"
			:y="series"
			:series-config="series_config"
			:y-axis="{ format: format.short, min: 0 }"
			horizontal
			stacked
			@select="(event) => emit('select', event.row.account)"
		>
			<template #actions>
				<div class="flex items-center gap-2">
					<Button
						v-if="can_add"
						size="sm"
						icon-left="lucide-plus"
						:label="__('Add budget')"
						@click="host.navigate?.(newBudgetRoute(accounts))"
					/>
					<Tooltip :text="__('View as table')">
						<Button
							size="sm"
							variant="ghost"
							icon="lucide-table"
							:aria-label="__('View as table')"
							@click="show_table = true"
						/>
					</Tooltip>
				</div>
			</template>
		</BarChart>

		<Dialog
			v-model:open="show_table"
			:title="__('Budget vs actual · {0}', [accounts.fiscal_year])"
			size="4xl"
		>
			<AccountTable :accounts="accounts" @select="select_from_table" />
		</Dialog>
	</ChartCard>
</template>
