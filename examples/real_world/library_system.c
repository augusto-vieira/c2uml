#include <stdio.h>
#include <string.h>
#include "library_system.h"

// Function to add a book
void add_book(Book books[], int *count, int id, const char *title, const char *author) {
    if (*count < MAX_BOOKS) {
        books[*count].id = id;
        strcpy(books[*count].title, title);
        strcpy(books[*count].author, author);
        books[*count].is_available = 1;
        (*count)++;
        printf("Book '%s' by %s added successfully.\n", title, author);
    } else {
        printf("Cannot add more books. Maximum limit reached.\n");
    }
}

// Function to borrow a book
void borrow_book(Book books[], int count, int id) {
    for (int i = 0; i < count; i++) {
        if (books[i].id == id) {
            if (books[i].is_available) {
                books[i].is_available = 0;
                printf("You have borrowed '%s'.\n", books[i].title);
            } else {
                printf("Sorry, '%s' is currently unavailable.\n", books[i].title);
            }
            return;
        }
    }
    printf("Book with ID %d not found.\n", id);
}

// Function to return a book
void return_book(Book books[], int count, int id) {
    for (int i = 0; i < count; i++) {
        if (books[i].id == id) {
            if (!books[i].is_available) {
                books[i].is_available = 1;
                printf("You have returned '%s'.\n", books[i].title);
            } else {
                printf("This book was not borrowed.\n");
            }
            return;
        }
    }
    printf("Book with ID %d not found.\n", id);
}

int main() {
    Book books[MAX_BOOKS];
    int book_count = 0;

    add_book(books, &book_count, 1, "1984", "George Orwell");
    add_book(books, &book_count, 2, "To Kill a Mockingbird", "Harper Lee");
    add_book(books, &book_count, 3, "The Great Gatsby", "F. Scott Fitzgerald");

    borrow_book(books, book_count, 2);
    borrow_book(books, book_count, 2);
    return_book(books, book_count, 2);
    borrow_book(books, book_count, 2);

    return 0;
}