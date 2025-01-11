# Bookmark Manager - README

## Introduction

**Bookmark Manager** is a versatile desktop application for managing, organizing, and cleaning up bookmarks stored in XML files. The program is particularly useful for users with large collections of bookmarks that need sorting, categorization, or deduplication. With its intuitive interface, it enables you to add, rename, or remove categories, tag bookmarks, and identify duplicate entries effortlessly.

This tool is ideal for anyone who values a structured and clutter-free approach to bookmark organization.

---

## Features Overview

- **Explorer Mode**: Navigate, add, remove, and categorize bookmarks easily.
- **Deduplication**: Identify and remove duplicate bookmarks based on their normalized URLs.
- **Drag-and-Drop Support**: Organize bookmarks across categories using an intuitive drag-and-drop interface.
- **Tag Management**: Add, remove, or filter bookmarks using tags for enhanced organization.
- **Custom XML Support**: Create and manage bookmark collections in XML format.
- **Bookmark Sorting**: Alphabetically sort categories and bookmarks for easier navigation.
- **Automatic Bookmark Title Extraction**: Fetch titles for bookmarks directly from their URLs.

---

## Getting Started

Follow these steps to download and run the Bookmark Manager application:

### Step 1: Download the Application
1. Visit the repository page on GitHub.
2. Locate the **Code** button and select **Download ZIP**.
3. Save the ZIP file to a location on your computer.

### Step 2: Extract the ZIP File
1. Navigate to the location where you downloaded the ZIP file.
2. Right-click the ZIP file and select **Extract All** or use your preferred extraction tool.
3. Choose a destination folder for the extracted files and confirm.

### Step 3: Run the Program
1. Open the extracted folder.
2. Locate the `bookmark-manager.py` file.
3. Double-click `bookmark-manager.py` to launch the application.

**Note**: This program requires Python 3.x to run. Additionally, it uses external libraries that are not included in a `requirements.txt`. Users are responsible for ensuring all necessary dependencies are installed.

---

## Use Cases and Examples

### Scenario 1: Organizing Bookmarks into Categories
Do you have a large collection of bookmarks saved haphazardly? Use **Bookmark Manager** to:
- Create meaningful categories like "Work", "Hobbies", "Travel", and "Learning."
- Drag and drop bookmarks into their respective categories for better organization.

### Scenario 2: Cleaning Up Duplicate Bookmarks
Tired of seeing the same bookmark multiple times? The **Deduper** tab lets you:
- Automatically group duplicate bookmarks by normalized URLs.
- Quickly remove redundant entries while keeping one copy.

### Scenario 3: Adding Tags for Quick Filtering
Want to group bookmarks across categories? Add tags like `research`, `important`, or `wishlist` to your bookmarks. Later, use the filter feature to display only bookmarks with specific tags.

### Scenario 4: Creating a New Bookmark Collection
Starting from scratch? Use the **Create Empty XML** button to generate a blank XML file. Then, populate it with your bookmarks and categories.

---

## Disclaimers and Updates

1. The **Bookmark Manager** is an evolving tool, and the repository may be updated without prior notice.
2. Updates to the code may render this README outdated. Users are encouraged to check for changes to the repository if issues arise.
3. A `requirements.txt` file is not provided. Users must independently ensure the required Python libraries are installed.

---

## Notes and Recommendations

- **Dependencies**: To run the program, ensure the following Python libraries are installed:
  - `tkinter` (standard library for GUI applications in Python)
  - `requests` (for fetching titles from URLs)
  - `xml.etree.ElementTree` (for XML parsing, included in Python's standard library)

- **Compatibility**: This application is optimized for modern desktop environments and may require additional setup for older systems.

By following these instructions and examples, users can efficiently manage their bookmarks and maintain an organized collection with minimal effort.
