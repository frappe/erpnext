<script setup>
import { computed } from "vue";
import { Button, Tooltip } from "frappe-ui";
import { ChartCard, ChartContainer, DonutChart } from "frappe-ui/charts";

import EmptyState from "./EmptyState.vue";
import InfoTip from "./InfoTip.vue";
import { useFormat } from "../format.js";
import { useActions } from "../host.js";

const props = defineProps({
	profitability: { type: Object, default: null },
});

const __ = window.__;
const format = useFormat();
const actions = useActions();

const info = __(
	"Billed is the amount on Sales Invoices for this project. Cost is the time logged at costing rates, plus purchases and consumed material. Gross margin is Billed less Cost."
);

const money = (value) => format.money(value, props.profitability.currency);
const rows = computed(() => [
	{ label: __("Billed"), value: props.profitability.billed },
	{ label: __("Cost"), value: props.profitability.cost },
]);
const nothing = computed(
	() => Boolean(props.profitability) && !props.profitability.billed && !props.profitability.cost
);
const colors = { [__("Billed")]: "var(--surface-green-7)", [__("Cost")]: "var(--surface-red-6)" };
const margin_label = computed(() => {
	const { margin_percent } = props.profitability;
	return margin_percent == null
		? __("Gross Margin")
		: __("Gross Margin {0}%", [format.number(margin_percent, 1)]);
});
</script>

<template>
	<ChartCard class="h-[350px]">
		<ChartContainer
			:title="__('Profitability')"
			:error="profitability ? null : __('Could not load tasks')"
			:empty="nothing"
		>
			<template #title-suffix><InfoTip :text="info" /></template>
			<template #actions>
				<Tooltip :text="__('Open Costing')">
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-arrow-up-right"
						:aria-label="__('Open Costing')"
						@click="actions.open_tab('costing_tab')"
					/>
				</Tooltip>
			</template>
			<template #error>
				<span class="text-sm-medium text-ink-red-7">{{ __("Could not load tasks") }}</span>
			</template>
			<template #empty>
				<EmptyState icon="lucide-wallet" :title="__('Nothing billed or spent yet')" />
			</template>

			<div v-if="profitability && !nothing" class="flex h-full flex-col gap-2">
				<div class="min-h-0 flex-1">
					<DonutChart
						:data="rows"
						category="label"
						value="value"
						order="rows"
						:colors="colors"
						:format="money"
					>
						<template #center>
							<div class="flex flex-col items-center">
								<span
									class="text-base font-semibold"
									:class="profitability.margin < 0 ? 'text-ink-red-7' : 'text-ink-gray-9'"
								>
									{{ money(profitability.margin) }}
								</span>
								<span class="text-xs text-ink-gray-5">{{ margin_label }}</span>
							</div>
						</template>
					</DonutChart>
				</div>
				<p class="text-center text-sm text-ink-gray-5">
					{{ __("Billed") }}
					<span class="tabular-nums text-ink-gray-8">{{ money(profitability.billed) }}</span> ·
					{{ __("Cost") }}
					<span class="tabular-nums text-ink-gray-8">{{ money(profitability.cost) }}</span>
				</p>
			</div>
		</ChartContainer>
	</ChartCard>
</template>
