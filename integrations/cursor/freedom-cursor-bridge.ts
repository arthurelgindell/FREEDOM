/**
 * FREEDOM Platform - Cursor IDE Integration Bridge
 * Production-ready integration layer for Cursor IDE
 * 
 * Features:
 * - REST API integration with FREEDOM Gateway
 * - WebSocket real-time communication
 * - Context-aware code assistance
 * - Knowledge base integration
 * - AI inference with fallback
 */

interface FreedomConfig {
  apiGateway: string;
  websocketUrl: string;
  apiKey: string;
  timeout: number;
  retries: number;
}

interface KnowledgeResult {
  id: string;
  technology_name: string;
  component_type: string;
  component_name: string;
  specification: any;
  similarity_score: number;
  confidence_score: number;
}

interface InferenceRequest {
  prompt: string;
  max_tokens?: number;
  temperature?: number;
  model?: string;
  context?: CodeContext;
}

interface InferenceResponse {
  id: string;
  model: string;
  content: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  correlation_id: string;
}

interface CodeContext {
  file_path: string;
  file_type: string;
  framework?: string;
  current_code?: string;
  cursor_position?: number;
  selected_text?: string;
}

interface HealthStatus {
  status: string;
  uptime_seconds: number;
  kb_service_status: string;
  mlx_service_status: string;
  timestamp: string;
}

export class FreedomCursorBridge {
  private config: FreedomConfig;
  private ws: WebSocket | null = null;
  private sessionId: string;
  private messageHandlers: Map<string, Function> = new Map();
  
  constructor(config: Partial<FreedomConfig> = {}) {
    this.config = {
      apiGateway: "http://localhost:8080",
      websocketUrl: "ws://localhost:8080",
      apiKey: "dev-key-change-in-production",
      timeout: 30000,
      retries: 3,
      ...config
    };
    this.sessionId = `cursor-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Initialize connection to FREEDOM Platform
   */
  async initialize(): Promise<boolean> {
    try {
      // Test API Gateway connectivity
      const health = await this.getSystemHealth();
      if (health.status !== 'healthy') {
        throw new Error(`FREEDOM Platform unhealthy: ${health.status}`);
      }

      // Initialize WebSocket connection
      await this.connectWebSocket();
      
      console.log('✅ FREEDOM Platform integration initialized');
      return true;
    } catch (error) {
      console.error('❌ Failed to initialize FREEDOM Platform:', error);
      return false;
    }
  }

  /**
   * Get system health status
   */
  async getSystemHealth(): Promise<HealthStatus> {
    const response = await this.apiRequest('GET', '/health');
    return response.json();
  }

  /**
   * Search knowledge base for relevant documentation
   */
  async searchKnowledge(query: string, context?: CodeContext): Promise<KnowledgeResult[]> {
    const requestBody = {
      query: this.enhanceQueryWithContext(query, context),
      limit: 10,
      similarity_threshold: 0.7
    };

    const response = await this.apiRequest('POST', '/kb/query', requestBody);
    const result = await response.json();
    return result.results || [];
  }

  /**
   * Generate code using AI inference
   */
  async generateCode(prompt: string, context?: CodeContext): Promise<string> {
    const requestBody: InferenceRequest = {
      prompt: this.buildContextualPrompt(prompt, context),
      max_tokens: 200,
      temperature: 0.7,
      context
    };

    const response = await this.apiRequest('POST', '/inference', requestBody);
    const result: InferenceResponse = await response.json();
    return result.content;
  }

  /**
   * Get documentation for specific technology
   */
  async getTechDocumentation(technology: string): Promise<any[]> {
    const response = await fetch(`http://localhost:8002/technologies`, {
      headers: { 'Content-Type': 'application/json' }
    });
    
    const technologies = await response.json();
    const tech = technologies.find((t: any) => 
      t.name.toLowerCase().includes(technology.toLowerCase())
    );
    
    if (tech) {
      const specsResponse = await fetch(`http://localhost:8002/technologies/${tech.id}/specifications`);
      return await specsResponse.json();
    }
    
    return [];
  }

  /**
   * Crawl web documentation for unknown topics
   */
  async crawlDocumentation(url: string, intent: string = "documentation"): Promise<any> {
    const response = await fetch('http://localhost:8003/crawl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, intent })
    });
    
    return await response.json();
  }

  /**
   * Get available AI models
   */
  async getAvailableModels(): Promise<string[]> {
    const response = await this.apiRequest('POST', '/inference/models');
    const result = await response.json();
    return result.models || [];
  }

  /**
   * WebSocket connection for real-time features
   */
  private async connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`${this.config.websocketUrl}/ws/${this.sessionId}`);
      
      this.ws.onopen = () => {
        console.log('✅ WebSocket connected to FREEDOM Platform');
        resolve();
      };
      
      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleWebSocketMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        setTimeout(() => this.connectWebSocket(), 5000); // Auto-reconnect
      };
    });
  }

  /**
   * Send real-time message via WebSocket
   */
  async sendRealtimeMessage(type: string, data: any): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type,
        data,
        correlation_id: `cursor-${Date.now()}`
      }));
    }
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleWebSocketMessage(message: any): void {
    const handler = this.messageHandlers.get(message.type);
    if (handler) {
      handler(message.data);
    } else {
      console.log('Unhandled WebSocket message:', message.type);
    }
  }

  /**
   * Register WebSocket message handler
   */
  onMessage(type: string, handler: Function): void {
    this.messageHandlers.set(type, handler);
  }

  /**
   * Build contextual prompt with file information
   */
  private buildContextualPrompt(prompt: string, context?: CodeContext): string {
    if (!context) return prompt;
    
    let contextualPrompt = prompt;
    
    if (context.framework) {
      contextualPrompt = `[Framework: ${context.framework}] ${prompt}`;
    }
    
    if (context.file_type) {
      contextualPrompt = `[Language: ${context.file_type}] ${contextualPrompt}`;
    }
    
    if (context.current_code) {
      contextualPrompt += `\n\nCurrent code context:\n\`\`\`${context.file_type}\n${context.current_code}\n\`\`\``;
    }
    
    return contextualPrompt;
  }

  /**
   * Enhance search query with context
   */
  private enhanceQueryWithContext(query: string, context?: CodeContext): string {
    if (!context) return query;
    
    const enhancements = [];
    if (context.framework) enhancements.push(context.framework);
    if (context.file_type) enhancements.push(context.file_type);
    
    return enhancements.length > 0 
      ? `${query} ${enhancements.join(' ')}`
      : query;
  }

  /**
   * Make authenticated API request to FREEDOM Gateway
   */
  private async apiRequest(method: string, endpoint: string, body?: any): Promise<Response> {
    const url = `${this.config.apiGateway}${endpoint}`;
    
    const options: RequestInit = {
      method,
      headers: {
        'X-API-Key': this.config.apiKey,
        'Content-Type': 'application/json',
        'X-Client': 'cursor-ide',
        'X-Session-ID': this.sessionId
      }
    };
    
    if (body) {
      options.body = JSON.stringify(body);
    }
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
      throw new Error(`FREEDOM API error: ${response.status} ${response.statusText}`);
    }
    
    return response;
  }

  /**
   * Cleanup resources
   */
  async dispose(): Promise<void> {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    console.log('FREEDOM Platform integration disposed');
  }
}

// Usage Example for Cursor Plugin
export async function createFreedomIntegration(): Promise<FreedomCursorBridge> {
  const bridge = new FreedomCursorBridge();
  
  // Set up event handlers
  bridge.onMessage('agent_response', (data) => {
    // Handle AI agent responses
    console.log('AI Response:', data);
  });
  
  bridge.onMessage('status_update', (data) => {
    // Handle system status updates
    console.log('Status Update:', data);
  });
  
  // Initialize connection
  await bridge.initialize();
  
  return bridge;
}

// Export for Cursor plugin use
export { FreedomCursorBridge, type CodeContext, type KnowledgeResult, type InferenceResponse };
