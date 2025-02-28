<script lang="ts">
  import { onMount } from 'svelte';
  import NotionIntegration from '$lib/components/Integrations/NotionIntegration.svelte';
  import i18n from '$lib/i18n';
  import Spinner from '$lib/components/common/Spinner.svelte';
  import Banner from '$lib/components/common/Banner.svelte';
  import { WEBUI_API_BASE_URL } from '$lib/constants';

  interface IntegrationDetails {
    name: string;
    description: string;
    icon: string;
    enabled: boolean;
  }

  interface IntegrationsData {
    available: Record<string, IntegrationDetails>;
    connected: Array<{
      id: string;
      integration_type: string;
      workspace_name?: string;
      workspace_icon?: string;
      active: boolean;
      created_at: string;
      updated_at: string;
    }>;
  }

  let loading = true;
  let error: string | null = null;
  let integrations: IntegrationsData = {
    available: {},
    connected: []
  };

  onMount(() => {
    fetchIntegrations();
  });

  async function fetchIntegrations() {
    try {
      loading = true;
      
      // Get the authentication token from localStorage
      const token = localStorage.getItem('token');
      
      if (!token) {
        throw new Error('You need to be logged in to access integrations');
      }
      
      const response = await fetch(`/api/v1/integrations/`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      integrations = data;
      error = null;
    } catch (err: unknown) {
      console.error('Error fetching integrations:', err);
      if (err instanceof Error) {
        error = err.message;
      } else {
        error = 'Failed to fetch integrations';
      }
    } finally {
      loading = false;
    }
  }

  $: hasAvailableIntegrations = Object.keys(integrations.available).length > 0;
</script>

<div class="container mx-auto py-8 px-4">
  <h1 class="text-2xl font-bold mb-6">{$i18n.t('Integrations')}</h1>
  
  {#if loading}
    <div class="flex justify-center items-center h-[50vh]">
      <Spinner className="size-10" />
    </div>
  {:else if error}
    <div class="mb-6">
      <Banner banner={{ 
        id: 'error-banner',
        type: 'error',
        content: error,
        dismissible: true,
        timestamp: Math.floor(Date.now() / 1000)
      }} />
    </div>
  {:else if !hasAvailableIntegrations}
    <div class="mb-6">
      <Banner banner={{ 
        id: 'info-banner',
        type: 'info',
        content: $i18n.t('No integrations are currently available. Please check your server configuration.'),
        dismissible: true,
        timestamp: Math.floor(Date.now() / 1000)
      }} />
    </div>
  {:else}
    <p class="mb-6">
      {$i18n.t('Connect your accounts to enhance AI capabilities with external data and services.')}
    </p>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      {#if integrations.available.notion}
        <div>
          <NotionIntegration />
        </div>
      {/if}
      
      <!-- Add more integrations here as they become available -->
    </div>
  {/if}
</div> 