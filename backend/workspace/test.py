#!/usr/bin/env python3
"""
Simple Python test file for syntax highlighting
"""

def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers."""
    return a + b

class Person:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def greet(self):
        print(f"Hello, my name is {self.name} and I'm {self.age} years old.")

if __name__ == "__main__":
    # Test the function
    result = calculate_sum(5, 10)
    print(f"Sum: {result}")

    # Create a person
    person = Person("Alice", 25)
    person.greet()
