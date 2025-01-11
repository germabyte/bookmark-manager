import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import urllib.parse
import requests
import re
import html  # for HTML entity decoding
from collections import defaultdict

class SafavorCleanerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Bookmark Manager")

        # Data structures
        self.xml_tree = None
        self.xml_root = None
        
        # groups: { normalized_url : [ (link_elem, original_url), ... ] }
        self.links_by_group = {}
        
        # categories: { catID : catName }
        self.categories = {}
        
        # We store TreeView group-IDs in an ordered list for display (Deduper tab)
        self.group_ids = []
        
        # map each link_elem -> child_item_id in the Deduper TreeView for easy reference
        self.link_to_tree_id = {}
        
        # Keep track of the currently selected link XML element (Deduper tab)
        self.current_selected_link = None

        # For the Explorer tab
        self.last_added_category_name = None

        # For Drag & Drop
        self.drag_mode = False
        self.dragging_items = None  # list of selected item IDs
        self.drag_tooltip = None
        self.drag_tooltip_label = None

        # TAG/FILTER
        self.filter_mode = False
        self.filter_tags = set()
        self.hidden_items = []

        # -------------
        # UI: NOTEBOOK
        # -------------
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Top-level toolbar (common for both tabs)
        self._build_top_toolbar()

        # ============================
        # TAB 1: EXPLORER (FIRST)
        # ============================
        self.explorer_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.explorer_frame, text="Explorer")

        self._build_explorer_tab()

        # ============================
        # TAB 2: DEDUPER (SECOND)
        # ============================
        self.deduper_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.deduper_frame, text="Deduper")
        
        self._build_deduper_tab()

        # Status label (bottom)
        self.status_label = tk.Label(self.master, text="Load an XML file to begin.")
        self.status_label.pack(pady=(0, 5))

    # --------------------------------------------------------------------------
    #  UI BUILDERS
    # --------------------------------------------------------------------------
    def _build_top_toolbar(self):
        """Build the top row of buttons that are always visible."""
        self.top_frame = tk.Frame(self.master)
        self.top_frame.pack(fill=tk.X, padx=5, pady=5)

        # Load & Save
        self.btn_load = tk.Button(self.top_frame, text="Load XML", command=self.load_xml)
        self.btn_load.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_save = tk.Button(self.top_frame, text="Save XML", command=self.save_xml, state=tk.DISABLED)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        # Create Empty XML
        self.btn_create_empty_xml = tk.Button(self.top_frame, text="Create Empty XML", command=self.create_empty_xml)
        self.btn_create_empty_xml.pack(side=tk.LEFT, padx=5)

    def _build_explorer_tab(self):
        """
        Build the "explorer-like" interface: categories as folders, bookmarks as items.
        Also add buttons to manage categories and add bookmarks, plus sorting.
        """
        # Top frame for category management
        cat_mgmt_frame = tk.LabelFrame(self.explorer_frame, text="Manage Categories")
        cat_mgmt_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.btn_add_category = tk.Button(cat_mgmt_frame, text="Add Category", command=self.add_category, state=tk.DISABLED)
        self.btn_add_category.pack(side=tk.LEFT, padx=5)

        self.btn_rename_category = tk.Button(cat_mgmt_frame, text="Rename Category", command=self.rename_category, state=tk.DISABLED)
        self.btn_rename_category.pack(side=tk.LEFT, padx=5)

        self.btn_remove_category = tk.Button(cat_mgmt_frame, text="Remove Category", command=self.remove_category, state=tk.DISABLED)
        self.btn_remove_category.pack(side=tk.LEFT, padx=5)

        # Buttons to sort categories/bookmarks
        sort_frame = tk.LabelFrame(self.explorer_frame, text="Sorting")
        sort_frame.pack(fill=tk.X, padx=5, pady=5)

        self.btn_sort_cats = tk.Button(sort_frame, text="Sort Categories by Title", command=self.sort_categories, state=tk.DISABLED)
        self.btn_sort_cats.pack(side=tk.LEFT, padx=5)

        self.btn_sort_bmks = tk.Button(sort_frame, text="Sort Bookmarks by URL", command=self.sort_bookmarks, state=tk.DISABLED)
        self.btn_sort_bmks.pack(side=tk.LEFT, padx=5)

        # Frame for "Add Bookmark"
        bookmark_mgmt_frame = tk.LabelFrame(self.explorer_frame, text="Add New Bookmark")
        bookmark_mgmt_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(bookmark_mgmt_frame, text="URL: ").pack(side=tk.LEFT, padx=2)
        self.new_url_entry = tk.Entry(bookmark_mgmt_frame, width=40)
        self.new_url_entry.pack(side=tk.LEFT, padx=2)

        tk.Label(bookmark_mgmt_frame, text="Category: ").pack(side=tk.LEFT, padx=2)
        self.new_bmk_cat_combo = ttk.Combobox(bookmark_mgmt_frame, state="readonly", width=25)
        self.new_bmk_cat_combo.pack(side=tk.LEFT, padx=2)

        self.btn_add_bookmark = tk.Button(bookmark_mgmt_frame, text="Add Bookmark", command=self.add_bookmark, state=tk.DISABLED)
        self.btn_add_bookmark.pack(side=tk.LEFT, padx=5)

        # Drag & Drop toggle
        self.drag_drop_btn = tk.Button(bookmark_mgmt_frame, text="Enable Drag & Drop", command=self.toggle_drag_drop, state=tk.DISABLED)
        self.drag_drop_btn.pack(side=tk.LEFT, padx=10)

        # Additional buttons (second row in Explorer)
        explorer_button_frame = tk.Frame(self.explorer_frame)
        explorer_button_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.btn_copy_url = tk.Button(explorer_button_frame, text="Copy Selected Bookmark URL", 
                                      command=self.copy_selected_bookmark_url, state=tk.DISABLED)
        self.btn_copy_url.pack(side=tk.LEFT, padx=5)

        self.btn_delete_bookmark = tk.Button(explorer_button_frame, text="Delete Selected Bookmark(s)", 
                                             command=self.delete_selected_bookmarks, state=tk.DISABLED)
        self.btn_delete_bookmark.pack(side=tk.LEFT, padx=5)

        # TAGS & FILTER
        self.btn_add_tags = tk.Button(explorer_button_frame, text="Add Tags to Selected Bookmarks",
                                      command=self.add_tags_to_selected, state=tk.DISABLED)
        self.btn_add_tags.pack(side=tk.LEFT, padx=5)

        self.btn_remove_tags = tk.Button(explorer_button_frame, text="Remove Tags from Selected Bookmarks",
                                         command=self.remove_tags_from_selected, state=tk.DISABLED)
        self.btn_remove_tags.pack(side=tk.LEFT, padx=5)

        self.btn_filter_by_tag = tk.Button(explorer_button_frame, text="Enable Filter by Tag",
                                           command=self.toggle_filter_by_tag, state=tk.DISABLED)
        self.btn_filter_by_tag.pack(side=tk.LEFT, padx=5)

        # Explorer Tree
        self.explorer_tree_frame = tk.Frame(self.explorer_frame)
        self.explorer_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,5))

        # =============== MAJOR CHANGE HERE =================
        # We now have 2 "data" columns: "URL" and "Tags"
        self.explorer_tree = ttk.Treeview(
            self.explorer_tree_frame,
            columns=("URL", "Tags"),
            show="tree headings"
        )
        self.explorer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.explorer_tree.heading("#0", text="Category / Bookmark Name")
        self.explorer_tree.heading("URL", text="Bookmark URL")
        self.explorer_tree.heading("Tags", text="Tags")

        self.explorer_tree.column("#0", width=250, stretch=True)
        self.explorer_tree.column("URL", width=400, stretch=True)
        self.explorer_tree.column("Tags", width=180, stretch=True)
        # =============== END CHANGE ========================

        # Scrollbar
        self.explorer_scrollbar = tk.Scrollbar(self.explorer_tree_frame, orient="vertical", command=self.explorer_tree.yview)
        self.explorer_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.explorer_tree.configure(yscrollcommand=self.explorer_scrollbar.set)
        
        # Binding
        self.explorer_tree.bind("<<TreeviewSelect>>", self.on_explorer_select)
        self.explorer_tree.bind("<ButtonPress-1>", self.on_tree_button_press)
        self.explorer_tree.bind("<B1-Motion>", self.on_tree_motion)
        self.explorer_tree.bind("<ButtonRelease-1>", self.on_tree_button_release)

    def _build_deduper_tab(self):
        """
        Build the deduper UI (mark/unmark/remove, expand/collapse),
        plus a TreeView for grouped duplicates.
        """
        # Frame for the deduper-specific buttons
        self.deduper_buttons = tk.Frame(self.deduper_frame)
        self.deduper_buttons.pack(fill=tk.X, padx=5, pady=5)

        self.btn_mark_all_but_one = tk.Button(self.deduper_buttons, text="Mark Duplicates (All but One)", 
                                              command=self.mark_all_but_one, state=tk.DISABLED)
        self.btn_mark_all_but_one.pack(side=tk.LEFT, padx=5)
        
        self.btn_remove_marked = tk.Button(self.deduper_buttons, text="Remove Marked Items", 
                                           command=self.remove_marked, state=tk.DISABLED)
        self.btn_remove_marked.pack(side=tk.LEFT, padx=5)
        
        self.btn_unmark_selected = tk.Button(self.deduper_buttons, text="Unmark Selected", 
                                             command=self.unmark_selected, state=tk.DISABLED)
        self.btn_unmark_selected.pack(side=tk.LEFT, padx=5)
        
        # Expand/Collapse all
        self.btn_expand_all = tk.Button(self.deduper_buttons, text="Expand All", 
                                        command=lambda: self.expand_collapse_all(True), state=tk.DISABLED)
        self.btn_expand_all.pack(side=tk.LEFT, padx=5)
        
        self.btn_collapse_all = tk.Button(self.deduper_buttons, text="Collapse All", 
                                          command=lambda: self.expand_collapse_all(False), state=tk.DISABLED)
        self.btn_collapse_all.pack(side=tk.LEFT, padx=5)

        # Refresh
        self.btn_refresh = tk.Button(
            self.deduper_buttons, text="Refresh",
            command=self.refresh_deduper, state=tk.NORMAL
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=5)
        
        # Deduper tree
        self.tree_frame = tk.Frame(self.deduper_frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Columns = OriginalURL, Category, Marked
        self.tree = ttk.Treeview(
            self.tree_frame, 
            columns=("OriginalURL", "Category", "Marked"), 
            show="tree headings"
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.tree.heading("#0", text="Duplicate Groups")
        self.tree.heading("OriginalURL", text="Original URL")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Marked", text="Marked")
        
        self.tree.column("#0", stretch=True, width=280)
        self.tree.column("OriginalURL", width=250)
        self.tree.column("Category", width=150)
        self.tree.column("Marked", anchor=tk.CENTER, width=60)
        
        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind selection and double-click
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # Bottom panel (for category reassignment)
        self.bottom_frame = tk.LabelFrame(self.deduper_frame, text="Change Category of Selected Link")
        self.bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(self.bottom_frame, text="Category: ").pack(side=tk.LEFT, padx=(5, 2))
        self.category_combo = ttk.Combobox(self.bottom_frame, state="readonly")
        self.category_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_apply_category = tk.Button(self.bottom_frame, text="Apply", command=self.apply_category, state=tk.DISABLED)
        self.btn_apply_category.pack(side=tk.LEFT, padx=5)
        
        self.category_combo.config(values=["<No categories loaded>"])
        self.category_combo.current(0)

    # --------------------------------------------------------------------------
    # 1. LOADING AND PARSING
    # --------------------------------------------------------------------------
    def load_xml(self):
        file_path = filedialog.askopenfilename(
            title="Open Safavor XML",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            self.xml_tree = ET.parse(file_path)
            self.xml_root = self.xml_tree.getroot()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse XML: {e}")
            return
        
        # Clear UI (both deduper tree and explorer tree)
        for child in self.tree.get_children():
            self.tree.delete(child)
        self.links_by_group.clear()
        self.categories.clear()
        self.group_ids.clear()
        self.link_to_tree_id.clear()
        self.current_selected_link = None

        for child in self.explorer_tree.get_children():
            self.explorer_tree.delete(child)

        # Reset filtering state
        self.filter_mode = False
        self.filter_tags.clear()
        self.hidden_items.clear()
        self.btn_filter_by_tag.config(text="Enable Filter by Tag")

        # Load categories
        self._load_categories()

        # Populate Category combos
        self._populate_category_combo()

        # Build deduper grouping
        self._group_links()
        self._populate_deduper_tree()

        # Build explorer tree
        self._populate_explorer_tree()

        # Enable UI components
        self.btn_save.config(state=tk.NORMAL)
        self.btn_mark_all_but_one.config(state=tk.NORMAL)
        self.btn_remove_marked.config(state=tk.NORMAL)
        self.btn_unmark_selected.config(state=tk.NORMAL)
        self.btn_expand_all.config(state=tk.NORMAL)
        self.btn_collapse_all.config(state=tk.NORMAL)

        self.btn_add_category.config(state=tk.NORMAL)
        self.btn_rename_category.config(state=tk.NORMAL)
        self.btn_remove_category.config(state=tk.NORMAL)
        self.btn_add_bookmark.config(state=tk.NORMAL)
        self.btn_sort_cats.config(state=tk.NORMAL)
        self.btn_sort_bmks.config(state=tk.NORMAL)
        self.drag_drop_btn.config(state=tk.NORMAL)
        self.btn_copy_url.config(state=tk.NORMAL)
        self.btn_delete_bookmark.config(state=tk.NORMAL)
        self.btn_add_tags.config(state=tk.NORMAL)
        self.btn_remove_tags.config(state=tk.NORMAL)
        self.btn_filter_by_tag.config(state=tk.NORMAL)

        self.status_label.config(text="XML loaded. Duplicates are grouped by normalized URL.")

    def _load_categories(self):
        self.categories.clear()
        for cat_elem in self.xml_root.findall("Kategorien"):
            cat_id_elem = cat_elem.find("ID")
            cat_name_elem = cat_elem.find("Kategorie")
            if cat_id_elem is not None and cat_name_elem is not None:
                cat_id = cat_id_elem.text.strip()
                cat_name = cat_name_elem.text.strip()
                self.categories[cat_id] = cat_name

    def _populate_category_combo(self):
        if self.categories:
            cat_names_sorted = sorted(self.categories.values())
            self.category_combo.config(values=cat_names_sorted)
            self.new_bmk_cat_combo.config(values=cat_names_sorted)
            self.category_combo.current(0)
            self.new_bmk_cat_combo.current(0)
        else:
            self.category_combo.config(values=["<No categories found>"])
            self.category_combo.current(0)
            self.new_bmk_cat_combo.config(values=["<No categories found>"])
            self.new_bmk_cat_combo.current(0)

    def _group_links(self):
        for link in self.xml_root.findall("Links"):
            url_elem = link.find("URL")
            raw_url = (url_elem.text.strip() if url_elem is not None and url_elem.text else "")
            
            if not raw_url:
                norm_url = "<EMPTY_URL>"
            else:
                norm_url = self.normalize_url(raw_url)
            
            if norm_url not in self.links_by_group:
                self.links_by_group[norm_url] = []
            self.links_by_group[norm_url].append((link, raw_url))
        
        self.group_ids = sorted(self.links_by_group.keys())

    def normalize_url(self, raw_url):
        temp_url = raw_url.strip()
        if not temp_url.startswith(("http://", "https://")):
            temp_url = "http://" + temp_url
        
        parsed = urllib.parse.urlparse(temp_url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/")
        
        if path:
            norm = f"{netloc}{path}"
        else:
            norm = netloc
        
        return norm

    # --------------------------------------------------------------------------
    # 2A. POPULATING THE TREE (DEDUPER)
    # --------------------------------------------------------------------------
    def _populate_deduper_tree(self):
        group_index = 1
        for norm_url in self.group_ids:
            link_tuples = self.links_by_group[norm_url]
            if len(link_tuples) <= 1:
                continue

            group_label = f"Group {group_index}: {norm_url}"
            group_index += 1

            group_item_id = self.tree.insert(
                "",
                "end",
                text=group_label,
                values=("", "", ""),
                open=False
            )
            
            for link_elem, orig_url in link_tuples:
                kat_id = self._safe_find_text(link_elem, "KategorieID")
                category_name = self.categories.get(kat_id, f"<Unknown:{kat_id}>")
                
                marked = "No"
                child_item_id = self.tree.insert(
                    group_item_id,
                    "end",
                    text="",
                    values=(orig_url, category_name, marked)
                )
                self.link_to_tree_id[link_elem] = child_item_id

    # --------------------------------------------------------------------------
    # 2B. POPULATING THE TREE (EXPLORER)
    # --------------------------------------------------------------------------
    def _populate_explorer_tree(self):
        links_by_cat = {}
        for link_elem in self.xml_root.findall("Links"):
            cat_id = self._safe_find_text(link_elem, "KategorieID")
            if cat_id not in links_by_cat:
                links_by_cat[cat_id] = []
            links_by_cat[cat_id].append(link_elem)

        for cat_id, cat_name in self.categories.items():
            cat_item_id = self.explorer_tree.insert(
                "", 
                "end", 
                text=cat_name, 
                values=("", ""),
                open=False
            )
            if cat_id in links_by_cat:
                for link_elem in links_by_cat[cat_id]:
                    url = self._safe_find_text(link_elem, "URL")
                    title_text = self._safe_find_text(link_elem, "Title")
                    if not title_text:
                        title_text = url

                    # NEW: gather tags
                    tags_set = self._get_tags_for_link_elem(link_elem)
                    tags_str = ", ".join(sorted(tags_set))

                    self.explorer_tree.insert(
                        cat_item_id,
                        "end",
                        text=title_text,
                        # Now store URL as first column, tags as second
                        values=(url, tags_str)
                    )

        if self.last_added_category_name:
            self._expand_category_by_name(self.last_added_category_name)
            self.last_added_category_name = None

    def _expand_category_by_name(self, cat_name):
        for item in self.explorer_tree.get_children():
            if self.explorer_tree.item(item, "text") == cat_name:
                self.explorer_tree.item(item, open=True)
                break

    def _safe_find_text(self, elem, tag):
        child = elem.find(tag)
        return child.text.strip() if (child is not None and child.text) else ""

    # --------------------------------------------------------------------------
    # 3. EVENT HANDLING - DEDUPER
    # --------------------------------------------------------------------------
    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            self.current_selected_link = None
            self.btn_apply_category.config(state=tk.DISABLED)
            return
        
        sel_item = selected[0]
        parent = self.tree.parent(sel_item)
        
        if not parent:
            self.current_selected_link = None
            self.btn_apply_category.config(state=tk.DISABLED)
            return
        
        link_elem = self._find_link_by_tree_item(sel_item)
        if link_elem:
            self.current_selected_link = link_elem
            kat_id = self._safe_find_text(link_elem, "KategorieID")
            cat_name = self.categories.get(kat_id, f"<Unknown:{kat_id}>")
            
            all_values = list(self.category_combo["values"])
            if cat_name not in all_values:
                all_values.append(cat_name)
                self.category_combo.config(values=all_values)
            try:
                self.category_combo.current(all_values.index(cat_name))
            except ValueError:
                self.category_combo.current(0)
            
            self.btn_apply_category.config(state=tk.NORMAL)
        else:
            self.current_selected_link = None
            self.btn_apply_category.config(state=tk.DISABLED)

    def on_tree_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        parent = self.tree.parent(item_id)
        if not parent:
            return
        current_vals = list(self.tree.item(item_id, "values"))
        marked = current_vals[-1]
        new_marked = "No" if marked == "Yes" else "Yes"
        current_vals[-1] = new_marked
        self.tree.item(item_id, values=current_vals)
        self.status_label.config(text=f"Marked toggled to '{new_marked}'.")

    def _find_link_by_tree_item(self, item_id):
        for link_elem, tid in self.link_to_tree_id.items():
            if tid == item_id:
                return link_elem
        return None

    # --------------------------------------------------------------------------
    # 4. CATEGORY REASSIGNMENT (DEDUPER)
    # --------------------------------------------------------------------------
    def apply_category(self):
        if not self.current_selected_link:
            return
        
        new_cat_name = self.category_combo.get()
        cat_id = None
        for k, v in self.categories.items():
            if v == new_cat_name:
                cat_id = k
                break
        if cat_id is None:
            cat_id = self._create_new_category(new_cat_name)

        katid_elem = self.current_selected_link.find("KategorieID")
        if katid_elem is None:
            katid_elem = ET.SubElement(self.current_selected_link, "KategorieID")
        katid_elem.text = cat_id
        
        item_id = self.link_to_tree_id[self.current_selected_link]
        vals = list(self.tree.item(item_id, "values"))
        vals[1] = new_cat_name
        self.tree.item(item_id, values=vals)
        
        # Rebuild Explorer
        for child in self.explorer_tree.get_children():
            self.explorer_tree.delete(child)
        self._populate_explorer_tree()

        self.status_label.config(text=f"Category changed to '{new_cat_name}'.")

    def _create_new_category(self, cat_name):
        new_id = self._generate_new_category_id()
        cat_elem = ET.SubElement(self.xml_root, "Kategorien")
        
        cat_id_elem = ET.SubElement(cat_elem, "ID")
        cat_id_elem.text = str(new_id)
        cat_name_elem = ET.SubElement(cat_elem, "Kategorie")
        cat_name_elem.text = cat_name

        self.categories[str(new_id)] = cat_name
        return str(new_id)

    def _generate_new_category_id(self):
        existing_ids = []
        for cid in self.categories:
            try:
                existing_ids.append(int(cid))
            except ValueError:
                pass
        if not existing_ids:
            return 1
        else:
            return max(existing_ids) + 1

    # --------------------------------------------------------------------------
    # 5. MARKING, UNMARKING, REMOVING (DEDUPER)
    # --------------------------------------------------------------------------
    def mark_all_but_one(self):
        group_count = 0
        for group_item in self.tree.get_children():
            child_items = self.tree.get_children(group_item)
            if len(child_items) > 1:
                group_count += 1
                for child_item in child_items[1:]:
                    vals = list(self.tree.item(child_item, "values"))
                    vals[-1] = "Yes"
                    self.tree.item(child_item, values=vals)
        self.status_label.config(text=f"Marked duplicates in {group_count} group(s).")

    def unmark_selected(self):
        selected = self.tree.selection()
        unmarked_count = 0
        for item_id in selected:
            parent = self.tree.parent(item_id)
            if parent:
                vals = list(self.tree.item(item_id, "values"))
                if vals[-1] == "Yes":
                    vals[-1] = "No"
                    self.tree.item(item_id, values=vals)
                    unmarked_count += 1
        self.status_label.config(text=f"Unmarked {unmarked_count} selected item(s).")

    def remove_marked(self):
        if not self.xml_root:
            return
        
        removed_count = 0
        for group_item in self.tree.get_children():
            for child_item in self.tree.get_children(group_item):
                vals = self.tree.item(child_item, "values")
                if vals[-1] == "Yes":
                    link_elem = self._find_link_by_tree_item(child_item)
                    if link_elem is not None:
                        self.xml_root.remove(link_elem)
                        removed_count += 1
                    self.tree.delete(child_item)
        
        # Rebuild Explorer
        for child in self.explorer_tree.get_children():
            self.explorer_tree.delete(child)
        self._populate_explorer_tree()

        self.status_label.config(text=f"Removed {removed_count} marked item(s).")

    # --------------------------------------------------------------------------
    # 6. EXPAND/COLLAPSE, SAVE (DEDUPER)
    # --------------------------------------------------------------------------
    def expand_collapse_all(self, expand=True):
        for group_item in self.tree.get_children():
            self.tree.item(group_item, open=expand)
        if expand:
            self.status_label.config(text="All groups expanded.")
        else:
            self.status_label.config(text="All groups collapsed.")

    def save_xml(self):
        if not self.xml_tree or not self.xml_root:
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Cleaned XML",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            self.xml_tree.write(file_path, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Saved", f"Saved cleaned XML to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    # --------------------------------------------------------------------------
    # 7. EXPLORER TAB: SELECTION + CATEGORY MGMT
    # --------------------------------------------------------------------------
    def on_explorer_select(self, event):
        pass

    def add_category(self):
        new_name = self._prompt_for_text("New Category Name")
        if not new_name:
            return
        
        cat_id = self._create_new_category(new_name)
        self._populate_category_combo()
        for child in self.explorer_tree.get_children():
            self.explorer_tree.delete(child)
        self._populate_explorer_tree()

        self.status_label.config(text=f"Added new category '{new_name}' (ID={cat_id}).")

    def rename_category(self):
        sel_items = self.explorer_tree.selection()
        if not sel_items:
            return
        
        item_id = sel_items[0]
        parent = self.explorer_tree.parent(item_id)
        if parent:
            messagebox.showinfo("Info", "Please select a category to rename.")
            return

        old_name = self.explorer_tree.item(item_id, "text")
        cat_id = self._find_category_id_by_name(old_name)
        if not cat_id:
            messagebox.showwarning("Warning", "Could not determine category ID for this category.")
            return

        new_name = self._prompt_for_text("New Category Name", default_value=old_name)
        if not new_name or new_name == old_name:
            return

        self._rename_category_in_xml(cat_id, new_name)
        self.categories[cat_id] = new_name

        self._populate_category_combo()
        for child in self.explorer_tree.get_children():
            self.explorer_tree.delete(child)
        self._populate_explorer_tree()

        self.status_label.config(text=f"Renamed category '{old_name}' to '{new_name}'.")

    def remove_category(self):
        sel_items = self.explorer_tree.selection()
        if not sel_items:
            return
        
        item_id = sel_items[0]
        parent = self.explorer_tree.parent(item_id)
        if parent:
            messagebox.showinfo("Info", "Please select a category to remove.")
            return
        
        cat_name = self.explorer_tree.item(item_id, "text")
        cat_id = self._find_category_id_by_name(cat_name)
        if not cat_id:
            messagebox.showwarning("Warning", "Could not determine category ID for this category.")
            return

        confirm = messagebox.askyesno("Confirm", 
            f"Remove category '{cat_name}' (ID={cat_id}) and all associated bookmarks?")
        if not confirm:
            return
        
        cat_elem = self._find_category_elem_by_id(cat_id)
        if cat_elem is not None:
            self.xml_root.remove(cat_elem)
        
        removed_links_count = 0
        for link_elem in list(self.xml_root.findall("Links")):
            kid = self._safe_find_text(link_elem, "KategorieID")
            if kid == cat_id:
                self.xml_root.remove(link_elem)
                removed_links_count += 1

        if cat_id in self.categories:
            del self.categories[cat_id]

        self._populate_category_combo()
        for child in self.explorer_tree.get_children():
            self.explorer_tree.delete(child)
        self._populate_explorer_tree()

        # Rebuild deduper
        for child in self.tree.get_children():
            self.tree.delete(child)
        self.links_by_group.clear()
        self.group_ids.clear()
        self.link_to_tree_id.clear()
        self._group_links()
        self._populate_deduper_tree()

        self.status_label.config(
            text=f"Removed category '{cat_name}' and {removed_links_count} associated bookmark(s)."
        )

    # --------------------------------------------------------------------------
    # 8. EXPLORER TAB: ADDING BOOKMARKS (with Enhanced Title Extraction)
    # --------------------------------------------------------------------------
    def add_bookmark(self):
        url = self.new_url_entry.get().strip()
        if not url:
            messagebox.showinfo("Info", "Please enter a valid URL.")
            return
        
        cat_name = self.new_bmk_cat_combo.get()
        cat_id = None
        for k, v in self.categories.items():
            if v == cat_name:
                cat_id = k
                break
        if cat_id is None:
            cat_id = self._create_new_category(cat_name)

        title_text = self._extract_title_from_url(url)
        if not title_text:
            title_text = url

        link_elem = ET.SubElement(self.xml_root, "Links")
        
        new_link_id = self._generate_new_link_id()
        id_elem = ET.SubElement(link_elem, "ID")
        id_elem.text = str(new_link_id)
        
        url_elem = ET.SubElement(link_elem, "URL")
        url_elem.text = url
        
        katid_elem = ET.SubElement(link_elem, "KategorieID")
        katid_elem.text = str(cat_id)

        title_elem = ET.SubElement(link_elem, "Title")
        title_elem.text = title_text

        # Also create <Tags> sub-element
        tags_elem = ET.SubElement(link_elem, "Tags")
        tags_elem.text = ""

        self.last_added_category_name = cat_name
        for child in self.explorer_tree.get_children():
            self.explorer_tree.delete(child)
        self._populate_explorer_tree()

        # Rebuild deduper
        for child in self.tree.get_children():
            self.tree.delete(child)
        self.links_by_group.clear()
        self.group_ids.clear()
        self.link_to_tree_id.clear()
        self._group_links()
        self._populate_deduper_tree()

        self.status_label.config(text=f"Added new bookmark (URL='{url}', Category='{cat_name}').")
        self.new_url_entry.delete(0, tk.END)

    def _generate_new_link_id(self):
        existing_ids = []
        for link_elem in self.xml_root.findall("Links"):
            link_id_text = self._safe_find_text(link_elem, "ID")
            if link_id_text.isdigit():
                existing_ids.append(int(link_id_text))
        if not existing_ids:
            return 1
        return max(existing_ids) + 1

    def _extract_title_from_url(self, url):
        try:
            if not url.startswith(("http://", "https://")):
                url = "http://" + url

            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                match = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
                if match:
                    raw_title = match.group(1).strip()
                    decoded_title = html.unescape(raw_title)
                    final_title = urllib.parse.unquote(decoded_title)
                    return final_title
        except Exception:
            pass
        return ""

    # --------------------------------------------------------------------------
    # 9. EXPLORER TAB: SORTING CATEGORIES/BOOKMARKS
    # --------------------------------------------------------------------------
    def sort_categories(self):
        top_items = self.explorer_tree.get_children("")
        cat_list = []
        for itm in top_items:
            cat_name = self.explorer_tree.item(itm, "text")
            cat_list.append((cat_name, itm))
        cat_list.sort(key=lambda x: x[0].lower())

        for idx, (cat_name, itm) in enumerate(cat_list):
            self.explorer_tree.move(itm, "", idx)

        self.status_label.config(text="Sorted categories by title.")

    def sort_bookmarks(self):
        top_items = self.explorer_tree.get_children("")
        for cat_item in top_items:
            children = self.explorer_tree.get_children(cat_item)
            bookmark_list = []
            for child_id in children:
                # URL is index=0 in .item(...,"values")
                url_val = self.explorer_tree.item(child_id, "values")[0]
                bookmark_list.append((url_val, child_id))
            bookmark_list.sort(key=lambda x: x[0].lower())

            for idx, (url_val, c_id) in enumerate(bookmark_list):
                self.explorer_tree.move(c_id, cat_item, idx)

        self.status_label.config(text="Sorted bookmarks by URL.")

    # --------------------------------------------------------------------------
    #  DRAG & DROP (EXPLORER)
    # --------------------------------------------------------------------------
    def toggle_drag_drop(self):
        self.drag_mode = not self.drag_mode
        if self.drag_mode:
            self.drag_drop_btn.configure(text="Disable Drag & Drop")
            self.status_label.config(text="Drag & Drop mode enabled. Select bookmarks and drag them to another category.")
        else:
            self.drag_drop_btn.configure(text="Enable Drag & Drop")
            self.status_label.config(text="Drag & Drop mode disabled.")

    def on_tree_button_press(self, event):
        if not self.drag_mode:
            return
        item_id = self.explorer_tree.identify_row(event.y)
        if not item_id:
            return
        sel = self.explorer_tree.selection()
        self.dragging_items = []
        for s in sel:
            parent = self.explorer_tree.parent(s)
            if parent:
                self.dragging_items.append(s)
        if self.dragging_items:
            self._show_drag_tooltip(len(self.dragging_items), event.x_root, event.y_root)

    def on_tree_motion(self, event):
        if not self.drag_mode or not self.dragging_items:
            return
        self._move_drag_tooltip(event.x_root, event.y_root)

    def on_tree_button_release(self, event):
        if not self.drag_mode or not self.dragging_items:
            self._hide_drag_tooltip()
            return

        drop_item_id = self.explorer_tree.identify_row(event.y)
        if not drop_item_id:
            self._hide_drag_tooltip()
            self.dragging_items = None
            return

        parent = self.explorer_tree.parent(drop_item_id)
        if parent:
            new_category_item = parent
        else:
            new_category_item = drop_item_id

        cat_name = self.explorer_tree.item(new_category_item, "text")
        cat_id = self._find_category_id_by_name(cat_name)

        for bm_item in self.dragging_items:
            old_parent = self.explorer_tree.parent(bm_item)
            if old_parent != new_category_item:
                self.explorer_tree.move(bm_item, new_category_item, 'end')

                url_val = self.explorer_tree.item(bm_item, "values")[0]
                bookmark_title = self.explorer_tree.item(bm_item, "text")
                link_elem = self._find_link_elem_by_url_and_title(url_val, bookmark_title, old_parent)
                if link_elem is not None:
                    if cat_id is None:
                        cat_id = self._create_new_category(cat_name)
                    katid_elem = link_elem.find("KategorieID")
                    if katid_elem is None:
                        katid_elem = ET.SubElement(link_elem, "KategorieID")
                    katid_elem.text = str(cat_id)

        self._hide_drag_tooltip()
        self.dragging_items = None
        self.status_label.config(text=f"Moved bookmark(s) to '{cat_name}' category.")

    def _find_link_elem_by_url_and_title(self, url, title, old_parent_item):
        old_parent_cat_name = self.explorer_tree.item(old_parent_item, "text")
        old_cat_id = self._find_category_id_by_name(old_parent_cat_name)

        for link_elem in self.xml_root.findall("Links"):
            kid = self._safe_find_text(link_elem, "KategorieID")
            if kid == old_cat_id:
                link_url = self._safe_find_text(link_elem, "URL")
                link_title = self._safe_find_text(link_elem, "Title")
                if not link_title:
                    link_title = link_url

                if link_url == url and link_title == title:
                    return link_elem
        return None

    def _show_drag_tooltip(self, count, x, y):
        if not self.drag_tooltip:
            self.drag_tooltip = tk.Toplevel(self.master)
            self.drag_tooltip.overrideredirect(True)
            self.drag_tooltip_label = tk.Label(self.drag_tooltip, bg="lightyellow", bd=1, relief="solid")
            self.drag_tooltip_label.pack()
        text = f"{count} item(s) selected"
        self.drag_tooltip_label.config(text=text)
        self._move_drag_tooltip(x, y)
        self.drag_tooltip.deiconify()

    def _move_drag_tooltip(self, x, y):
        if self.drag_tooltip:
            self.drag_tooltip.geometry(f"+{x+12}+{y+12}")

    def _hide_drag_tooltip(self):
        if self.drag_tooltip:
            self.drag_tooltip.withdraw()

    # --------------------------------------------------------------------------
    #  HELPER METHODS - CATEGORY UTILS
    # --------------------------------------------------------------------------
    def _find_category_id_by_name(self, cat_name):
        for cid, cname in self.categories.items():
            if cname == cat_name:
                return cid
        return None

    def _find_category_elem_by_id(self, cat_id):
        for cat_elem in self.xml_root.findall("Kategorien"):
            cid = self._safe_find_text(cat_elem, "ID")
            if cid == cat_id:
                return cat_elem
        return None

    def _rename_category_in_xml(self, cat_id, new_name):
        cat_elem = self._find_category_elem_by_id(cat_id)
        if cat_elem is None:
            return
        cat_name_elem = cat_elem.find("Kategorie")
        if cat_name_elem is not None:
            cat_name_elem.text = new_name

    # --------------------------------------------------------------------------
    #  SMALL UTILITY FOR TEXT PROMPT
    # --------------------------------------------------------------------------
    def _prompt_for_text(self, title, default_value=""):
        dialog = tk.Toplevel(self.master)
        dialog.title(title)
        dialog.transient(self.master)
        dialog.grab_set()

        tk.Label(dialog, text=title).pack(padx=10, pady=(10,0))

        entry_var = tk.StringVar(value=default_value)
        entry = tk.Entry(dialog, textvariable=entry_var, width=40)
        entry.pack(padx=10, pady=(0,10))
        entry.focus()

        result = [None]
        
        def on_ok():
            result[0] = entry_var.get().strip()
            dialog.destroy()
        def on_cancel():
            result[0] = None
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=(0,10))
        
        ok_btn = tk.Button(btn_frame, text="OK", command=on_ok)
        ok_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=on_cancel)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        dialog.wait_window()
        return result[0]

    # --------------------------------------------------------------------------
    #  COPY & DELETE SELECTED BOOKMARKS
    # --------------------------------------------------------------------------
    def copy_selected_bookmark_url(self):
        sel = self.explorer_tree.selection()
        if not sel:
            return
        
        urls_to_copy = []
        for item_id in sel:
            parent = self.explorer_tree.parent(item_id)
            if parent:
                url_val = self.explorer_tree.item(item_id, "values")[0]
                urls_to_copy.append(url_val)
        if not urls_to_copy:
            self.status_label.config(text="No bookmarks selected to copy.")
            return

        clip_text = "\n".join(urls_to_copy)
        self.master.clipboard_clear()
        self.master.clipboard_append(clip_text)
        self.status_label.config(text=f"Copied {len(urls_to_copy)} URL(s) to clipboard.")

    def delete_selected_bookmarks(self):
        sel = self.explorer_tree.selection()
        if not sel:
            return

        delete_count = 0
        for item_id in sel:
            parent = self.explorer_tree.parent(item_id)
            if parent:
                url_val = self.explorer_tree.item(item_id, "values")[0]
                bookmark_title = self.explorer_tree.item(item_id, "text")

                link_elem = self._find_link_elem_by_url_and_title(url_val, bookmark_title, parent)
                if link_elem is not None:
                    self.xml_root.remove(link_elem)
                    delete_count += 1

                self.explorer_tree.delete(item_id)

        if delete_count > 0:
            for child in self.tree.get_children():
                self.tree.delete(child)
            self.links_by_group.clear()
            self.group_ids.clear()
            self.link_to_tree_id.clear()
            self._group_links()
            self._populate_deduper_tree()

        self.status_label.config(text=f"Deleted {delete_count} bookmark(s).")

    # --------------------------------------------------------------------------
    #  CREATE AN EMPTY XML
    # --------------------------------------------------------------------------
    def create_empty_xml(self):
        file_path = filedialog.asksaveasfilename(
            title="Create Empty XML",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        
        new_root = ET.Element("SafavorRoot")
        new_tree = ET.ElementTree(new_root)

        try:
            new_tree.write(file_path, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Success", f"Empty XML created at: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create file:\n{e}")

    # --------------------------------------------------------------------------
    #  REFRESH DEDUPER
    # --------------------------------------------------------------------------
    def refresh_deduper(self):
        for child in self.tree.get_children():
            self.tree.delete(child)
        self.links_by_group.clear()
        self.group_ids.clear()
        self.link_to_tree_id.clear()
        self.current_selected_link = None

        self._group_links()
        self._populate_deduper_tree()

        self.status_label.config(text="Deduper tab refreshed with latest changes from Explorer.")

    # --------------------------------------------------------------------------
    #  TAGGING HELPER METHODS
    # --------------------------------------------------------------------------
    def _get_tags_for_link_elem(self, link_elem):
        tags_elem = link_elem.find("Tags")
        if tags_elem is None or not tags_elem.text:
            return set()
        raw = tags_elem.text.strip()
        return set(t.strip() for t in raw.split(",") if t.strip())

    def _set_tags_for_link_elem(self, link_elem, tags_set):
        tags_elem = link_elem.find("Tags")
        if tags_elem is None:
            tags_elem = ET.SubElement(link_elem, "Tags")
        tags_elem.text = ",".join(sorted(tags_set))

    # --------------------------------------------------------------------------
    #  ADD / REMOVE TAGS
    # --------------------------------------------------------------------------
    def add_tags_to_selected(self):
        sel = self.explorer_tree.selection()
        if not sel:
            return

        tags_input = self._prompt_for_text("Enter one or more tags (comma-separated)")
        if not tags_input:
            return

        new_tags = set(t.strip() for t in tags_input.split(",") if t.strip())

        updated_count = 0
        for item_id in sel:
            parent = self.explorer_tree.parent(item_id)
            if parent:  # It's a bookmark
                url_val = self.explorer_tree.item(item_id, "values")[0]
                bookmark_title = self.explorer_tree.item(item_id, "text")
                link_elem = self._find_link_elem_by_url_and_title(url_val, bookmark_title, parent)
                if link_elem is not None:
                    # 1. Update the XML <Tags> element
                    current_tags = self._get_tags_for_link_elem(link_elem)
                    updated_tags = current_tags.union(new_tags)
                    self._set_tags_for_link_elem(link_elem, updated_tags)
                    
                    # 2. Update the Explorer Tree “Tags” column in-place
                    tags_str = ", ".join(sorted(updated_tags))
                    # The Explorer’s columns are (URL, Tags), so index 1 is the Tags column
                    old_vals = list(self.explorer_tree.item(item_id, "values"))
                    old_vals[1] = tags_str
                    self.explorer_tree.item(item_id, values=old_vals)

                    # 3. If the filter is on, check if we need to detach/reinsert
                    if self.filter_mode:
                        if self._bookmark_matches_filter(updated_tags):
                            # If it was hidden but now qualifies, re-show it
                            if item_id in [h[0] for h in self.hidden_items]:
                                self._reinsert_item(item_id)
                        else:
                            # If it doesn't match, hide it
                            if item_id not in [h[0] for h in self.hidden_items]:
                                self._detach_item(item_id)

                    updated_count += 1

        self.status_label.config(text=f"Added tags to {updated_count} bookmark(s).")


    def remove_tags_from_selected(self):
        sel = self.explorer_tree.selection()
        if not sel:
            return

        tags_input = self._prompt_for_text("Enter one or more tags to remove (comma-separated)")
        if not tags_input:
            return

        remove_tags = set(t.strip() for t in tags_input.split(",") if t.strip())

        updated_count = 0
        for item_id in sel:
            parent = self.explorer_tree.parent(item_id)
            if parent:  # It's a bookmark
                url_val = self.explorer_tree.item(item_id, "values")[0]
                bookmark_title = self.explorer_tree.item(item_id, "text")
                link_elem = self._find_link_elem_by_url_and_title(url_val, bookmark_title, parent)
                if link_elem is not None:
                    # 1. Update the XML <Tags> element
                    current_tags = self._get_tags_for_link_elem(link_elem)
                    updated_tags = current_tags - remove_tags
                    self._set_tags_for_link_elem(link_elem, updated_tags)

                    # 2. Update the Explorer Tree “Tags” column in-place
                    tags_str = ", ".join(sorted(updated_tags))
                    old_vals = list(self.explorer_tree.item(item_id, "values"))
                    old_vals[1] = tags_str  # tags are in second column
                    self.explorer_tree.item(item_id, values=old_vals)

                    # 3. If filter is on, check if we need to detach/reinsert
                    if self.filter_mode:
                        if self._bookmark_matches_filter(updated_tags):
                            if item_id in [h[0] for h in self.hidden_items]:
                                self._reinsert_item(item_id)
                        else:
                            if item_id not in [h[0] for h in self.hidden_items]:
                                self._detach_item(item_id)

                    updated_count += 1

        self.status_label.config(text=f"Removed tags from {updated_count} bookmark(s).")


    # --------------------------------------------------------------------------
    #  TOGGLE FILTER BY TAG
    # --------------------------------------------------------------------------
    def toggle_filter_by_tag(self):
        if not self.filter_mode:
            tags_input = self._prompt_for_text("Enter tag(s) to filter by (comma-separated)")
            if not tags_input:
                return
            self.filter_tags = set(t.strip() for t in tags_input.split(",") if t.strip())
            self.filter_mode = True
            self.btn_filter_by_tag.config(text="Disable Filter by Tag")
            self._apply_filter()
            self.status_label.config(text=f"Filter ON. Showing only bookmarks that have all tags: {', '.join(self.filter_tags)}")
        else:
            self.filter_mode = False
            self.filter_tags.clear()
            self.btn_filter_by_tag.config(text="Enable Filter by Tag")
            self._restore_hidden_items()
            self.hidden_items.clear()
            self.status_label.config(text="Filter OFF. Restored all bookmarks.")

    def _apply_filter(self):
        self.hidden_items.clear()
        top_items = self.explorer_tree.get_children("")
        for cat_item in top_items:
            bookmark_children = self.explorer_tree.get_children(cat_item)
            match_count = 0
            for bm_item in bookmark_children:
                url_val = self.explorer_tree.item(bm_item, "values")[0]
                bookmark_title = self.explorer_tree.item(bm_item, "text")
                link_elem = self._find_link_elem_by_url_and_title(url_val, bookmark_title, cat_item)
                if link_elem is not None:
                    tags_set = self._get_tags_for_link_elem(link_elem)
                    if self._bookmark_matches_filter(tags_set):
                        match_count += 1
                    else:
                        self._detach_item(bm_item)
                else:
                    self._detach_item(bm_item)

            if match_count == 0:
                self._detach_item(cat_item)

    def _bookmark_matches_filter(self, bookmark_tags):
        return self.filter_tags.issubset(bookmark_tags)

    def _detach_item(self, item_id):
        parent_id = self.explorer_tree.parent(item_id)
        index_in_parent = self.explorer_tree.index(item_id)
        self.hidden_items.append((item_id, parent_id, index_in_parent))
        self.explorer_tree.detach(item_id)

    def _reinsert_item(self, item_id):
        record = None
        for h in self.hidden_items:
            if h[0] == item_id:
                record = h
                break
        if not record:
            return
        (itm, parent_id, index_in_parent) = record
        self.explorer_tree.move(itm, parent_id, index_in_parent)
        self.hidden_items.remove(record)

    def _restore_hidden_items(self):
        self.hidden_items.sort(key=lambda x: (x[1], x[2]))
        for (itm, parent_id, index_in_parent) in self.hidden_items:
            self.explorer_tree.move(itm, parent_id, index_in_parent)

# --------------------------------------------------------------------------
#  MAIN
# --------------------------------------------------------------------------
def main():
    root = tk.Tk()
    root.geometry("1200x700")
    app = SafavorCleanerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
