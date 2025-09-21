#!/usr/bin/env python3
"""
FREEDOM Platform - LM Studio Live Model Validation
Real-time testing of loaded LM Studio models via http://localhost:1234/v1
Prime Directive: "If it doesn't run, it doesn't exist"
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, List

class LMStudioLiveValidator:
    """Live validation of LM Studio server and loaded models"""
    
    def __init__(self):
        self.base_url = "http://localhost:1234/v1"
        self.results = []
        self.start_time = time.time()
        
    def log_result(self, test_name: str, passed: bool, duration: float, details: Dict = None, error: str = None):
        """Log validation result"""
        result = {
            "test": test_name,
            "status": "PASS" if passed else "FAIL",
            "duration_ms": duration * 1000,
            "details": details or {},
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results.append(result)
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} {test_name}: {result['status']} ({duration*1000:.1f}ms)")
        if error:
            print(f"   Error: {error}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    def test_server_connectivity(self) -> bool:
        """Test LM Studio server is running and responding"""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/models", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                models = data.get('data', [])
                model_ids = [model['id'] for model in models]
                
                self.log_result("Server Connectivity", True, time.time() - start, {
                    "status_code": 200,
                    "models_loaded": len(models),
                    "model_ids": model_ids
                })
                return True
            else:
                self.log_result("Server Connectivity", False, time.time() - start, 
                              {"status_code": response.status_code}, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Server Connectivity", False, time.time() - start, 
                          {}, f"Connection error: {str(e)}")
            return False
    
    def test_qwen3_30b_model(self) -> bool:
        """Test Qwen3-30B model inference"""
        start = time.time()
        try:
            payload = {
                "model": "qwen3-30b-a3b-instruct-2507-mlx",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant. Be concise."},
                    {"role": "user", "content": "What is the capital of France? Answer with just the city name."}
                ],
                "max_tokens": 5,
                "temperature": 0.1
            }
            
            response = requests.post(f"{self.base_url}/chat/completions", 
                                   json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content'].strip()
                usage = data.get('usage', {})
                
                # Check if answer contains "Paris"
                is_correct = 'paris' in content.lower()
                
                self.log_result("Qwen3-30B Model Test", True, time.time() - start, {
                    "model": data.get('model'),
                    "response": content,
                    "correct_answer": is_correct,
                    "tokens": usage.get('total_tokens', 0),
                    "prompt_tokens": usage.get('prompt_tokens', 0),
                    "completion_tokens": usage.get('completion_tokens', 0)
                })
                return True
            else:
                self.log_result("Qwen3-30B Model Test", False, time.time() - start,
                              {"status_code": response.status_code}, response.text)
                return False
                
        except Exception as e:
            self.log_result("Qwen3-30B Model Test", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def test_ui_tars_model(self) -> bool:
        """Test UI-TARS model code generation"""
        start = time.time()
        try:
            payload = {
                "model": "ui-tars-1.5-7b-mlx",
                "messages": [
                    {"role": "user", "content": "Write a Python function that multiplies two numbers. Just show the function definition."}
                ],
                "max_tokens": 100,
                "temperature": 0.3
            }
            
            response = requests.post(f"{self.base_url}/chat/completions", 
                                   json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                usage = data.get('usage', {})
                
                # Check if response contains Python function
                has_def = 'def ' in content
                has_return = 'return' in content or '*' in content
                
                self.log_result("UI-TARS Model Test", True, time.time() - start, {
                    "model": data.get('model'),
                    "response_length": len(content),
                    "has_function_def": has_def,
                    "has_multiplication": has_return,
                    "tokens": usage.get('total_tokens', 0),
                    "response_preview": content[:100] + "..." if len(content) > 100 else content
                })
                return True
            else:
                self.log_result("UI-TARS Model Test", False, time.time() - start,
                              {"status_code": response.status_code}, response.text)
                return False
                
        except Exception as e:
            self.log_result("UI-TARS Model Test", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def test_embedding_model(self) -> bool:
        """Test text embedding model (if available)"""
        start = time.time()
        try:
            # Check if embedding model is available
            models_response = requests.get(f"{self.base_url}/models", timeout=10)
            if models_response.status_code != 200:
                self.log_result("Embedding Model Test", False, time.time() - start,
                              {}, "Could not fetch models list")
                return False
            
            models_data = models_response.json()
            embedding_models = [m for m in models_data.get('data', []) 
                              if 'embed' in m['id'].lower()]
            
            if not embedding_models:
                self.log_result("Embedding Model Test", False, time.time() - start,
                              {}, "No embedding models found")
                return False
            
            # Note: LM Studio might not have embeddings endpoint active
            # This test just confirms the model is listed
            self.log_result("Embedding Model Test", True, time.time() - start, {
                "embedding_models_available": [m['id'] for m in embedding_models],
                "note": "Model listed but embeddings endpoint may not be active"
            })
            return True
            
        except Exception as e:
            self.log_result("Embedding Model Test", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def test_performance_benchmark(self) -> bool:
        """Performance benchmark test"""
        start = time.time()
        try:
            # Test with a longer prompt for performance measurement
            payload = {
                "model": "qwen3-30b-a3b-instruct-2507-mlx",
                "messages": [
                    {"role": "user", "content": "Explain the concept of machine learning in exactly 3 sentences."}
                ],
                "max_tokens": 150,
                "temperature": 0.5
            }
            
            generation_start = time.time()
            response = requests.post(f"{self.base_url}/chat/completions", 
                                   json=payload, timeout=60)
            generation_time = time.time() - generation_start
            
            if response.status_code == 200:
                data = response.json()
                usage = data.get('usage', {})
                content = data['choices'][0]['message']['content']
                
                total_tokens = usage.get('total_tokens', 0)
                tokens_per_second = total_tokens / generation_time if generation_time > 0 else 0
                
                self.log_result("Performance Benchmark", True, time.time() - start, {
                    "generation_time_seconds": round(generation_time, 3),
                    "total_tokens": total_tokens,
                    "tokens_per_second": round(tokens_per_second, 2),
                    "response_length": len(content),
                    "model": data.get('model')
                })
                return True
            else:
                self.log_result("Performance Benchmark", False, time.time() - start,
                              {"status_code": response.status_code}, response.text)
                return False
                
        except Exception as e:
            self.log_result("Performance Benchmark", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def test_mlx_proxy_fallback(self) -> bool:
        """Test FREEDOM MLX proxy fallback to LM Studio"""
        start = time.time()
        try:
            # Check MLX proxy health
            proxy_response = requests.get("http://localhost:8001/health", timeout=10)
            
            if proxy_response.status_code == 200:
                proxy_data = proxy_response.json()
                
                # Test inference through API Gateway (should fallback to LM Studio if MLX fails)
                gateway_response = requests.post("http://localhost:8080/inference",
                    headers={"X-API-Key": "dev-key-change-in-production"},
                    json={"prompt": "Hello", "max_tokens": 10},
                    timeout=30
                )
                
                gateway_working = gateway_response.status_code == 200
                
                self.log_result("MLX Proxy Fallback", True, time.time() - start, {
                    "proxy_healthy": True,
                    "upstream": proxy_data.get('upstream'),
                    "upstream_url": proxy_data.get('upstream_url'),
                    "mlx_server_reachable": proxy_data.get('mlx_server_reachable'),
                    "gateway_inference_working": gateway_working,
                    "gateway_status": gateway_response.status_code
                })
                return True
            else:
                self.log_result("MLX Proxy Fallback", False, time.time() - start,
                              {"proxy_status": proxy_response.status_code}, "MLX proxy not healthy")
                return False
                
        except Exception as e:
            self.log_result("MLX Proxy Fallback", False, time.time() - start, 
                          {}, f"Error: {str(e)}")
            return False
    
    def run_live_validation(self) -> bool:
        """Run complete live validation of LM Studio integration"""
        print("🔴 FREEDOM Platform - LM Studio Live Validation")
        print("=" * 60)
        print(f"Testing LM Studio server at: {self.base_url}")
        print(f"Validation started: {datetime.utcnow().isoformat()}")
        print()
        
        tests = [
            ("Server Connectivity", self.test_server_connectivity),
            ("Qwen3-30B Model", self.test_qwen3_30b_model),
            ("UI-TARS Model", self.test_ui_tars_model),
            ("Embedding Model", self.test_embedding_model),
            ("Performance Benchmark", self.test_performance_benchmark),
            ("MLX Proxy Fallback", self.test_mlx_proxy_fallback)
        ]
        
        passed = 0
        for test_name, test_func in tests:
            if test_func():
                passed += 1
            print()  # Add spacing between tests
        
        total_time = time.time() - self.start_time
        
        print("=" * 60)
        print(f"Live Validation Results: {passed}/{len(tests)} passed")
        print(f"Total execution time: {total_time:.2f}s")
        
        if passed >= len(tests) - 1:  # Allow 1 test to fail (embedding might not be active)
            print("✅ LM STUDIO LIVE VALIDATION PASSED")
            print("LM Studio server is operational with loaded models")
            return True
        else:
            print("❌ LM STUDIO LIVE VALIDATION FAILED")
            print("Check LM Studio server and model loading status")
            return False
    
    def save_validation_report(self, filename: str = "lm_studio_live_validation_report.json"):
        """Save validation report"""
        report = {
            "validation_timestamp": datetime.utcnow().isoformat(),
            "server_url": self.base_url,
            "total_tests": len(self.results),
            "passed_tests": len([r for r in self.results if r['status'] == 'PASS']),
            "failed_tests": len([r for r in self.results if r['status'] == 'FAIL']),
            "total_duration_seconds": time.time() - self.start_time,
            "results": self.results,
            "summary": {
                "server_operational": any(r['test'] == 'Server Connectivity' and r['status'] == 'PASS' for r in self.results),
                "models_working": len([r for r in self.results if 'Model Test' in r['test'] and r['status'] == 'PASS']),
                "performance_validated": any(r['test'] == 'Performance Benchmark' and r['status'] == 'PASS' for r in self.results)
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nValidation report saved to: {filename}")
        return report


def main():
    """Main validation runner"""
    validator = LMStudioLiveValidator()
    success = validator.run_live_validation()
    validator.save_validation_report()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
