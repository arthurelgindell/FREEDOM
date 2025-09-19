#!/usr/bin/env python3
"""
FREEDOM API Gateway Deployment Verification
Verifies that the API Gateway is properly configured and ready for deployment
"""

import os
import yaml
import json
from pathlib import Path

def verify_file_structure():
    """Verify all required files are present"""
    required_files = [
        "main.py",
        "requirements.txt",
        "Dockerfile",
        "test_smoke.py",
        "run.sh",
        "README.md",
        ".env.example"
    ]

    api_dir = Path("/Volumes/DATA/FREEDOM/services/api")
    missing_files = []

    for file in required_files:
        if not (api_dir / file).exists():
            missing_files.append(file)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def verify_docker_compose():
    """Verify docker-compose configuration"""
    try:
        with open("/Volumes/DATA/FREEDOM/docker-compose.yml", 'r') as f:
            config = yaml.safe_load(f)

        # Check if api service exists
        if 'api' not in config.get('services', {}):
            print("❌ API service not found in docker-compose.yml")
            return False

        api_service = config['services']['api']

        # Check required configuration
        required_keys = ['build', 'ports', 'environment', 'depends_on', 'healthcheck']
        missing_keys = [key for key in required_keys if key not in api_service]

        if missing_keys:
            print(f"❌ Missing docker-compose keys: {missing_keys}")
            return False

        # Check environment variables
        env = api_service.get('environment', {})
        required_env = ['FREEDOM_API_KEY', 'KB_SERVICE_URL', 'CORS_ORIGINS']
        missing_env = [var for var in required_env if var not in env]

        if missing_env:
            print(f"❌ Missing environment variables: {missing_env}")
            return False

        # Check if kb-service dependency exists
        if 'kb-service' not in config.get('services', {}):
            print("❌ KB service dependency not found")
            return False

        print("✅ Docker-compose configuration valid")
        return True

    except Exception as e:
        print(f"❌ Docker-compose validation failed: {e}")
        return False

def verify_python_imports():
    """Verify Python code can be imported without errors"""
    try:
        import ast

        # Parse main.py
        with open("/Volumes/DATA/FREEDOM/services/api/main.py", 'r') as f:
            main_code = f.read()

        ast.parse(main_code)

        # Parse test_smoke.py
        with open("/Volumes/DATA/FREEDOM/services/api/test_smoke.py", 'r') as f:
            test_code = f.read()

        ast.parse(test_code)

        print("✅ Python syntax validation passed")
        return True

    except SyntaxError as e:
        print(f"❌ Python syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Python validation failed: {e}")
        return False

def verify_requirements():
    """Verify requirements.txt contains necessary dependencies"""
    try:
        with open("/Volumes/DATA/FREEDOM/services/api/requirements.txt", 'r') as f:
            requirements = f.read()

        required_packages = [
            'fastapi',
            'uvicorn',
            'pydantic',
            'structlog',
            'prometheus-client',
            'httpx',
            'slowapi'
        ]

        missing_packages = []
        for package in required_packages:
            if package not in requirements:
                missing_packages.append(package)

        if missing_packages:
            print(f"❌ Missing required packages: {missing_packages}")
            return False

        print("✅ Requirements.txt contains all required packages")
        return True

    except Exception as e:
        print(f"❌ Requirements validation failed: {e}")
        return False

def verify_executable_files():
    """Verify scripts are executable"""
    scripts = [
        "/Volumes/DATA/FREEDOM/services/api/test_smoke.py",
        "/Volumes/DATA/FREEDOM/services/api/run.sh"
    ]

    for script in scripts:
        if not os.access(script, os.X_OK):
            print(f"❌ Script not executable: {script}")
            return False

    print("✅ All scripts are executable")
    return True

def verify_security_config():
    """Verify security configuration is proper"""
    try:
        with open("/Volumes/DATA/FREEDOM/services/api/main.py", 'r') as f:
            content = f.read()

        # Check for security features
        security_features = [
            'APIKeyHeader',
            'CORSMiddleware',
            'TrustedHostMiddleware',
            'rate_limit',
            'verify_api_key'
        ]

        missing_features = []
        for feature in security_features:
            if feature not in content:
                missing_features.append(feature)

        if missing_features:
            print(f"❌ Missing security features: {missing_features}")
            return False

        print("✅ Security configuration verified")
        return True

    except Exception as e:
        print(f"❌ Security verification failed: {e}")
        return False

def verify_monitoring_config():
    """Verify monitoring and observability features"""
    try:
        with open("/Volumes/DATA/FREEDOM/services/api/main.py", 'r') as f:
            content = f.read()

        # Check for monitoring features
        monitoring_features = [
            'prometheus_client',
            'Counter',
            'Histogram',
            'Gauge',
            'structlog',
            'correlation_id',
            '/metrics'
        ]

        missing_features = []
        for feature in monitoring_features:
            if feature not in content:
                missing_features.append(feature)

        if missing_features:
            print(f"❌ Missing monitoring features: {missing_features}")
            return False

        print("✅ Monitoring configuration verified")
        return True

    except Exception as e:
        print(f"❌ Monitoring verification failed: {e}")
        return False

def main():
    """Run all verification checks"""
    print("🔍 FREEDOM API Gateway Deployment Verification")
    print("=" * 50)

    checks = [
        ("File Structure", verify_file_structure),
        ("Docker Compose Config", verify_docker_compose),
        ("Python Syntax", verify_python_imports),
        ("Requirements", verify_requirements),
        ("Executable Scripts", verify_executable_files),
        ("Security Configuration", verify_security_config),
        ("Monitoring Configuration", verify_monitoring_config)
    ]

    passed = 0
    total = len(checks)

    for name, check_func in checks:
        print(f"\n📋 {name}:")
        if check_func():
            passed += 1
        else:
            print(f"   Failed: {name}")

    print("\n" + "=" * 50)
    print(f"📊 VERIFICATION RESULTS")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\n🎉 ALL VERIFICATION CHECKS PASSED!")
        print("✅ API Gateway is ready for deployment")
        print("\nNext steps:")
        print("1. Set FREEDOM_API_KEY environment variable")
        print("2. Set OPENAI_API_KEY for KB service")
        print("3. Run: docker-compose up -d")
        print("4. Test: python services/api/test_smoke.py")
        return True
    else:
        print(f"\n💥 {total - passed} VERIFICATION CHECKS FAILED!")
        print("❌ Fix the above issues before deployment")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)