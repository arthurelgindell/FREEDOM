#!/usr/bin/env python3
"""
Test script for UI-TARS-1.5-7B-mlx-bf16 vision-language model
"""

import sys
from mlx_vlm import load, generate
from PIL import Image
import requests
from io import BytesIO

def test_model_loading():
    """Test if the model can be loaded"""
    print("Loading UI-TARS-1.5-7B-mlx-bf16 model...")
    try:
        model_path = "./models/portalAI/UI-TARS-1.5-7B-mlx-bf16"
        model, processor = load(model_path)
        print(f"✓ Model loaded successfully")
        return model, processor
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        return None, None

def create_test_image():
    """Create a simple test image"""
    try:
        # Create a simple colored rectangle
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (400, 300), color='lightblue')
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 350, 250], fill='white', outline='black', width=2)
        draw.text((200, 150), "Test UI", fill='black', anchor='mm')
        return img
    except Exception as e:
        print(f"Error creating test image: {e}")
        return None

def test_text_only_prompts(model, processor):
    """Test text-only prompts"""
    print("\n=== Testing Text-Only Prompts ===")

    text_prompts = [
        "What is UI automation?",
        "Explain the purpose of a user interface",
        "How would you click a button in a web application?"
    ]

    for prompt in text_prompts:
        try:
            print(f"\nPrompt: {prompt}")
            # For text-only, pass an empty image or skip image parameter
            response = generate(model, processor, image=None, prompt=prompt, max_tokens=100, temp=0.7)
            print(f"Response: {response}")
        except Exception as e:
            print(f"✗ Error with prompt '{prompt}': {e}")
            # Try alternative approach - create a blank image
            try:
                blank_img = Image.new('RGB', (100, 100), color='white')
                response = generate(model, processor, image=blank_img, prompt=prompt, max_tokens=100, temp=0.7)
                print(f"Response (with blank image): {response}")
            except Exception as e2:
                print(f"✗ Fallback also failed: {e2}")

def test_image_prompts(model, processor):
    """Test image + text prompts"""
    print("\n=== Testing Image + Text Prompts ===")

    # Create test image
    test_img = create_test_image()
    if test_img is None:
        print("✗ Could not create test image")
        return

    image_prompts = [
        "Describe what you see in this image",
        "What UI elements are visible?",
        "How would you interact with this interface?",
        "What color is the background?"
    ]

    for prompt in image_prompts:
        try:
            print(f"\nPrompt: {prompt}")
            response = generate(model, processor, image=test_img, prompt=prompt, max_tokens=150, temp=0.7)
            print(f"Response: {response}")
        except Exception as e:
            print(f"✗ Error with image prompt '{prompt}': {e}")

def main():
    """Main test function"""
    print("Starting UI-TARS model tests...")

    # Load model
    model, processor = test_model_loading()
    if model is None:
        print("Cannot proceed without model")
        sys.exit(1)

    # Test text prompts
    test_text_only_prompts(model, processor)

    # Test image prompts
    test_image_prompts(model, processor)

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()