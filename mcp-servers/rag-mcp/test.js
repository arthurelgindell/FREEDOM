#!/usr/bin/env node
// Test script for RAG MCP Server
import axios from 'axios';

const RAG_API_URL = 'http://localhost:5003';

async function testRAGAPI() {
  console.log('Testing RAG API connectivity...\n');

  try {
    // Test health endpoint
    console.log('1. Testing /health endpoint:');
    const healthResp = await axios.get(`${RAG_API_URL}/health`);
    console.log('   ✅ Health:', healthResp.data.status);
    console.log('   ✅ Database:', healthResp.data.database);
    console.log('   ✅ Chunks:', healthResp.data.chunks_count);

    // Test stats endpoint
    console.log('\n2. Testing /stats endpoint:');
    const statsResp = await axios.get(`${RAG_API_URL}/stats`);
    console.log('   ✅ Total chunks:', statsResp.data.total_chunks);
    console.log('   ✅ Technologies:', statsResp.data.technology_distribution?.length || 0);

    // Test query endpoint
    console.log('\n3. Testing /query endpoint:');
    const queryResp = await axios.post(`${RAG_API_URL}/query`, {
      query: 'What is cursor?',
      top_k: 3
    });
    console.log('   ✅ Query executed successfully');
    console.log('   ✅ Retrieved', queryResp.data.chunks?.length || 0, 'chunks');
    console.log('   ✅ Response time:', queryResp.data.retrieval_time_ms, 'ms');

    console.log('\n✅ All RAG API tests passed!');
    console.log('\nRAG MCP is ready to use. Restart Claude Desktop to activate it.');

  } catch (error) {
    console.error('\n❌ RAG API test failed:');
    console.error('   Error:', error.message);
    console.error('\n⚠️  Make sure the RAG API is running:');
    console.error('   cd /Volumes/DATA/FREEDOM/services/rag_chunker');
    console.error('   python3 rag_api.py');
  }
}

testRAGAPI();