#!/usr/bin/env python3
"""
FREEDOM Tools for CrewAI
Reusable tools for agent collaboration
"""

import json
import time
from pathlib import Path
from typing import Any, Optional
from crewai.tools import BaseTool


class FREEDOMTool(BaseTool):
    """Base tool for FREEDOM platform integration"""
    
    name: str
    description: str
    
    def __init__(self, name: str, description: str, truth_engine=None, mlx_server=None):
        super().__init__()
        self.name = name
        self.description = description
        self.truth_engine = truth_engine
        self.mlx_server = mlx_server
    
    def _run(self, *args, **kwargs) -> str:
        """Execute the tool"""
        raise NotImplementedError("Subclasses must implement _run method")


class TruthVerificationTool(FREEDOMTool):
    """Tool for verifying claims using the Truth Engine"""
    
    def __init__(self, truth_engine, mlx_server=None):
        super().__init__(
            name="truth_verification",
            description="Verify claims using the FREEDOM Truth Engine",
            truth_engine=truth_engine,
            mlx_server=mlx_server
        )
    
    def _run(self, claim: str) -> str:
        """Verify a claim using the Truth Engine"""
        try:
            if self.truth_engine:
                result = self.truth_engine.verify_claim(claim)
                return f"Claim verification: {result['verified']} (confidence: {result['confidence']:.2f})"
            else:
                return "Truth Engine not available"
        except Exception as e:
            return f"Verification failed: {str(e)}"


class MLXInferenceTool(FREEDOMTool):
    """Tool for generating responses using MLX models"""
    
    def __init__(self, truth_engine=None, mlx_server=None):
        super().__init__(
            name="mlx_inference",
            description="Generate AI responses using MLX models",
            truth_engine=truth_engine,
            mlx_server=mlx_server
        )
    
    def _run(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate response using MLX models"""
        try:
            if self.mlx_server:
                models = self.mlx_server.get_available_models()
                if models:
                    model_name = models[0].name if hasattr(models[0], 'name') else str(models[0])
                    result = self.mlx_server.generate_response(
                        model_name=model_name,
                        prompt=prompt,
                        max_tokens=max_tokens
                    )
                    return result.get('response', 'No response generated')
                else:
                    return "No models available for inference"
            else:
                # Fallback to mock response
                return f"[Mock MLX Response to: {prompt[:50]}...]"
        except Exception as e:
            return f"Inference failed: {str(e)}"


class FileAnalysisTool(FREEDOMTool):
    """Tool for analyzing files and extracting information"""
    
    def __init__(self, truth_engine=None, mlx_server=None):
        super().__init__(
            name="file_analysis",
            description="Analyze files and extract key information",
            truth_engine=truth_engine,
            mlx_server=mlx_server
        )
    
    def _run(self, file_path: str) -> str:
        """Analyze a file and extract key information"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"File not found: {file_path}"
            
            # Basic file analysis
            file_info = {
                "name": path.name,
                "size": path.stat().st_size,
                "size_human": self._format_size(path.stat().st_size),
                "extension": path.suffix,
                "modified": time.ctime(path.stat().st_mtime),
                "is_directory": path.is_dir()
            }
            
            # Read content for text files
            if not path.is_dir() and path.suffix in ['.txt', '.py', '.md', '.json', '.yaml', '.yml']:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_info["lines"] = len(content.splitlines())
                        file_info["characters"] = len(content)
                        file_info["content_preview"] = content[:500] + "..." if len(content) > 500 else content
                        
                        # Special handling for specific file types
                        if path.suffix == '.json':
                            try:
                                json_data = json.loads(content)
                                file_info["json_keys"] = list(json_data.keys()) if isinstance(json_data, dict) else "Array"
                            except:
                                file_info["json_valid"] = False
                                
                except Exception as e:
                    file_info["content_error"] = str(e)
            
            return f"File analysis complete:\n{json.dumps(file_info, indent=2)}"
            
        except Exception as e:
            return f"File analysis failed: {str(e)}"
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


class DataProcessingTool(FREEDOMTool):
    """Tool for processing and transforming data"""
    
    def __init__(self, truth_engine=None, mlx_server=None):
        super().__init__(
            name="data_processing",
            description="Process and transform data in various formats",
            truth_engine=truth_engine,
            mlx_server=mlx_server
        )
    
    def _run(self, data: str, operation: str = "summary") -> str:
        """Process data based on the specified operation"""
        try:
            operations = {
                "summary": self._summarize_data,
                "statistics": self._calculate_statistics,
                "format": self._format_data,
                "validate": self._validate_data
            }
            
            if operation not in operations:
                return f"Unknown operation: {operation}. Available: {list(operations.keys())}"
            
            return operations[operation](data)
            
        except Exception as e:
            return f"Data processing failed: {str(e)}"
    
    def _summarize_data(self, data: str) -> str:
        """Create a summary of the data"""
        lines = data.strip().split('\n')
        return f"Data summary: {len(lines)} lines, {len(data)} characters, {len(data.split())} words"
    
    def _calculate_statistics(self, data: str) -> str:
        """Calculate basic statistics"""
        try:
            # Try to parse as numbers
            numbers = [float(x) for x in data.split() if x.replace('.', '').replace('-', '').isdigit()]
            if numbers:
                import statistics
                return f"Statistics: count={len(numbers)}, mean={statistics.mean(numbers):.2f}, median={statistics.median(numbers):.2f}"
            else:
                return "No numeric data found for statistics"
        except:
            return "Could not calculate statistics"
    
    def _format_data(self, data: str) -> str:
        """Format data for better readability"""
        try:
            # Try JSON formatting
            json_data = json.loads(data)
            return json.dumps(json_data, indent=2)
        except:
            # Return cleaned text
            return '\n'.join(line.strip() for line in data.split('\n') if line.strip())
    
    def _validate_data(self, data: str) -> str:
        """Validate data format"""
        validations = []
        
        # Check JSON
        try:
            json.loads(data)
            validations.append("✓ Valid JSON")
        except:
            validations.append("✗ Invalid JSON")
        
        # Check for common patterns
        if '@' in data and '.' in data:
            validations.append("✓ Contains email-like patterns")
        
        if data.strip().startswith('http'):
            validations.append("✓ Contains URL-like patterns")
        
        return "Data validation:\n" + '\n'.join(validations)


class CodeAnalysisTool(FREEDOMTool):
    """Tool for analyzing code files"""
    
    def __init__(self, truth_engine=None, mlx_server=None):
        super().__init__(
            name="code_analysis",
            description="Analyze code files for structure, complexity, and quality",
            truth_engine=truth_engine,
            mlx_server=mlx_server
        )
    
    def _run(self, file_path: str) -> str:
        """Analyze a code file"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"File not found: {file_path}"
            
            if not path.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']:
                return f"Not a recognized code file: {path.suffix}"
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                "file": path.name,
                "language": self._detect_language(path.suffix),
                "lines": len(content.splitlines()),
                "non_empty_lines": len([l for l in content.splitlines() if l.strip()]),
                "functions": self._count_functions(content, path.suffix),
                "classes": self._count_classes(content, path.suffix),
                "imports": self._count_imports(content, path.suffix),
                "comments": self._count_comments(content, path.suffix),
                "complexity_estimate": self._estimate_complexity(content)
            }
            
            return f"Code analysis:\n{json.dumps(analysis, indent=2)}"
            
        except Exception as e:
            return f"Code analysis failed: {str(e)}"
    
    def _detect_language(self, suffix: str) -> str:
        """Detect programming language from file extension"""
        languages = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rs': 'Rust'
        }
        return languages.get(suffix, 'Unknown')
    
    def _count_functions(self, content: str, suffix: str) -> int:
        """Count function definitions"""
        if suffix == '.py':
            return content.count('def ')
        elif suffix in ['.js', '.ts']:
            return content.count('function ') + content.count('=>')
        elif suffix == '.java':
            return content.count('public ') + content.count('private ') + content.count('protected ')
        return 0
    
    def _count_classes(self, content: str, suffix: str) -> int:
        """Count class definitions"""
        if suffix in ['.py', '.java', '.ts']:
            return content.count('class ')
        return 0
    
    def _count_imports(self, content: str, suffix: str) -> int:
        """Count import statements"""
        if suffix == '.py':
            return content.count('import ') + content.count('from ')
        elif suffix in ['.js', '.ts']:
            return content.count('import ') + content.count('require(')
        elif suffix == '.java':
            return content.count('import ')
        return 0
    
    def _count_comments(self, content: str, suffix: str) -> int:
        """Count comment lines"""
        lines = content.splitlines()
        comment_count = 0
        
        for line in lines:
            stripped = line.strip()
            if suffix == '.py' and stripped.startswith('#'):
                comment_count += 1
            elif suffix in ['.js', '.ts', '.java', '.cpp', '.c'] and stripped.startswith('//'):
                comment_count += 1
                
        return comment_count
    
    def _estimate_complexity(self, content: str) -> str:
        """Estimate code complexity"""
        lines = len(content.splitlines())
        
        if lines < 100:
            return "Low"
        elif lines < 500:
            return "Medium"
        elif lines < 1000:
            return "High"
        else:
            return "Very High"
