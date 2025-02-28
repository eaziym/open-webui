import { derived } from 'svelte/store';
import i18n from './index';
import { t as i18nextT } from 'i18next';

export const t = derived(i18n, () => {
	return (key: string, options?: any) => {
		return i18nextT(key, options);
	};
});
