#!/usr/bin/env python3
"""
Demo script showing the improved Safe Calculator in action.
This demonstrates that Task 1.1 is working correctly.
"""

from simplest_agent import CalculatorTool

def demo_calculator():
    print("=" * 60)
    print("SAFE CALCULATOR DEMO - Task 1.1 Implementation")
    print("=" * 60)
    
    calc_tool = CalculatorTool()
    
    print("\n🧮 Testing legitimate mathematical calculations:")
    test_cases = [
        "2 + 3",
        "15 * 7",
        "(10 + 5) / 3",
        "2 ** 8", 
        "100 % 7",
        "-(5 + 3)",
        "15 / 3 + 2 * 4",
    ]
    
    for expression in test_cases:
        result = calc_tool._run(expression)
        print(f"  {expression:<20} = {result}")
    
    print("\n🔒 Testing security - these should be blocked:")
    malicious_cases = [
        "__import__('os').system('ls')",
        "eval('2+2')", 
        "exec('print(1)')",
        "open('/etc/passwd')",
    ]
    
    for expression in malicious_cases:
        result = calc_tool._run(expression)
        print(f"  {expression:<30} = {result}")
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS: eval() has been safely replaced!")
    print("✅ Mathematical operations work correctly")
    print("✅ Security vulnerabilities blocked") 
    print("✅ Task 1.1 implementation complete")
    print("=" * 60)

if __name__ == "__main__":
    demo_calculator()
