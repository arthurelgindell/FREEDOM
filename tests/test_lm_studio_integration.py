#!/usr/bin/env python3
"""
FREEDOM Platform - LM Studio Integration Tests
Tests for LM Studio model integration and functionality
Following Prime Directive: "If it doesn't run, it doesn't exist"
"""

import asyncio
import json
import time
import requests
import pytest
from typing import Dict, Any, Optional
from pathlib import Path

# Test configuration
LM_STUDIO_CONFIG = {
    "base_url": "http://localhost:1234/v1",
    "models_url": "http://localhost:1234/v1/models",
    "chat_url": "http://localhost:1234/v1/chat/completions",
    "timeout": 30,
    "test_model": "qwen3-30b-a3b-instruct-2507-mlx"
}

class LMStudioIntegrationTest:
    """Comprehensive LM Studio integration tests"""
    
    def __init__(self):
        self.results = []
        self.start_time = time.time()
    
    def log_result(self, test_name: str, passed: bool, duration: float, details: Dict = None, error: str = None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": "PASS" if passed else "FAIL",
            "duration_ms": duration * 1000,
            "details": details or {},
            "error": error,
            "timestamp": time.time()
        }
        self.results.append(result)
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} {test_name}: {result['status']} ({duration*1000:.1f}ms)")
        if error:
            print(f"   Error: {error}")
    
    def test_lm_studio_connectivity(self) -> bool:
        """Test basic LM Studio server connectivity"""
        start = time.time()
        try:
            response = requests.get(f"{LM_STUDIO_CONFIG['base_url']}/models", 
                                  timeout=LM_STUDIO_CONFIG['timeout'])
            
            if response.status_code == 200:
                models_data = response.json()
                self.log_result("LM Studio Connectivity", True, time.time() - start, 
                              {"status_code": 200, "models_count": len(models_data.get('data', []))})
                return True
            else:
                self.log_result("LM Studio Connectivity", False, time.time() - start, 
                              {"status_code": response.status_code}, f"HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            self.log_result("LM Studio Connectivity", False, time.time() - start, 
                          {}, f"Connection refused: {str(e)}")
            return False
        except Exception as e:
            self.log_result("LM Studio Connectivity", False, time.time() - start, 
                          {}, f"Unexpected error: {str(e)}")
            return False
    
    def test_model_availability(self) -> bool:
        """Test if required models are available"""
        start = time.time()
        try:
            response = requests.get(LM_STUDIO_CONFIG['models_url'], 
                                  timeout=LM_STUDIO_CONFIG['timeout'])
            
            if response.status_code == 200:
                models_data = response.json()
                available_models = [model['id'] for model in models_data.get('data', [])]
                
                # Check for FREEDOM models
                freedom_models = [
                    "qwen3-30b-a3b-instruct-2507-mlx",
                    "ui-tars-1.5-7b-mlx"
                ]
                
                found_models = [model for model in freedom_models if any(model in available for available in available_models)]
                
                self.log_result("Model Availability", len(found_models) > 0, time.time() - start,
                              {"available_models": available_models, "freedom_models_found": found_models})
                return len(found_models) > 0
            else:
                self.log_result("Model Availability", False, time.time() - start,
                              {"status_code": response.status_code}, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Model Availability", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def test_chat_completion(self) -> bool:
        """Test chat completion functionality"""
        start = time.time()
        try:
            payload = {
                "model": LM_STUDIO_CONFIG['test_model'],
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant. Respond concisely."},
                    {"role": "user", "content": "What is 2+2? Answer with just the number."}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            response = requests.post(LM_STUDIO_CONFIG['chat_url'], 
                                   json=payload,
                                   timeout=LM_STUDIO_CONFIG['timeout'],
                                   headers={"Content-Type": "application/json"})
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                usage = data.get('usage', {})
                
                # Check if response contains "4" (correct answer)
                is_correct = '4' in content
                
                self.log_result("Chat Completion", True, time.time() - start,
                              {
                                  "response": content.strip(),
                                  "correct_answer": is_correct,
                                  "tokens_used": usage.get('total_tokens', 0),
                                  "model": data.get('model', 'unknown')
                              })
                return True
            else:
                self.log_result("Chat Completion", False, time.time() - start,
                              {"status_code": response.status_code}, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Chat Completion", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def test_model_performance(self) -> bool:
        """Test model performance metrics"""
        start = time.time()
        try:
            test_prompt = "Write a simple Python function that adds two numbers."
            
            payload = {
                "model": LM_STUDIO_CONFIG['test_model'],
                "messages": [
                    {"role": "user", "content": test_prompt}
                ],
                "max_tokens": 100,
                "temperature": 0.3
            }
            
            generation_start = time.time()
            response = requests.post(LM_STUDIO_CONFIG['chat_url'], 
                                   json=payload,
                                   timeout=LM_STUDIO_CONFIG['timeout'])
            generation_time = time.time() - generation_start
            
            if response.status_code == 200:
                data = response.json()
                usage = data.get('usage', {})
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Calculate tokens per second
                total_tokens = usage.get('total_tokens', 0)
                tokens_per_second = total_tokens / generation_time if generation_time > 0 else 0
                
                # Check if response contains Python code
                has_python_code = 'def ' in content or 'return' in content
                
                self.log_result("Model Performance", True, time.time() - start,
                              {
                                  "generation_time_seconds": generation_time,
                                  "total_tokens": total_tokens,
                                  "tokens_per_second": round(tokens_per_second, 2),
                                  "response_length": len(content),
                                  "contains_code": has_python_code
                              })
                return True
            else:
                self.log_result("Model Performance", False, time.time() - start,
                              {"status_code": response.status_code}, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Model Performance", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def test_integration_with_mlx_proxy(self) -> bool:
        """Test integration with FREEDOM MLX proxy service"""
        start = time.time()
        try:
            # Test MLX proxy health
            proxy_response = requests.get("http://localhost:8001/health", timeout=10)
            
            if proxy_response.status_code == 200:
                proxy_data = proxy_response.json()
                using_fallback = proxy_data.get('upstream') == 'fallback'
                upstream_url = proxy_data.get('upstream_url', '')
                
                self.log_result("MLX Proxy Integration", True, time.time() - start,
                              {
                                  "proxy_healthy": True,
                                  "using_fallback": using_fallback,
                                  "upstream_url": upstream_url,
                                  "mlx_server_reachable": proxy_data.get('mlx_server_reachable', False)
                              })
                return True
            else:
                self.log_result("MLX Proxy Integration", False, time.time() - start,
                              {"proxy_status": proxy_response.status_code}, "MLX proxy unhealthy")
                return False
                
        except Exception as e:
            self.log_result("MLX Proxy Integration", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def test_model_files_exist(self) -> bool:
        """Test that model files exist in FREEDOM repository"""
        start = time.time()
        try:
            model_paths = [
                Path("models/lmstudio-community/Qwen3-30B-A3B-Instruct-2507-MLX-4bit"),
                Path("models/portalAI/UI-TARS-1.5-7B-mlx-bf16")
            ]
            
            results = {}
            all_exist = True
            
            for model_path in model_paths:
                exists = model_path.exists()
                if exists:
                    config_file = model_path / "config.json"
                    has_config = config_file.exists()
                    
                    # Count model files
                    model_files = list(model_path.glob("*.safetensors")) + list(model_path.glob("*.bin"))
                    file_count = len(model_files)
                    
                    results[str(model_path)] = {
                        "exists": True,
                        "has_config": has_config,
                        "model_files": file_count
                    }
                else:
                    results[str(model_path)] = {"exists": False}
                    all_exist = False
            
            self.log_result("Model Files Exist", all_exist, time.time() - start, results)
            return all_exist
            
        except Exception as e:
            self.log_result("Model Files Exist", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all LM Studio integration tests"""
        print("🧪 FREEDOM Platform - LM Studio Integration Tests")
        print("=" * 60)
        
        tests = [
            self.test_model_files_exist,
            self.test_lm_studio_connectivity,
            self.test_model_availability,
            self.test_chat_completion,
            self.test_model_performance,
            self.test_integration_with_mlx_proxy
        ]
        
        passed = 0
        for test in tests:
            if test():
                passed += 1
        
        total_time = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print(f"LM Studio Integration Test Results: {passed}/{len(tests)} passed")
        print(f"Total execution time: {total_time:.2f}s")
        
        if passed == len(tests):
            print("✅ ALL LM STUDIO TESTS PASSED")
            print("LM Studio is fully integrated and functional in FREEDOM Platform")
            return True
        else:
            print("❌ SOME LM STUDIO TESTS FAILED")
            print("Check LM Studio configuration and service status")
            return False
    
    def save_results(self, filename: str = "lm_studio_test_results.json"):
        """Save test results to file"""
        results_data = {
            "timestamp": time.time(),
            "total_tests": len(self.results),
            "passed_tests": len([r for r in self.results if r['status'] == 'PASS']),
            "failed_tests": len([r for r in self.results if r['status'] == 'FAIL']),
            "total_duration": time.time() - self.start_time,
            "results": self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"Test results saved to: {filename}")


def main():
    """Main test runner"""
    tester = LMStudioIntegrationTest()
    success = tester.run_all_tests()
    tester.save_results()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
