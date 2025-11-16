/**
 * Simple TypeScript test file for syntax highlighting
 */

interface User {
    name: string;
    age: number;
    email?: string;
}

function calculateSum(a: number, b: number): number {
    return a + b;
}

class Person implements User {
    name: string;
    age: number;
    email?: string;

    constructor(name: string, age: number, email?: string) {
        this.name = name;
        this.age = age;
        this.email = email;
    }

    greet(): void {
        console.log(`Hello, my name is ${this.name} and I'm ${this.age} years old.`);
    }
}

// Test the function
const result: number = calculateSum(5, 10);
console.log(`Sum: ${result}`);

// Create a person
const person: Person = new Person("Charlie", 35, "charlie@example.com");
person.greet();

// Generic function
function identity<T>(arg: T): T {
    return arg;
}
