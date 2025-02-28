/**
 * Utility functions for making API requests
 */

/**
 * Make a request to the API
 * @param {string} url - The API endpoint to call
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} - The API response
 */
export async function fetchAPI(url, options = {}) {
	const defaultOptions = {
		headers: {
			'Content-Type': 'application/json'
		}
	};

	const mergedOptions = {
		...defaultOptions,
		...options,
		headers: {
			...defaultOptions.headers,
			...options.headers
		}
	};

	try {
		const response = await fetch(url, mergedOptions);

		// Handle non-JSON responses
		const contentType = response.headers.get('content-type');
		if (contentType && contentType.includes('application/json')) {
			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || data.message || `API error: ${response.status}`);
			}

			return data;
		} else {
			if (!response.ok) {
				const text = await response.text();
				throw new Error(text || `API error: ${response.status}`);
			}

			return await response.text();
		}
	} catch (error) {
		console.error('API request failed:', error);
		throw error;
	}
}
