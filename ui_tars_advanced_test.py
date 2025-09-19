#!/usr/bin/env python3
"""
Advanced test for UI-TARS-1.5-7B-mlx-bf16 vision-language model
Testing UI automation specific capabilities
"""

from mlx_vlm import load, generate
from PIL import Image, ImageDraw, ImageFont
import sys
import os

def create_ui_mockup():
    """Create a realistic UI mockup for testing"""
    img = Image.new('RGB', (800, 600), color='#f0f0f0')
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([0, 0, 800, 60], fill='#2c3e50')
    draw.text((20, 20), "My App Dashboard", fill='white')

    # Navigation buttons
    buttons = ['Home', 'Profile', 'Settings', 'Logout']
    for i, btn in enumerate(buttons):
        x = 600 + i * 80
        draw.rectangle([x, 15, x+70, 45], fill='#3498db', outline='#2980b9')
        draw.text((x+10, 25), btn, fill='white')

    # Main content area
    draw.rectangle([50, 100, 750, 500], fill='white', outline='#bdc3c7')

    # Form elements
    draw.text((70, 120), "User Information Form", fill='#2c3e50')

    # Input fields
    fields = ['Name:', 'Email:', 'Phone:']
    for i, field in enumerate(fields):
        y = 160 + i * 60
        draw.text((70, y), field, fill='#34495e')
        draw.rectangle([150, y-5, 400, y+25], fill='white', outline='#95a5a6')

    # Buttons
    draw.rectangle([70, 400, 150, 430], fill='#27ae60', outline='#229954')
    draw.text((95, 410), "Submit", fill='white')

    draw.rectangle([170, 400, 250, 430], fill='#e74c3c', outline='#c0392b')
    draw.text((195, 410), "Cancel", fill='white')

    # Status indicator
    draw.ellipse([600, 120, 620, 140], fill='#f39c12')
    draw.text((630, 125), "Online", fill='#f39c12')

    return img

def test_ui_specific_prompts(model, processor):
    """Test UI automation specific prompts"""
    print("\n=== Testing UI Automation Specific Prompts ===")

    ui_mockup = create_ui_mockup()

    ui_prompts = [
        "What interactive elements can you identify in this interface?",
        "How would you fill out the form shown in this UI?",
        "List all the clickable buttons visible in this interface",
        "What is the color scheme of this application?",
        "Describe the layout structure of this interface",
        "How would you navigate to the Settings page?",
        "What form validation might be needed for this interface?",
        "Identify any status indicators in this UI"
    ]

    for prompt in ui_prompts:
        try:
            print(f"\n{'='*50}")
            print(f"Prompt: {prompt}")
            print(f"{'='*50}")
            response = generate(model, processor, image=ui_mockup, prompt=prompt, max_tokens=200, temp=0.6)
            print(f"Response: {response.text.strip()}")
            print(f"Stats: {response.generation_tokens} tokens, {response.generation_tps:.1f} tokens/sec")
        except Exception as e:
            print(f"✗ Error: {e}")

def test_automation_scenarios(model, processor):
    """Test automation scenario understanding"""
    print("\n=== Testing Automation Scenarios ===")

    # Create different UI scenarios
    scenarios = [
        {
            "name": "Login Screen",
            "image": create_login_screen(),
            "prompts": [
                "How would you automate logging into this application?",
                "What elements need to be located for automated testing?",
                "Describe the test steps for this login form"
            ]
        },
        {
            "name": "Data Table",
            "image": create_data_table(),
            "prompts": [
                "How would you automate data validation in this table?",
                "What sorting and filtering operations are possible?",
                "Describe how to automate row selection"
            ]
        }
    ]

    for scenario in scenarios:
        print(f"\n--- {scenario['name']} Scenario ---")
        for prompt in scenario['prompts']:
            try:
                print(f"\nPrompt: {prompt}")
                response = generate(model, processor, image=scenario['image'], prompt=prompt, max_tokens=150, temp=0.6)
                print(f"Response: {response.text.strip()}")
            except Exception as e:
                print(f"✗ Error: {e}")

def create_login_screen():
    """Create a login screen mockup"""
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((150, 50), "Login", fill='#2c3e50')

    # Username field
    draw.text((50, 100), "Username:", fill='#34495e')
    draw.rectangle([50, 120, 350, 150], fill='white', outline='#95a5a6')

    # Password field
    draw.text((50, 170), "Password:", fill='#34495e')
    draw.rectangle([50, 190, 350, 220], fill='white', outline='#95a5a6')

    # Login button
    draw.rectangle([50, 240, 150, 270], fill='#3498db', outline='#2980b9')
    draw.text((85, 250), "Login", fill='white')

    return img

def create_data_table():
    """Create a data table mockup"""
    img = Image.new('RGB', (600, 400), color='white')
    draw = ImageDraw.Draw(img)

    # Table header
    headers = ['ID', 'Name', 'Email', 'Status']
    for i, header in enumerate(headers):
        x = 50 + i * 130
        draw.rectangle([x, 50, x+120, 80], fill='#34495e')
        draw.text((x+10, 60), header, fill='white')

    # Table rows
    data = [
        ['001', 'John Doe', 'john@email.com', 'Active'],
        ['002', 'Jane Smith', 'jane@email.com', 'Inactive'],
        ['003', 'Bob Johnson', 'bob@email.com', 'Active']
    ]

    for row_idx, row in enumerate(data):
        y = 80 + (row_idx + 1) * 30
        for col_idx, cell in enumerate(row):
            x = 50 + col_idx * 130
            draw.rectangle([x, y, x+120, y+30], fill='#ecf0f1', outline='#bdc3c7')
            draw.text((x+5, y+5), cell, fill='#2c3e50')

    return img

def main():
    """Main test function"""
    print("Starting Advanced UI-TARS Model Tests...")
    print("Loading model...")

    try:
        model_path = "./models/portalAI/UI-TARS-1.5-7B-mlx-bf16"
        model, processor = load(model_path)
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        sys.exit(1)

    # Run tests
    test_ui_specific_prompts(model, processor)
    test_automation_scenarios(model, processor)

    print("\n=== Advanced Test Complete ===")

if __name__ == "__main__":
    main()