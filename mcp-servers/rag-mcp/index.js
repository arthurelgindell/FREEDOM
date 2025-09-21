#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import axios from 'axios';

const RAG_API_URL = process.env.RAG_API_URL || 'http://localhost:5003';

class RAGMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'rag-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.axiosClient = axios.create({
      baseURL: RAG_API_URL,
      timeout: 30000,
    });

    this.setupHandlers();
  }

  setupHandlers() {
    this.server.setRequestHandler('tools/list', async () => ({
      tools: [
        {
          name: 'rag_query',
          description: 'Semantic search across technical documentation with context building',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'Natural language question or search query'
              },
              top_k: {
                type: 'number',
                description: 'Number of chunks to retrieve (default: 10)',
                default: 10
              },
              technology: {
                type: 'string',
                description: 'Filter by technology (e.g., cursor, lmstudio, anthropic)'
              },
              use_cache: {
                type: 'boolean',
                description: 'Use cached results if available (default: true)',
                default: true
              }
            },
            required: ['query']
          }
        },
        {
          name: 'rag_search',
          description: 'Simple keyword search without semantic processing',
          inputSchema: {
            type: 'object',
            properties: {
              q: {
                type: 'string',
                description: 'Search keywords'
              },
              technology: {
                type: 'string',
                description: 'Filter by technology'
              },
              component_type: {
                type: 'string',
                description: 'Filter by component type'
              },
              limit: {
                type: 'number',
                description: 'Maximum results (default: 10)',
                default: 10
              }
            },
            required: ['q']
          }
        },
        {
          name: 'rag_stats',
          description: 'Get RAG system statistics and health status',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        },
        {
          name: 'rag_explore',
          description: 'Browse knowledge base by technology or component',
          inputSchema: {
            type: 'object',
            properties: {
              technology: {
                type: 'string',
                description: 'Technology to explore'
              },
              component_type: {
                type: 'string',
                description: 'Component type to filter'
              },
              limit: {
                type: 'number',
                description: 'Maximum results (default: 20)',
                default: 20
              }
            }
          }
        },
        {
          name: 'rag_explain',
          description: 'Get detailed explanation of a technical concept',
          inputSchema: {
            type: 'object',
            properties: {
              concept: {
                type: 'string',
                description: 'Technical concept to explain'
              },
              technology: {
                type: 'string',
                description: 'Technology context (optional)'
              },
              detail_level: {
                type: 'string',
                description: 'Level of detail: brief, standard, comprehensive',
                enum: ['brief', 'standard', 'comprehensive'],
                default: 'standard'
              }
            },
            required: ['concept']
          }
        },
        {
          name: 'rag_compare',
          description: 'Compare features across different technologies',
          inputSchema: {
            type: 'object',
            properties: {
              feature: {
                type: 'string',
                description: 'Feature or concept to compare'
              },
              technologies: {
                type: 'array',
                items: { type: 'string' },
                description: 'List of technologies to compare'
              }
            },
            required: ['feature']
          }
        }
      ]
    }));

    this.server.setRequestHandler('tools/call', async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'rag_query':
            return await this.ragQuery(args);

          case 'rag_search':
            return await this.ragSearch(args);

          case 'rag_stats':
            return await this.ragStats();

          case 'rag_explore':
            return await this.ragExplore(args);

          case 'rag_explain':
            return await this.ragExplain(args);

          case 'rag_compare':
            return await this.ragCompare(args);

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [{
            type: 'text',
            text: `Error: ${error.message}`
          }]
        };
      }
    });
  }

  async ragQuery(args) {
    try {
      const response = await this.axiosClient.post('/query', {
        query: args.query,
        top_k: args.top_k || 10,
        rerank: true,
        hybrid_alpha: 0.7,
        filters: args.technology ? { technology: args.technology } : {}
      });

      const data = response.data;

      // Format the response for Claude
      let result = `## RAG Query Results\n\n`;
      result += `**Query**: ${data.query}\n\n`;
      result += `### Context\n${data.context}\n\n`;

      if (data.chunks && data.chunks.length > 0) {
        result += `### Source Chunks (${data.chunks.length} found)\n\n`;
        data.chunks.forEach((chunk, idx) => {
          result += `**${idx + 1}. ${chunk.technology || 'Unknown'} - ${chunk.component}**\n`;
          result += `${chunk.text}\n`;
          result += `*Score: ${chunk.score?.toFixed(3) || 'N/A'}*\n\n`;
        });
      }

      result += `\n---\n*Response time: ${data.retrieval_time_ms}ms`;
      result += data.cached ? ' (cached)' : ' (fresh)*';

      return {
        content: [{
          type: 'text',
          text: result
        }]
      };
    } catch (error) {
      throw new Error(`RAG query failed: ${error.message}`);
    }
  }

  async ragSearch(args) {
    try {
      const params = new URLSearchParams({
        q: args.q,
        limit: args.limit || 10
      });

      if (args.technology) params.append('technology', args.technology);
      if (args.component_type) params.append('component_type', args.component_type);

      const response = await this.axiosClient.get(`/search?${params}`);
      const data = response.data;

      let result = `## Search Results for "${args.q}"\n\n`;

      if (data.chunks && data.chunks.length > 0) {
        result += `Found ${data.chunks.length} results:\n\n`;
        data.chunks.forEach((chunk, idx) => {
          result += `**${idx + 1}. ${chunk.technology || 'Unknown'} - ${chunk.component}**\n`;
          result += `${chunk.text}\n\n`;
        });
      } else {
        result += 'No results found.';
      }

      return {
        content: [{
          type: 'text',
          text: result
        }]
      };
    } catch (error) {
      throw new Error(`Search failed: ${error.message}`);
    }
  }

  async ragStats() {
    try {
      const [healthResp, statsResp] = await Promise.all([
        this.axiosClient.get('/health'),
        this.axiosClient.get('/stats')
      ]);

      const health = healthResp.data;
      const stats = statsResp.data;

      let result = `## RAG System Status\n\n`;
      result += `### Health\n`;
      result += `- Status: ${health.status}\n`;
      result += `- Database: ${health.database}\n`;
      result += `- Total Chunks: ${health.chunks_count}\n\n`;

      result += `### Statistics\n`;
      result += `- Total Documents: ${stats.total_chunks}\n\n`;

      if (stats.technology_distribution) {
        result += `### Technology Distribution\n`;
        stats.technology_distribution.forEach(tech => {
          result += `- ${tech.technology}: ${tech.count} chunks\n`;
        });
        result += '\n';
      }

      if (stats.cache) {
        result += `### Cache Statistics\n`;
        result += `- Cached Entries: ${stats.cache.entries}\n`;
        result += `- Total Cache Hits: ${stats.cache.total_hits}\n`;
      }

      return {
        content: [{
          type: 'text',
          text: result
        }]
      };
    } catch (error) {
      throw new Error(`Stats retrieval failed: ${error.message}`);
    }
  }

  async ragExplore(args) {
    try {
      // Use search endpoint with filters
      const params = new URLSearchParams({
        q: '*',  // Wildcard to get all
        limit: args.limit || 20
      });

      if (args.technology) params.append('technology', args.technology);
      if (args.component_type) params.append('component_type', args.component_type);

      const response = await this.axiosClient.get(`/search?${params}`);
      const data = response.data;

      let result = `## Knowledge Base Explorer\n\n`;

      if (args.technology) {
        result += `### Technology: ${args.technology}\n\n`;
      }
      if (args.component_type) {
        result += `### Component Type: ${args.component_type}\n\n`;
      }

      if (data.chunks && data.chunks.length > 0) {
        result += `Found ${data.chunks.length} documents:\n\n`;
        data.chunks.forEach((chunk, idx) => {
          result += `${idx + 1}. **${chunk.component}** (${chunk.technology})\n`;
          result += `   ${chunk.text.substring(0, 150)}...\n\n`;
        });
      } else {
        result += 'No documents found with these filters.';
      }

      return {
        content: [{
          type: 'text',
          text: result
        }]
      };
    } catch (error) {
      throw new Error(`Explore failed: ${error.message}`);
    }
  }

  async ragExplain(args) {
    try {
      // Construct a detailed query for explanation
      let query = `Explain ${args.concept}`;
      if (args.technology) {
        query += ` in the context of ${args.technology}`;
      }

      // Adjust top_k based on detail level
      const topK = args.detail_level === 'comprehensive' ? 15 :
                   args.detail_level === 'brief' ? 5 : 10;

      const response = await this.axiosClient.post('/query', {
        query: query,
        top_k: topK,
        rerank: true,
        filters: args.technology ? { technology: args.technology } : {}
      });

      const data = response.data;

      let result = `## Explanation: ${args.concept}\n\n`;
      if (args.technology) {
        result += `*Context: ${args.technology}*\n\n`;
      }

      result += `### Summary\n${data.context}\n\n`;

      if (args.detail_level !== 'brief' && data.chunks && data.chunks.length > 0) {
        result += `### Detailed Information\n\n`;
        data.chunks.slice(0, args.detail_level === 'comprehensive' ? 10 : 3).forEach(chunk => {
          result += `**From ${chunk.technology} - ${chunk.component}:**\n`;
          result += `${chunk.text}\n\n`;
        });
      }

      return {
        content: [{
          type: 'text',
          text: result
        }]
      };
    } catch (error) {
      throw new Error(`Explain failed: ${error.message}`);
    }
  }

  async ragCompare(args) {
    try {
      const technologies = args.technologies || ['cursor', 'lmstudio', 'anthropic'];
      const comparisons = [];

      // Query for each technology
      for (const tech of technologies) {
        const response = await this.axiosClient.post('/query', {
          query: `${args.feature} in ${tech}`,
          top_k: 5,
          rerank: true,
          filters: { technology: tech }
        });

        comparisons.push({
          technology: tech,
          data: response.data
        });
      }

      let result = `## Comparison: ${args.feature}\n\n`;
      result += `### Technologies Compared\n`;
      technologies.forEach(tech => result += `- ${tech}\n`);
      result += '\n';

      // Present comparison
      comparisons.forEach(comp => {
        result += `### ${comp.technology}\n`;
        if (comp.data.context) {
          result += comp.data.context.substring(0, 500);
          if (comp.data.context.length > 500) result += '...';
          result += '\n\n';
        } else {
          result += 'No information found.\n\n';
        }
      });

      return {
        content: [{
          type: 'text',
          text: result
        }]
      };
    } catch (error) {
      throw new Error(`Compare failed: ${error.message}`);
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('RAG MCP Server running');
  }
}

const server = new RAGMCPServer();
server.run().catch(console.error);