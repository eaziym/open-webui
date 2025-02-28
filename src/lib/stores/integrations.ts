import { writable } from 'svelte/store';
import { fetchAPI } from '$lib/utils/api';

// Define an interface for the Notion integration data
export interface NotionIntegration {
	id: string;
	integration_type: string;
	workspace_name: string;
	workspace_icon?: string;
	active: boolean;
	created_at: string;
	updated_at: string;
}

export const notionIntegration = writable<NotionIntegration | null>(null);
export const integrationsLoading = writable<boolean>(false);

/**
 * Fetch the user's active Notion integration
 * @returns {Promise<NotionIntegration | null>} The Notion integration data
 */
export async function fetchNotionIntegration(): Promise<NotionIntegration | null> {
	integrationsLoading.set(true);

	try {
		const response = await fetchAPI('/api/v1/integrations/notion/status');

		if (response.integration) {
			notionIntegration.set(response.integration);
			console.log('Notion integration loaded:', response.integration);
		} else {
			notionIntegration.set(null);
		}

		return response.integration;
	} catch (error) {
		console.error('Error fetching Notion integration:', error);
		notionIntegration.set(null);
		return null;
	} finally {
		integrationsLoading.set(false);
	}
}

/**
 * Disconnect the Notion integration
 * @returns {Promise<boolean>} Success status
 */
export async function disconnectNotionIntegration(): Promise<boolean> {
	integrationsLoading.set(true);

	try {
		await fetchAPI('/api/v1/integrations/notion/disconnect', {
			method: 'POST'
		});

		notionIntegration.set(null);
		return true;
	} catch (error) {
		console.error('Error disconnecting Notion integration:', error);
		return false;
	} finally {
		integrationsLoading.set(false);
	}
}

/**
 * Login to Notion
 */
export function loginToNotion(): void {
	window.location.href = '/api/v1/integrations/notion/login';
}

/**
 * Execute a Notion action
 * @param {string} action - The action to execute
 * @param {Record<string, unknown>} params - The parameters for the action
 * @returns {Promise<unknown>} The result of the action
 */
export async function executeNotionAction(
	action: string,
	params: Record<string, unknown> = {}
): Promise<unknown> {
	try {
		const response = await fetchAPI('/api/v1/integrations/notion/execute', {
			method: 'POST',
			body: JSON.stringify({
				action,
				params
			})
		});

		return response;
	} catch (error) {
		console.error('Error executing Notion action:', error);
		throw error;
	}
}
