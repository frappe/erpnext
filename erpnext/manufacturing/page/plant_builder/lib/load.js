import { ref } from "vue";

export function useLoad(fetch) {
	const failed = ref(false);

	async function load() {
		failed.value = false;
		try {
			await fetch();
		} catch {
			failed.value = true;
		}
	}

	return { failed, load };
}
