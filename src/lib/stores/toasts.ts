import { writable } from 'svelte/store';

interface Toast {
	id: string;
	type: 'success' | 'error' | 'info' | 'warning';
	message: string;
	timeout?: number;
}

const createToastStore = () => {
	const { subscribe, update } = writable<Toast[]>([]);

	const addToast = (toast: Omit<Toast, 'id'>) => {
		const id = Math.random().toString(36).substring(2, 9);
		update((toasts) => [...toasts, { ...toast, id }]);

		if (toast.timeout !== 0) {
			setTimeout(() => {
				removeToast(id);
			}, toast.timeout || 3000);
		}

		return id;
	};

	const removeToast = (id: string) => {
		update((toasts) => toasts.filter((t) => t.id !== id));
	};

	const success = (message: string, timeout?: number) => {
		return addToast({ type: 'success', message, timeout });
	};

	const error = (message: string, timeout?: number) => {
		return addToast({ type: 'error', message, timeout });
	};

	const info = (message: string, timeout?: number) => {
		return addToast({ type: 'info', message, timeout });
	};

	const warning = (message: string, timeout?: number) => {
		return addToast({ type: 'warning', message, timeout });
	};

	return {
		subscribe,
		success,
		error,
		info,
		warning,
		remove: removeToast
	};
};

const toast = createToastStore();
export default toast;
