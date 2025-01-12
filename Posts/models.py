from django.db import models

# Create your models here.
import threading
import time
import json
import sqlite3
from datetime import datetime


# Database Management
class LibraryDatabase:
    def __init__(self, db_name="library.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.setup_tables()

    def setup_tables(self):
        # Create books table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT,
                available INTEGER DEFAULT 1
            )
        """)
        # Create members table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                join_date TEXT NOT NULL
            )
        """)
        # Create borrow history table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS borrow_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                book_id INTEGER,
                borrow_date TEXT NOT NULL,
                return_date TEXT
            )
        """)
        self.conn.commit()

    def add_book(self, title, author, genre):
        self.cursor.execute("INSERT INTO books (title, author, genre) VALUES (?, ?, ?)", (title, author, genre))
        self.conn.commit()

    def add_member(self, name):
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO members (name, join_date) VALUES (?, ?)", (name, join_date))
        self.conn.commit()

    def borrow_book(self, member_id, book_id):
        borrow_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO borrow_history (member_id, book_id, borrow_date) VALUES (?, ?, ?)",
                            (member_id, book_id, borrow_date))
        self.cursor.execute("UPDATE books SET available = 0 WHERE id = ?", (book_id,))
        self.conn.commit()

    def return_book(self, book_id):
        return_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("UPDATE books SET available = 1 WHERE id = ?", (book_id,))
        self.cursor.execute("""
            UPDATE borrow_history SET return_date = ?
            WHERE book_id = ? AND return_date IS NULL
        """, (return_date, book_id))
        self.conn.commit()

    def list_books(self, available=None):
        if available is None:
            self.cursor.execute("SELECT * FROM books")
        else:
            self.cursor.execute("SELECT * FROM books WHERE available = ?", (1 if available else 0,))
        return self.cursor.fetchall()

    def list_members(self):
        self.cursor.execute("SELECT * FROM members")
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()


# Library Operations
class Library:
    def __init__(self):
        self.db = LibraryDatabase()

    def add_book(self):
        title = input("Enter book title: ")
        author = input("Enter book author: ")
        genre = input("Enter book genre: ")
        self.db.add_book(title, author, genre)
        print(f"Book '{title}' by {author} added successfully.")

    def add_member(self):
        name = input("Enter member name: ")
        self.db.add_member(name)
        print(f"Member '{name}' added successfully.")

    def borrow_book(self):
        member_id = int(input("Enter member ID: "))
        book_id = int(input("Enter book ID: "))
        self.db.borrow_book(member_id, book_id)
        print(f"Book ID {book_id} borrowed by Member ID {member_id}.")

    def return_book(self):
        book_id = int(input("Enter book ID to return: "))
        self.db.return_book(book_id)
        print(f"Book ID {book_id} returned successfully.")

    def list_books(self):
        available = input("List (1) Available, (0) Borrowed, or (Enter) All books? ").strip()
        if available == "1":
            books = self.db.list_books(available=True)
        elif available == "0":
            books = self.db.list_books(available=False)
        else:
            books = self.db.list_books()
        self.display_books(books)

    def list_members(self):
        members = self.db.list_members()
        print("\n=== Members List ===")
        for member in members:
            print(f"ID: {member[0]} | Name: {member[1]} | Joined: {member[2]}")
        print("====================")

    @staticmethod
    def display_books(books):
        print("\n=== Books List ===")
        for book in books:
            status = "Available" if book[4] else "Borrowed"
            print(f"ID: {book[0]} | Title: {book[1]} | Author: {book[2]} | Genre: {book[3]} | Status: {status}")
        print("===================")


# File Export
def export_books_to_file(library, filename="books.json"):
    books = library.db.list_books()
    data = [{"id": book[0], "title": book[1], "author": book[2], "genre": book[3], "available": bool(book[4])}
            for book in books]
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)
    print(f"Books exported to {filename} successfully.")


# Multithreading for Auto Save
class AutoSaveThread(threading.Thread):
    def __init__(self, library, interval=10):
        super().__init__()
        self.library = library
        self.interval = interval
        self.running = True

    def run(self):
        print("Auto-save thread started.")
        while self.running:
            time.sleep(self.interval)
            export_books_to_file(self.library, "books_autosave.json")
            print("Auto-saved books to books_autosave.json.")

    def stop(self):
        self.running = False
        print("Auto-save thread stopped.")


# Main Menu
def main():
    library = Library()
    auto_save_thread = AutoSaveThread(library)
    auto_save_thread.start()

    try:
        while True:
            print("\n=== Library Management ===")
            print("1. Add Book")
            print("2. Add Member")
            print("3. Borrow Book")
            print("4. Return Book")
            print("5. List Books")
            print("6. List Members")
            print("7. Export Books to File")
            print("8. Exit")

            choice = input("Enter your choice: ").strip()
            if choice == "1":
                library.add_book()
            elif choice == "2":
                library.add_member()
            elif choice == "3":
                library.borrow_book()
            elif choice == "4":
                library.return_book()
            elif choice == "5":
                library.list_books()
            elif choice == "6":
                library.list_members()
            elif choice == "7":
                filename = input("Enter filename (default: books.json): ").strip() or "books.json"
                export_books_to_file(library, filename)
            elif choice == "8":
                break
            else:
                print("Invalid choice. Please try again.")
    finally:
        auto_save_thread.stop()
        auto_save_thread.join()
        library.db.close()
        print("Goodbye!")


if __name__ == "__main__":
    main()
