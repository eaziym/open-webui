<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { config } from '$lib/stores';
	import { goto } from '$app/navigation';
	import i18n from '$lib/i18n';

	const dispatch = createEventDispatcher();

	export let saveSettings: Function;

	let loading = false;

	const navigateToIntegrationsPage = () => {
		goto('/integrations');
	};

	// Define types for integration data
	interface Integration {
		name: string;
		icon: string;
		description: string;
		enabled: boolean;
	}

	// Helper function to type-safely access extended properties
	function getExtendedConfig() {
		const extConfig = $config as any;
		return {
			enableIntegrations: extConfig?.features?.enable_integrations,
			availableIntegrations: extConfig?.integrations?.available || {}
		};
	}

	// Helper function to get typed integrations
	function getIntegrations(): [string, Integration][] {
		const available = getExtendedConfig().availableIntegrations;
		return Object.entries(available).map(([key, value]) => {
			return [key, value as unknown as Integration];
		});
	}
</script>

<div class="flex flex-col h-full text-sm">
	<div class="overflow-y-auto scrollbar-hidden h-full pb-6">
		<div class="pr-1.5">
			<div class="mb-3">
				<div class="font-medium mb-1">{$i18n.t('Integrations')}</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
					{$i18n.t('Connect external services to enhance AI capabilities.')}
				</div>

				{#if getExtendedConfig().enableIntegrations}
					<button
						class="px-4 py-2 w-full text-left rounded-lg transition bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/30"
						on:click={navigateToIntegrationsPage}
					>
						{$i18n.t('Manage Integrations')}
					</button>
				{:else}
					<div class="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400">
						{$i18n.t('Integrations are not enabled on this server. Please contact your administrator.')}
					</div>
				{/if}
			</div>

			<div class="mb-3">
				<div class="font-medium mb-1">{$i18n.t('Available Integrations')}</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
					{$i18n.t('The following integrations are available on this server:')}
				</div>

				{#if Object.keys(getExtendedConfig().availableIntegrations).length > 0}
					{#each getIntegrations() as [key, integration]}
						{#if integration.enabled}
							<div class="flex items-center p-3 mb-2 rounded-lg border border-gray-200 dark:border-gray-700">
								<div class="flex-shrink-0 mr-3">
									<img 
										src={integration.icon} 
										alt={integration.name} 
										class="w-6 h-6"
									/>
								</div>
								<div class="flex-1">
									<div class="font-medium">{integration.name}</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">
										{integration.description}
									</div>
								</div>
							</div>
						{/if}
					{/each}
				{:else}
					<div class="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400">
						{$i18n.t('No integrations are available on this server.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div> 