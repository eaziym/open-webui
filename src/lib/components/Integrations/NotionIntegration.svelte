<script lang="ts">
  import { onMount } from 'svelte';
  import i18n from '$lib/i18n';
  import toast from '$lib/stores/toasts';
  import Button from '$lib/components/common/Button.svelte';
  import Card from '$lib/components/common/Card.svelte';
  import Spinner from '$lib/components/common/Spinner.svelte';

  interface Integration {
    id: string;
    integration_type: string;
    workspace_name?: string;
    workspace_icon?: string;
    active: boolean;
    created_at: string;
    updated_at: string;
  }

  interface Database {
    id: string;
    title: string;
    description?: string;
    url?: string;
    last_edited_time?: string;
    properties?: Record<string, any>;
  }

  let loading = false;
  let connected = false;
  let integration: Integration | null = null;
  let databases: Database[] = [];
  let databasesLoading = false;

  onMount(() => {
    fetchIntegrationStatus();
  });

  // Fetch integration status
  async function fetchIntegrationStatus() {
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
      
      const data = await response.json();
      
      // Check if Notion is connected AND active
      const notionIntegration = data.connected.find((i: any) => i.integration_type === 'notion' && i.active === true);
      if (notionIntegration) {
        connected = true;
        integration = notionIntegration;
        fetchDatabases();
      } else {
        connected = false;
        integration = null;
      }
    } catch (error) {
      console.error('Error fetching integration status:', error);
      toast.error('Failed to fetch integration status');
    } finally {
      loading = false;
    }
  }

  // Connect to Notion
  async function connectNotion() {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Authentication token not found');
      }
      
      loading = true;
      
      // Use the notion login endpoint
      console.log('Attempting to connect to Notion via login endpoint...');
      const response = await fetch('/api/v1/integrations/notion/login', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Login endpoint failed:', response.status, errorText);
        throw new Error(`Failed to connect to Notion: ${response.status} - ${errorText || 'No response from server'}`);
      }
      
      const data = await response.json();
      console.log('Login endpoint returned data:', data);
      
      // Open Notion authorization page in a new window
      const authUrl = data.auth_url || data.authorization_url;
      if (!authUrl) {
        console.error('No authorization URL found in response:', data);
        throw new Error('No authorization URL found in the server response');
      }
      
      console.log('Opening Notion authorization URL:', authUrl);
      window.location.href = authUrl;
      
      // We don't need the polling logic as the callback will redirect back to the app
      
    } catch (error) {
      console.error('Error connecting to Notion:', error);
      toast.error(`Failed to connect to Notion: ${error instanceof Error ? error.message : 'Unknown error'}`);
      loading = false;
    }
  }

  // Disconnect from Notion
  async function disconnectNotion() {
    try {
      if (!integration) return;
      
      // Get the authentication token from localStorage
      const token = localStorage.getItem('token');
      
      if (!token) {
        throw new Error('You need to be logged in to disconnect from Notion');
      }
      
      loading = true;
      
      // Use the notion-specific disconnect endpoint
      console.log('Attempting to disconnect from Notion via disconnect endpoint...');
      const response = await fetch('/api/v1/integrations/notion/disconnect', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Disconnect endpoint failed:', response.status, errorText);
        throw new Error(`Failed to disconnect: ${response.status} - ${errorText || 'No response from server'}`);
      }
      
      connected = false;
      integration = null;
      databases = [];
      
      toast.success('Disconnected from Notion successfully');
    } catch (error) {
      console.error('Error disconnecting from Notion:', error);
      toast.error(`Failed to disconnect from Notion: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      loading = false;
    }
  }

  // Fetch Notion databases
  async function fetchDatabases() {
    if (!connected) return;
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Authentication token not found');
      }
      
      databasesLoading = true;
      
      // Actually fetch databases from the API
      console.log('Fetching Notion databases from API...');
      // Use the direct databases endpoint instead of the execute endpoint
      const response = await fetch('/api/v1/integrations/notion/databases', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch databases: ${response.status} - ${errorText}`);
      }
      
      const data = await response.json();
      console.log('Database response:', data);
      
      if (data && Array.isArray(data)) {
        databases = data.map((db: any) => ({
          id: db.id,
          title: db.title || 'Untitled Database',
          url: db.url,
          last_edited_time: db.last_edited_time,
          properties: db.properties || {}
        }));
        
        console.log('Fetched databases:', databases);
        
        if (databases.length === 0) {
          toast.info('No databases found in your Notion workspace.');
        }
      } else {
        console.warn('Invalid database response format:', data);
        toast.warning('Received unexpected response format from server.');
        databases = [];
      }
    } catch (error) {
      console.error('Error fetching Notion databases:', error);
      toast.error(`Error fetching Notion databases: ${error instanceof Error ? error.message : 'Unknown error'}`);
      databases = [];
    } finally {
      databasesLoading = false;
    }
  }
</script>

<Card class="p-4 w-full">
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center">
      <h3 class="text-lg font-semibold">{$i18n.t('Notion Integration')}</h3>
      {#if loading}
        <Spinner className="size-5" />
      {:else if connected}
        <Button 
          color="red" 
          size="sm" 
          on:click={disconnectNotion}
        >
          <i class="fas fa-trash mr-2"></i> {$i18n.t('Disconnect')}
        </Button>
      {:else}
        <Button 
          color="blue" 
          size="sm" 
          on:click={connectNotion}
        >
          <i class="fas fa-plus mr-2"></i> {$i18n.t('Connect')}
        </Button>
      {/if}
    </div>

    {#if connected && integration}
      <div>
        <p class="font-bold">{$i18n.t('Connected to')}:</p>
        <p>{integration.workspace_name || 'Notion Workspace'}</p>
      </div>
    {/if}

    {#if connected}
      <div>
        <div class="flex justify-between items-center mb-2">
          <h4 class="text-md font-semibold">{$i18n.t('Databases')}</h4>
          <Button 
            size="xs" 
            on:click={fetchDatabases} 
            loading={databasesLoading}
          >
            {$i18n.t('Refresh')}
          </Button>
        </div>
        
        {#if databasesLoading}
          <div class="flex justify-center py-4">
            <Spinner className="size-5" />
          </div>
        {:else if databases.length > 0}
          <div class="flex flex-col gap-2">
            {#each databases as db}
              <Card class="p-2" variant="outline">
                <div class="flex items-center gap-2">
                  <i class="fas fa-database"></i>
                  <p class="font-medium">{db.title}</p>
                </div>
                {#if db.url}
                  <a href={db.url} target="_blank" rel="noopener noreferrer" class="text-blue-500 text-sm">
                    {$i18n.t('Open in Notion')}
                  </a>
                {/if}
              </Card>
            {/each}
          </div>
        {:else}
          <p class="text-gray-500">{$i18n.t('No databases found')}</p>
        {/if}
      </div>
    {/if}

    {#if !connected && !loading}
      <p class="text-gray-500">
        {$i18n.t('Connect your Notion account to access your databases and pages from the AI.')}
      </p>
    {/if}
  </div>
</Card> 