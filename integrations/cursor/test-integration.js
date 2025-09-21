/**
 * FREEDOM Platform - Integration Test Script
 * Tests the bridge functionality with live FREEDOM services
 */

const axios = require('axios');
const WebSocket = require('ws');

class FreedomCursorBridge {
    constructor(config = {}) {
        this.config = {
            apiGateway: "http://localhost:8080",
            websocketUrl: "ws://localhost:8080",
            apiKey: "dev-key-change-in-production",
            timeout: 30000,
            retries: 3,
            ...config
        };
        this.sessionId = `cursor-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        this.ws = null;
    }

    async initialize() {
        try {
            console.log('🔗 Initializing FREEDOM Platform connection...');
            
            // Test API Gateway connectivity
            const health = await this.getSystemHealth();
            if (health.status !== 'healthy') {
                throw new Error(`FREEDOM Platform unhealthy: ${health.status}`);
            }

            console.log('✅ API Gateway connected successfully');
            return true;
        } catch (error) {
            console.error('❌ Failed to initialize FREEDOM Platform:', error.message);
            return false;
        }
    }

    async getSystemHealth() {
        const response = await axios.get(`${this.config.apiGateway}/health`, {
            headers: {
                'X-API-Key': this.config.apiKey,
                'X-Client': 'cursor-test',
                'X-Session-ID': this.sessionId
            },
            timeout: this.config.timeout
        });
        return response.data;
    }

    async searchKnowledge(query, context = null) {
        const requestBody = {
            query: this.enhanceQueryWithContext(query, context),
            limit: 10,
            similarity_threshold: 0.7
        };

        const response = await axios.post(`${this.config.apiGateway}/kb/query`, requestBody, {
            headers: {
                'X-API-Key': this.config.apiKey,
                'Content-Type': 'application/json',
                'X-Client': 'cursor-test',
                'X-Session-ID': this.sessionId
            },
            timeout: this.config.timeout
        });

        return response.data.results || [];
    }

    async generateCode(prompt, context = null) {
        const requestBody = {
            prompt: this.buildContextualPrompt(prompt, context),
            max_tokens: 200,
            temperature: 0.7,
            context
        };

        const response = await axios.post(`${this.config.apiGateway}/inference`, requestBody, {
            headers: {
                'X-API-Key': this.config.apiKey,
                'Content-Type': 'application/json',
                'X-Client': 'cursor-test',
                'X-Session-ID': this.sessionId
            },
            timeout: this.config.timeout
        });

        return response.data.content;
    }

    async getAvailableModels() {
        const response = await axios.post(`${this.config.apiGateway}/inference/models`, {}, {
            headers: {
                'X-API-Key': this.config.apiKey,
                'Content-Type': 'application/json',
                'X-Client': 'cursor-test',
                'X-Session-ID': this.sessionId
            },
            timeout: this.config.timeout
        });

        return response.data.models || [];
    }

    async getTechDocumentation(technology) {
        try {
            const response = await axios.get(`http://localhost:8002/technologies`, {
                headers: { 'Content-Type': 'application/json' },
                timeout: this.config.timeout
            });
            
            const technologies = response.data;
            const tech = technologies.find(t => 
                t.name.toLowerCase().includes(technology.toLowerCase())
            );
            
            if (tech) {
                const specsResponse = await axios.get(`http://localhost:8002/technologies/${tech.id}/specifications`);
                return specsResponse.data;
            }
            
            return [];
        } catch (error) {
            console.log(`TechKnowledge service not available: ${error.message}`);
            return [];
        }
    }

    buildContextualPrompt(prompt, context) {
        if (!context) return prompt;
        
        let contextualPrompt = prompt;
        
        if (context.framework) {
            contextualPrompt = `[Framework: ${context.framework}] ${prompt}`;
        }
        
        if (context.file_type) {
            contextualPrompt = `[Language: ${context.file_type}] ${contextualPrompt}`;
        }
        
        return contextualPrompt;
    }

    enhanceQueryWithContext(query, context) {
        if (!context) return query;
        
        const enhancements = [];
        if (context.framework) enhancements.push(context.framework);
        if (context.file_type) enhancements.push(context.file_type);
        
        return enhancements.length > 0 
            ? `${query} ${enhancements.join(' ')}`
            : query;
    }

    async dispose() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        console.log('FREEDOM Platform integration disposed');
    }
}

// Test Suite
async function runIntegrationTests() {
    console.log('🚀 Starting FREEDOM Platform Integration Tests');
    console.log('=' .repeat(50));

    let passed = 0;
    let failed = 0;

    try {
        const bridge = new FreedomCursorBridge();
        console.log('✅ Bridge created successfully');
        passed++;

        // Test 1: Initialize connection
        console.log('\n🔗 Test 1: Initialize FREEDOM Platform connection');
        const connected = await bridge.initialize();
        if (connected) {
            console.log('✅ FREEDOM Platform connection successful');
            passed++;
        } else {
            console.log('❌ FREEDOM Platform connection failed');
            failed++;
            return;
        }

        // Test 2: Health check
        console.log('\n🏥 Test 2: System health check');
        try {
            const health = await bridge.getSystemHealth();
            console.log(`✅ Health check passed: ${health.status}`);
            console.log(`   - Uptime: ${Math.round(health.uptime_seconds / 60)} minutes`);
            console.log(`   - KB Service: ${health.kb_service_status}`);
            console.log(`   - MLX Service: ${health.mlx_service_status}`);
            passed++;
        } catch (error) {
            console.log(`❌ Health check failed: ${error.message}`);
            failed++;
        }

        // Test 3: Knowledge search
        console.log('\n📚 Test 3: Knowledge base search');
        try {
            const knowledgeResults = await bridge.searchKnowledge('React hooks');
            console.log(`✅ Knowledge search successful: ${knowledgeResults.length} results`);
            if (knowledgeResults.length > 0) {
                console.log(`   - Top result: ${knowledgeResults[0].component_name} (${knowledgeResults[0].technology_name})`);
                console.log(`   - Confidence: ${(knowledgeResults[0].confidence_score * 100).toFixed(1)}%`);
            }
            passed++;
        } catch (error) {
            console.log(`❌ Knowledge search failed: ${error.message}`);
            failed++;
        }

        // Test 4: AI code generation
        console.log('\n🤖 Test 4: AI code generation');
        try {
            const context = {
                file_type: 'typescript',
                framework: 'react'
            };
            const generatedCode = await bridge.generateCode('Write a simple React component', context);
            console.log('✅ AI code generation successful');
            console.log(`   - Generated: ${generatedCode.substring(0, 100)}...`);
            passed++;
        } catch (error) {
            console.log(`❌ AI code generation failed: ${error.message}`);
            failed++;
        }

        // Test 5: Available models
        console.log('\n🎯 Test 5: Available AI models');
        try {
            const models = await bridge.getAvailableModels();
            console.log(`✅ Model list retrieved: ${models.length} models`);
            models.forEach(model => console.log(`   - ${model}`));
            passed++;
        } catch (error) {
            console.log(`❌ Model list failed: ${error.message}`);
            failed++;
        }

        // Test 6: Tech documentation (optional)
        console.log('\n📖 Test 6: Technical documentation');
        try {
            const docs = await bridge.getTechDocumentation('React');
            console.log(`✅ Tech documentation retrieved: ${docs.length} specifications`);
            passed++;
        } catch (error) {
            console.log(`⚠️  Tech documentation not available: ${error.message}`);
            // Don't count as failure since this service might not be running
        }

        // Cleanup
        await bridge.dispose();

    } catch (error) {
        console.error(`❌ Critical test failure: ${error.message}`);
        failed++;
    }

    // Results summary
    console.log('\n' + '=' .repeat(50));
    console.log('🎯 INTEGRATION TEST RESULTS');
    console.log('=' .repeat(50));
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);
    console.log(`📊 Success Rate: ${((passed / (passed + failed)) * 100).toFixed(1)}%`);

    if (failed === 0) {
        console.log('\n🎉 ALL TESTS PASSED - FREEDOM Platform ready for Cursor integration!');
        return true;
    } else {
        console.log('\n⚠️  Some tests failed - check FREEDOM Platform services');
        return false;
    }
}

// Run tests if called directly
if (require.main === module) {
    runIntegrationTests().then(success => {
        process.exit(success ? 0 : 1);
    }).catch(error => {
        console.error('Test runner failed:', error);
        process.exit(1);
    });
}

module.exports = { FreedomCursorBridge, runIntegrationTests };
