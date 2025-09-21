#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createClient } from 'redis';

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

class RedisMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'redis-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.redisClient = null;
    this.setupHandlers();
  }

  async connectRedis() {
    if (!this.redisClient) {
      this.redisClient = createClient({ url: REDIS_URL });
      this.redisClient.on('error', err => console.error('Redis Client Error', err));
      await this.redisClient.connect();
    }
    return this.redisClient;
  }

  setupHandlers() {
    this.server.setRequestHandler('tools/list', async () => ({
      tools: [
        {
          name: 'redis_get',
          description: 'Get a value from Redis',
          inputSchema: {
            type: 'object',
            properties: {
              key: { type: 'string', description: 'Redis key' }
            },
            required: ['key']
          }
        },
        {
          name: 'redis_set',
          description: 'Set a value in Redis',
          inputSchema: {
            type: 'object',
            properties: {
              key: { type: 'string', description: 'Redis key' },
              value: { type: 'string', description: 'Value to set' },
              ttl: { type: 'number', description: 'TTL in seconds (optional)' }
            },
            required: ['key', 'value']
          }
        },
        {
          name: 'redis_keys',
          description: 'List keys matching a pattern',
          inputSchema: {
            type: 'object',
            properties: {
              pattern: { type: 'string', description: 'Pattern to match (default: *)' }
            }
          }
        },
        {
          name: 'redis_queue_status',
          description: 'Get status of Redis queues',
          inputSchema: {
            type: 'object',
            properties: {
              queue: { type: 'string', description: 'Queue name (optional)' }
            }
          }
        },
        {
          name: 'redis_flush',
          description: 'Flush Redis database',
          inputSchema: {
            type: 'object',
            properties: {
              confirm: { type: 'boolean', description: 'Confirm flush operation' }
            },
            required: ['confirm']
          }
        }
      ]
    }));

    this.server.setRequestHandler('tools/call', async (request) => {
      const { name, arguments: args } = request.params;
      const client = await this.connectRedis();

      try {
        switch (name) {
          case 'redis_get':
            const value = await client.get(args.key);
            return {
              content: [{
                type: 'text',
                text: value ? `Value: ${value}` : 'Key not found'
              }]
            };

          case 'redis_set':
            if (args.ttl) {
              await client.setEx(args.key, args.ttl, args.value);
            } else {
              await client.set(args.key, args.value);
            }
            return {
              content: [{
                type: 'text',
                text: `Set ${args.key} = ${args.value}${args.ttl ? ` (TTL: ${args.ttl}s)` : ''}`
              }]
            };

          case 'redis_keys':
            const keys = await client.keys(args.pattern || '*');
            return {
              content: [{
                type: 'text',
                text: keys.length ? `Keys: \n${keys.join('\n')}` : 'No keys found'
              }]
            };

          case 'redis_queue_status':
            const queues = args.queue ? [args.queue] : await client.keys('*:queue');
            const status = [];
            for (const queue of queues) {
              const len = await client.lLen(queue);
              status.push(`${queue}: ${len} items`);
            }
            return {
              content: [{
                type: 'text',
                text: status.length ? status.join('\n') : 'No queues found'
              }]
            };

          case 'redis_flush':
            if (args.confirm) {
              await client.flushDb();
              return {
                content: [{
                  type: 'text',
                  text: 'Redis database flushed'
                }]
              };
            }
            return {
              content: [{
                type: 'text',
                text: 'Flush cancelled - confirm required'
              }]
            };

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

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Redis MCP Server running');
  }
}

const server = new RedisMCPServer();
server.run().catch(console.error);