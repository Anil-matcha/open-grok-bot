const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export async function fetchBots() {
  try {
    const res = await fetch(`${API_BASE_URL}/bots`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('Backend server offline or unreachable:', err);
    return [];
  }
}

export async function createBot(botData) {
  const res = await fetch(`${API_BASE_URL}/bots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(botData),
  });
  if (!res.ok) throw new Error('Failed to create bot');
  return res.json();
}

export async function updateBot(botId, updates) {
  const res = await fetch(`${API_BASE_URL}/bots/${botId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('Failed to update bot');
  return res.json();
}

export async function deleteBot(botId) {
  const res = await fetch(`${API_BASE_URL}/bots/${botId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete bot');
  return res.json();
}

export async function fetchModels() {
  try {
    const res = await fetch(`${API_BASE_URL}/models`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('Models catalog API offline:', err);
    return [];
  }
}

export async function fetchChatHistory(threadId) {
  try {
    const res = await fetch(`${API_BASE_URL}/chat/history/${threadId}`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('Chat history API offline:', err);
    return [];
  }
}

export async function sendMessage(threadId, botId, text, model = 'grok-4-5', imageUrl = null) {
  try {
    const res = await fetch(`${API_BASE_URL}/chat/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        thread_id: threadId,
        bot_id: botId,
        user_text: text,
        model,
        image_url: imageUrl,
      }),
    });
    if (!res.ok) throw new Error('Failed to send message');
    return await res.json();
  } catch (err) {
    console.warn('Send message API call error:', err);
    return { status: 'error', detail: err.message };
  }
}

export async function uploadImage(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to upload image' }));
    throw new Error(err.detail || 'Failed to upload image');
  }
  return res.json();
}

export async function fetchConnectorCatalog() {
  try {
    const res = await fetch(`${API_BASE_URL}/connectors/catalog`);
    if (!res.ok) return { cards: [], source: 'curated', configured: false };
    return await res.json();
  } catch (err) {
    console.warn('Connector catalog offline:', err);
    return { cards: [], source: 'curated', configured: false };
  }
}

export async function fetchConnectionStatus(slugs = []) {
  if (!slugs.length) return { services: {} };
  try {
    const res = await fetch(`${API_BASE_URL}/connectors?services=${encodeURIComponent(slugs.join(','))}`);
    if (!res.ok) return { services: {} };
    return await res.json();
  } catch (err) {
    console.warn('Connection status offline:', err);
    return { services: {} };
  }
}

export async function authorizeConnector(slug) {
  const res = await fetch(`${API_BASE_URL}/connectors/${slug}/authorize`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to authorize ${slug}`);
  return res.json();
}

export async function disconnectConnector(slug) {
  const res = await fetch(`${API_BASE_URL}/connectors/${slug}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to disconnect ${slug}`);
  return res.json();
}

export async function fetchAuditEvents(limit = 100) {
  try {
    const res = await fetch(`${API_BASE_URL}/audit?limit=${encodeURIComponent(limit)}`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('Audit API offline:', err);
    return [];
  }
}

export function subscribeToChatStream(threadId, model, onEvent, onError) {
  const url = `${API_BASE_URL}/chat/stream/${threadId}?model=${encodeURIComponent(model)}`;
  let eventSource = null;

  try {
    eventSource = new EventSource(url);

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (onEvent) onEvent(data);
      } catch (err) {
        console.warn('Failed to parse SSE payload:', err);
      }
    };

    eventSource.onerror = (err) => {
      // Gracefully close stream when completed or disconnected
      if (eventSource) {
        eventSource.close();
      }
      if (onError && typeof onError === 'function') {
        onError(err);
      }
    };
  } catch (err) {
    console.warn('EventSource initialization error:', err);
    if (onError && typeof onError === 'function') {
      onError(err);
    }
  }

  return () => {
    if (eventSource) {
      eventSource.close();
    }
  };
}

export async function respondApproval(requestId, action) {
  const res = await fetch(`${API_BASE_URL}/approvals/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_id: requestId, action }),
  });
  if (!res.ok) throw new Error('Failed to respond approval');
  return res.json();
}

export async function fetchSettings() {
  try {
    const res = await fetch(`${API_BASE_URL}/settings`);
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn('Fetch settings API offline:', err);
    return null;
  }
}

export async function saveSettings(settingsData) {
  const res = await fetch(`${API_BASE_URL}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settingsData),
  });
  if (!res.ok) throw new Error('Failed to save settings');
  return res.json();
}
