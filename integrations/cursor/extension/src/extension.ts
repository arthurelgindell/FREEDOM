/**
 * FREEDOM Platform - Cursor IDE Extension
 * Main extension entry point with command registration and integration logic
 */

import * as vscode from 'vscode';
import { FreedomCursorBridge, CodeContext, KnowledgeResult } from '../freedom-cursor-bridge';

export class FreedomExtension {
    private bridge: FreedomCursorBridge | null = null;
    private statusBarItem: vscode.StatusBarItem;
    private outputChannel: vscode.OutputChannel;
    private isConnected = false;

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.outputChannel = vscode.window.createOutputChannel('FREEDOM Platform');
        
        this.statusBarItem.text = "$(circle-slash) FREEDOM";
        this.statusBarItem.command = 'freedom.showHealth';
        this.statusBarItem.show();
    }

    async activate(context: vscode.ExtensionContext) {
        this.outputChannel.appendLine('🚀 FREEDOM Platform extension activating...');
        
        // Initialize FREEDOM bridge
        await this.initializeBridge();
        
        // Register commands
        this.registerCommands(context);
        
        // Set up file watchers for context awareness
        this.setupFileWatchers(context);
        
        this.outputChannel.appendLine('✅ FREEDOM Platform extension activated');
    }

    private async initializeBridge() {
        try {
            const config = vscode.workspace.getConfiguration('freedom');
            
            this.bridge = new FreedomCursorBridge({
                apiGateway: config.get('apiGateway', 'http://localhost:8080'),
                apiKey: config.get('apiKey', 'dev-key-change-in-production'),
                websocketUrl: config.get('apiGateway', 'http://localhost:8080').replace('http', 'ws'),
                timeout: 30000,
                retries: 3
            });

            // Set up WebSocket message handlers
            if (config.get('enableRealtime', true)) {
                this.bridge.onMessage('agent_response', (data) => {
                    this.handleAIResponse(data);
                });
                
                this.bridge.onMessage('status_update', (data) => {
                    this.updateStatusBar(data);
                });
            }

            // Test connection
            const connected = await this.bridge.initialize();
            if (connected) {
                this.isConnected = true;
                this.updateStatusBar({ status: 'connected', uptime: 0 });
                this.outputChannel.appendLine('✅ Connected to FREEDOM Platform');
            } else {
                this.updateStatusBar({ status: 'disconnected', error: 'Connection failed' });
                this.outputChannel.appendLine('❌ Failed to connect to FREEDOM Platform');
            }

        } catch (error) {
            this.outputChannel.appendLine(`❌ Bridge initialization error: ${error}`);
            this.updateStatusBar({ status: 'error', error: error.message });
        }
    }

    private registerCommands(context: vscode.ExtensionContext) {
        // Search Knowledge Base
        const searchKnowledgeCmd = vscode.commands.registerCommand('freedom.searchKnowledge', async () => {
            await this.searchKnowledge();
        });

        // Generate Code with AI
        const generateCodeCmd = vscode.commands.registerCommand('freedom.generateCode', async () => {
            await this.generateCode();
        });

        // Get Framework Documentation
        const getDocumentationCmd = vscode.commands.registerCommand('freedom.getDocumentation', async () => {
            await this.getDocumentation();
        });

        // Crawl Web Documentation
        const crawlWebDocsCmd = vscode.commands.registerCommand('freedom.crawlWebDocs', async () => {
            await this.crawlWebDocs();
        });

        // Show Platform Health
        const showHealthCmd = vscode.commands.registerCommand('freedom.showHealth', async () => {
            await this.showHealth();
        });

        // Context menu commands
        const contextSearchCmd = vscode.commands.registerCommand('freedom.contextSearch', async () => {
            const selection = vscode.window.activeTextEditor?.selection;
            if (selection && !selection.isEmpty) {
                await this.searchKnowledgeForSelection();
            }
        });

        const contextGenerateCmd = vscode.commands.registerCommand('freedom.contextGenerate', async () => {
            const selection = vscode.window.activeTextEditor?.selection;
            if (selection && !selection.isEmpty) {
                await this.generateCodeForSelection();
            }
        });

        context.subscriptions.push(
            searchKnowledgeCmd,
            generateCodeCmd,
            getDocumentationCmd,
            crawlWebDocsCmd,
            showHealthCmd,
            contextSearchCmd,
            contextGenerateCmd
        );
    }

    private setupFileWatchers(context: vscode.ExtensionContext) {
        // Watch for file changes to maintain context awareness
        const fileWatcher = vscode.workspace.onDidChangeTextDocument((event) => {
            if (this.bridge && this.isConnected) {
                // Send context updates via WebSocket for real-time assistance
                const context = this.getCurrentContext();
                this.bridge.sendRealtimeMessage('context_update', context);
            }
        });

        // Watch for active editor changes
        const editorWatcher = vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (editor && this.bridge && this.isConnected) {
                const context = this.getCurrentContext();
                this.bridge.sendRealtimeMessage('editor_change', context);
            }
        });

        context.subscriptions.push(fileWatcher, editorWatcher);
    }

    private async searchKnowledge() {
        if (!this.bridge || !this.isConnected) {
            vscode.window.showErrorMessage('FREEDOM Platform not connected');
            return;
        }

        try {
            const query = await vscode.window.showInputBox({
                prompt: 'Enter your search query',
                placeHolder: 'e.g., React hooks, Python async, Node.js middleware'
            });

            if (!query) return;

            const context = this.getCurrentContext();
            const results = await this.bridge.searchKnowledge(query, context);
            
            await this.displayKnowledgeResults(results, query);

        } catch (error) {
            vscode.window.showErrorMessage(`Knowledge search failed: ${error.message}`);
            this.outputChannel.appendLine(`❌ Knowledge search error: ${error}`);
        }
    }

    private async generateCode() {
        if (!this.bridge || !this.isConnected) {
            vscode.window.showErrorMessage('FREEDOM Platform not connected');
            return;
        }

        try {
            const prompt = await vscode.window.showInputBox({
                prompt: 'Describe what code you want to generate',
                placeHolder: 'e.g., Create a React component that fetches data from an API'
            });

            if (!prompt) return;

            const context = this.getCurrentContext();
            const generatedCode = await this.bridge.generateCode(prompt, context);
            
            await this.insertGeneratedCode(generatedCode);

        } catch (error) {
            vscode.window.showErrorMessage(`Code generation failed: ${error.message}`);
            this.outputChannel.appendLine(`❌ Code generation error: ${error}`);
        }
    }

    private async getDocumentation() {
        if (!this.bridge || !this.isConnected) {
            vscode.window.showErrorMessage('FREEDOM Platform not connected');
            return;
        }

        try {
            const framework = await vscode.window.showInputBox({
                prompt: 'Enter framework or technology name',
                placeHolder: 'e.g., React, Vue, Express, Django'
            });

            if (!framework) return;

            const docs = await this.bridge.getTechDocumentation(framework);
            
            if (docs.length > 0) {
                await this.displayDocumentation(docs, framework);
            } else {
                vscode.window.showInformationMessage(`No documentation found for ${framework}`);
            }

        } catch (error) {
            vscode.window.showErrorMessage(`Documentation retrieval failed: ${error.message}`);
            this.outputChannel.appendLine(`❌ Documentation error: ${error}`);
        }
    }

    private async crawlWebDocs() {
        if (!this.bridge || !this.isConnected) {
            vscode.window.showErrorMessage('FREEDOM Platform not connected');
            return;
        }

        try {
            const url = await vscode.window.showInputBox({
                prompt: 'Enter documentation URL to crawl',
                placeHolder: 'e.g., https://docs.react.dev/hooks/useState'
            });

            if (!url) return;

            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Crawling web documentation...",
                cancellable: false
            }, async () => {
                const result = await this.bridge.crawlDocumentation(url, 'documentation');
                await this.displayCrawledDocumentation(result, url);
            });

        } catch (error) {
            vscode.window.showErrorMessage(`Web crawling failed: ${error.message}`);
            this.outputChannel.appendLine(`❌ Web crawling error: ${error}`);
        }
    }

    private async showHealth() {
        if (!this.bridge) {
            vscode.window.showErrorMessage('FREEDOM Platform not initialized');
            return;
        }

        try {
            const health = await this.bridge.getSystemHealth();
            
            const message = `FREEDOM Platform Status: ${health.status}\n` +
                          `Uptime: ${Math.round(health.uptime_seconds / 60)} minutes\n` +
                          `KB Service: ${health.kb_service_status}\n` +
                          `MLX Service: ${health.mlx_service_status}`;
            
            vscode.window.showInformationMessage(message);
            this.outputChannel.appendLine(`🏥 Health check: ${JSON.stringify(health, null, 2)}`);

        } catch (error) {
            vscode.window.showErrorMessage(`Health check failed: ${error.message}`);
            this.outputChannel.appendLine(`❌ Health check error: ${error}`);
        }
    }

    private async searchKnowledgeForSelection() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const selectedText = editor.document.getText(editor.selection);
        if (!selectedText.trim()) return;

        if (!this.bridge || !this.isConnected) {
            vscode.window.showErrorMessage('FREEDOM Platform not connected');
            return;
        }

        try {
            const context = this.getCurrentContext();
            const results = await this.bridge.searchKnowledge(selectedText, context);
            await this.displayKnowledgeResults(results, selectedText);

        } catch (error) {
            vscode.window.showErrorMessage(`Knowledge search failed: ${error.message}`);
        }
    }

    private async generateCodeForSelection() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const selectedText = editor.document.getText(editor.selection);
        if (!selectedText.trim()) return;

        if (!this.bridge || !this.isConnected) {
            vscode.window.showErrorMessage('FREEDOM Platform not connected');
            return;
        }

        try {
            const prompt = `Improve or complete this code: ${selectedText}`;
            const context = this.getCurrentContext();
            const generatedCode = await this.bridge.generateCode(prompt, context);
            
            // Replace selection with generated code
            await editor.edit(editBuilder => {
                editBuilder.replace(editor.selection, generatedCode);
            });

            vscode.window.showInformationMessage('Code generated and inserted');

        } catch (error) {
            vscode.window.showErrorMessage(`Code generation failed: ${error.message}`);
        }
    }

    private getCurrentContext(): CodeContext | undefined {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return undefined;

        const document = editor.document;
        const languageId = document.languageId;
        const filePath = document.fileName;
        const selectedText = editor.selection.isEmpty ? undefined : document.getText(editor.selection);

        // Detect framework based on file content and path
        const framework = this.detectFramework(document.getText(), filePath, languageId);

        return {
            file_path: filePath,
            file_type: languageId,
            framework,
            current_code: document.getText(),
            cursor_position: editor.selection.active.character,
            selected_text: selectedText
        };
    }

    private detectFramework(content: string, filePath: string, languageId: string): string | undefined {
        // Simple framework detection logic
        if (languageId === 'typescript' || languageId === 'javascript') {
            if (content.includes('import React') || content.includes('from "react"')) return 'react';
            if (content.includes('import Vue') || content.includes('from "vue"')) return 'vue';
            if (content.includes('import express') || content.includes('from "express"')) return 'express';
            if (content.includes('import fastapi') || content.includes('from "fastapi"')) return 'fastapi';
            if (filePath.includes('angular')) return 'angular';
            if (filePath.includes('next')) return 'nextjs';
        }
        
        if (languageId === 'python') {
            if (content.includes('import django')) return 'django';
            if (content.includes('import flask')) return 'flask';
            if (content.includes('import fastapi')) return 'fastapi';
        }

        return undefined;
    }

    private async displayKnowledgeResults(results: KnowledgeResult[], query: string) {
        if (results.length === 0) {
            vscode.window.showInformationMessage(`No knowledge found for: ${query}`);
            return;
        }

        // Create a webview to display results
        const panel = vscode.window.createWebviewPanel(
            'freedomKnowledge',
            `FREEDOM Knowledge: ${query}`,
            vscode.ViewColumn.One,
            { enableScripts: true }
        );

        const html = this.generateKnowledgeHTML(results, query);
        panel.webview.html = html;

        // Show summary in notification
        const summary = `Found ${results.length} knowledge results for "${query}"`;
        vscode.window.showInformationMessage(summary);
    }

    private generateKnowledgeHTML(results: KnowledgeResult[], query: string): string {
        const resultsHTML = results.map(result => `
            <div class="result-item">
                <h3>${result.component_name}</h3>
                <p class="tech">Technology: ${result.technology_name}</p>
                <p class="type">Type: ${result.component_type}</p>
                <p class="confidence">Confidence: ${(result.confidence_score * 100).toFixed(1)}%</p>
                <div class="specification">
                    <pre>${JSON.stringify(result.specification, null, 2)}</pre>
                </div>
            </div>
        `).join('');

        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>FREEDOM Knowledge Results</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; }
                    .result-item { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
                    .tech { color: #0066cc; font-weight: bold; }
                    .type { color: #666; }
                    .confidence { color: #009900; font-weight: bold; }
                    .specification { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; }
                    pre { margin: 0; white-space: pre-wrap; }
                </style>
            </head>
            <body>
                <h1>FREEDOM Knowledge Results</h1>
                <p>Query: <strong>${query}</strong></p>
                <p>Found ${results.length} results:</p>
                ${resultsHTML}
            </body>
            </html>
        `;
    }

    private async insertGeneratedCode(code: string) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const position = editor.selection.active;
        await editor.edit(editBuilder => {
            editBuilder.insert(position, code);
        });

        vscode.window.showInformationMessage('Code generated and inserted');
    }

    private async displayDocumentation(docs: any[], framework: string) {
        const panel = vscode.window.createWebviewPanel(
            'freedomDocs',
            `FREEDOM Docs: ${framework}`,
            vscode.ViewColumn.One,
            { enableScripts: true }
        );

        const docsHTML = docs.map(doc => `
            <div class="doc-item">
                <h3>${doc.name || 'Documentation'}</h3>
                <div class="content">${JSON.stringify(doc, null, 2)}</div>
            </div>
        `).join('');

        panel.webview.html = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>FREEDOM Documentation</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; }
                    .doc-item { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
                    .content { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; }
                </style>
            </head>
            <body>
                <h1>FREEDOM Documentation: ${framework}</h1>
                ${docsHTML}
            </body>
            </html>
        `;
    }

    private async displayCrawledDocumentation(result: any, url: string) {
        const panel = vscode.window.createWebviewPanel(
            'freedomCrawled',
            `FREEDOM Crawled: ${url}`,
            vscode.ViewColumn.One,
            { enableScripts: true }
        );

        panel.webview.html = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>FREEDOM Crawled Documentation</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; }
                    .content { background: #f5f5f5; padding: 15px; border-radius: 5px; }
                </style>
            </head>
            <body>
                <h1>Crawled Documentation</h1>
                <p>Source: <a href="${url}" target="_blank">${url}</a></p>
                <div class="content">
                    <pre>${JSON.stringify(result, null, 2)}</pre>
                </div>
            </body>
            </html>
        `;
    }

    private handleAIResponse(data: any) {
        this.outputChannel.appendLine(`🤖 AI Response: ${JSON.stringify(data)}`);
        // Handle real-time AI responses
    }

    private updateStatusBar(data: any) {
        if (data.status === 'connected') {
            this.statusBarItem.text = "$(check) FREEDOM";
            this.statusBarItem.tooltip = "FREEDOM Platform Connected";
            this.isConnected = true;
        } else if (data.status === 'disconnected') {
            this.statusBarItem.text = "$(circle-slash) FREEDOM";
            this.statusBarItem.tooltip = "FREEDOM Platform Disconnected";
            this.isConnected = false;
        } else if (data.status === 'error') {
            this.statusBarItem.text = "$(error) FREEDOM";
            this.statusBarItem.tooltip = `FREEDOM Platform Error: ${data.error}`;
            this.isConnected = false;
        }
    }

    async deactivate() {
        if (this.bridge) {
            await this.bridge.dispose();
        }
        this.statusBarItem.dispose();
        this.outputChannel.dispose();
    }
}

// Extension activation
export function activate(context: vscode.ExtensionContext) {
    const extension = new FreedomExtension();
    return extension.activate(context);
}

// Extension deactivation
export function deactivate() {
    // Cleanup handled by extension instance
}
