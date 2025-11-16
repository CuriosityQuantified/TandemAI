/**
 * Simple JavaScript test file for syntax highlighting
 */

function calculateSum(a, b) {
    return a + b;
}

class Person {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }

    greet() {
        console.log(`Hello, my name is ${this.name} and I'm ${this.age} years old.`);
    }
}

// Test the function
const result = calculateSum(5, 10);
console.log(`Sum: ${result}`);

// Create a person
const person = new Person("Bob", 30);
person.greet();

// Array operations
const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(n => n * 2);
console.log("Doubled:", doubled);
