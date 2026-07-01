#ifndef LIBRARY_SYSTEM_H
#define LIBRARY_SYSTEM_H

#define MAX_BOOKS 100

// Structure to represent a book
typedef struct {
    int id;
    char title[100];
    char author[100];
    int is_available;
} Book;

// Function prototypes
void add_book(Book books[], int *count, int id, const char *title, const char *author);
void borrow_book(Book books[], int count, int id);
void return_book(Book books[], int count, int id);

#endif // LIBRARY_SYSTEM_H