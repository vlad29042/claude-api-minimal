#!/usr/bin/env python3
"""Test script for minimal server."""

import requests
import time
import subprocess
import sys
import signal

def test_server():
    """Test the minimal server."""

    API_URL = "http://localhost:8001/api/v1/chat"
    HEALTH_URL = "http://localhost:8001/health"
    API_KEY = "test-api-key-change-me-in-production"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print("🧪 Testing Minimal Claude Server\n")

    # Test 1: Health check
    print("1️⃣ Testing health endpoint...")
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        if response.status_code == 200:
            print(f"✅ Health check OK: {response.json()}\n")
        else:
            print(f"❌ Health check failed: {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}\n")
        return False

    # Test 2: Chat without session_id
    print("2️⃣ Testing chat endpoint (new session)...")
    try:
        payload = {
            "prompt": "Say hello in one word",
            "user_id": 1
        }

        print(f"Request: {payload}")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response received:")
            print(f"   Content: {data['content'][:100]}...")
            print(f"   Session ID: {data['session_id']}")
            print(f"   Cost: ${data['cost']}")
            print(f"   Duration: {data['duration_ms']}ms\n")

            session_id = data['session_id']

            # Test 3: Continue session
            print("3️⃣ Testing session continuation...")
            payload2 = {
                "prompt": "Now say goodbye in one word",
                "session_id": session_id,
                "user_id": 1
            }

            response2 = requests.post(API_URL, headers=headers, json=payload2, timeout=30)

            if response2.status_code == 200:
                data2 = response2.json()
                print(f"✅ Session continued:")
                print(f"   Content: {data2['content'][:100]}...")
                print(f"   Session ID: {data2['session_id']}")
                print(f"   Same session: {data2['session_id'] == session_id}\n")
                return True
            else:
                print(f"❌ Session continuation failed: {response2.status_code}")
                print(f"   Error: {response2.text}\n")
                return False
        else:
            print(f"❌ Chat failed: {response.status_code}")
            print(f"   Error: {response.text}\n")
            return False

    except Exception as e:
        print(f"❌ Chat error: {e}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)
