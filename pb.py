import yaml
import os
import sys
import re

ITEMS_FILE = "pb.yaml"

# --- Color support (TTY-only; honors NO_COLOR and PB_COLOR=0) ---


def _supports_color():
    if os.environ.get("PB_COLOR", "1") == "0":
        return False
    if os.environ.get("NO_COLOR"):
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


_COLOR_ON = _supports_color()

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"


def fmt(text: str, *styles: str) -> str:
    if not _COLOR_ON or not styles:
        return text
    return "".join(styles) + text + RESET


def clear_screen():
    """Clear terminal screen on macOS/Linux/Windows."""
    try:
        if os.name == "nt":
            os.system("cls")
        else:
            # ANSI clear screen and move cursor to home
            print("\033[2J\033[H", end="")
    except Exception:
        # Fallback: some newlines
        print("\n" * 5)


def wait_for_enter():
    """Pause to let user read output before returning to menu."""
    try:
        input(fmt("\nPress Enter to return to menu...", YELLOW))
    except EOFError:
        # In non-interactive cases, just continue
        pass


def colorize_yaml(yaml_text: str) -> str:
    """Minimal YAML colorization for terminal (common YAML conventions).
    - Top-level keys: bold magenta (main elements)
    - Keys (nested): bold (no color)
    - Strings: green
    - Numbers: yellow
    - Booleans/Null: magenta
    - Punctuation [] and {}: magenta
    - List marker '- ': cyan
    - Comments: blue
    """
    if not _COLOR_ON:
        return yaml_text

    comment_re = re.compile(r"^(\s*#.*)$")
    kv_re = re.compile(r"^(\s*)([^:\n]+?)(:)(\s*)(.*)$")
    dash_re = re.compile(r"^(\s*)-\s+(.*)$")

    def color_value(v: str) -> str:
        sv = v.strip()
        # punctuation and nulls
        if sv in ("[]", "{}"):
            return fmt(v, MAGENTA)
        if sv.lower() in ("~", "null", "nil", "none"):
            return fmt(v, MAGENTA)
        # booleans
        if sv.lower() in ("true", "false", "yes", "no", "on", "off"):
            return fmt(v, MAGENTA)
        # numbers (int/float/scientific)
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", sv):
            return fmt(v, YELLOW)
        # quoted strings
        if (sv.startswith("'") and sv.endswith("'")) or (sv.startswith('"') and sv.endswith('"')):
            return fmt(v, GREEN)
        # unquoted scalars as strings
        return fmt(v, GREEN)

    out_lines = []
    for line in yaml_text.splitlines():
        m = comment_re.match(line)
        if m:
            out_lines.append(fmt(m.group(1), BLUE))
            continue

        m = dash_re.match(line)
        if m:
            indent, val = m.groups()
            out_lines.append(indent + fmt("- ", CYAN) + color_value(val))
            continue

        m = kv_re.match(line)
        if m:
            indent, key, colon, space, val = m.groups()
            # Top-level keys have no indentation
            if len(indent) == 0:
                key_part = fmt(key, BOLD, MAGENTA)
            else:
                key_part = fmt(key, BOLD)
            out_lines.append(
                indent + key_part + colon + space +
                (color_value(val) if val else "")
            )
            continue

        out_lines.append(line)

    return "\n".join(out_lines)


def load_items():
    if not os.path.exists(ITEMS_FILE):
        return {"categories": {}}
    with open(ITEMS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_items(data):
    with open(ITEMS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def choose_category(data):
    print(fmt("\nAvailable categories:", BOLD, CYAN))
    for key, name in data["categories"].items():
        print(f"  {fmt(key, BOLD, MAGENTA)} → {fmt(name, CYAN)}")
    cat = input(
        "Choose category (key, or press Enter to cancel): ").strip().lower()
    return cat if cat in data["categories"] else None


def add_item(data):
    cat = choose_category(data)
    if not cat:
        print(fmt("No category chosen.", YELLOW))
        return

    item_name = input("Item name (e.g. laptop, toothbrush): ").strip().lower()
    if not item_name:
        print(fmt("Item name required.", RED))
        return

    details = input("Details (e.g. mb, ios) [Enter = none]: ").strip().lower()
    season = input(
        "Season (s=summer, w=winter, n=neutral) [default=n]: ").strip().lower() or "n"
    index = input("Index (a, b, c...) [Enter = none]: ").strip().lower()

    parts = [f"{cat}-{item_name}"]
    if details:
        parts.append(details)
    parts.append(season)
    if index:
        parts.append(index)

    code = "-".join(parts)

    category_name = data["categories"][cat]
    if category_name not in data:
        data[category_name] = []
    data[category_name].append(code)

    print(fmt(f"Added: {code}", GREEN))


def manage_categories(data):
    # Backward-compat wrapper; use the unified categories menu
    categories_menu(data)


def categories_menu(data):
    print(fmt("\nCategories:", BOLD, CYAN))
    print("1. Add category")
    print("2. Delete category")
    print("3. Modify category")
    choice = input("Choose option (Enter to cancel): ").strip()

    if choice == "":
        return
    if choice == "1":
        key = input("Category key (one letter): ").strip().lower()
        name = input("Category name: ").strip()
        if key and name:
            data["categories"][key] = name
            if name not in data:
                data[name] = []
            print(fmt(f"Category added: {key} → {name}", GREEN))
        else:
            print(fmt("Key and name are required.", YELLOW))
    elif choice == "2":
        key = choose_category(data)
        if key:
            name = data["categories"].pop(key)
            data.pop(name, None)
            print(fmt(f"Category {key} → {name} deleted.", GREEN))
        else:
            print(fmt("No category chosen.", YELLOW))
    elif choice == "3":
        old_key = choose_category(data)
        if not old_key:
            print(fmt("No category chosen.", YELLOW))
            return
        old_name = data["categories"][old_key]
        print(fmt(f"\nModify category {old_key} → {old_name}", BOLD, CYAN))
        new_key = input(f"New key (Enter to keep '{old_key}'): ").strip().lower() or old_key
        new_name = input(f"New name (Enter to keep '{old_name}'): ").strip() or old_name

        # Validate collisions
        if new_key != old_key and new_key in data["categories"]:
            print(fmt("A category with this key already exists.", RED))
            return
        if new_name != old_name and new_name in data and new_name not in (old_name,):
            print(fmt("A category with this name already exists.", RED))
            return

        # Update name (list key) if changed
        if new_name != old_name:
            data.setdefault(new_name, data.get(old_name, []))
            if old_name in data and new_name != old_name:
                # Move items to new list key
                items_list = data.pop(old_name)
                data[new_name] = items_list

        # Update key mapping
        if new_key != old_key or new_name != old_name:
            # Replace mapping
            data["categories"].pop(old_key)
            data["categories"][new_key] = new_name

        # If key changed, update all item codes under this category
        if new_key != old_key:
            items = data.get(new_name, [])
            updated = []
            for code in items:
                parts = code.split("-", 1)
                if parts:
                    if len(parts) == 1:
                        updated.append(new_key)
                    else:
                        updated.append(new_key + "-" + parts[1])
                else:
                    updated.append(code)
            data[new_name] = updated
        print(fmt("Category modified.", GREEN))
    else:
        print(fmt("Invalid choice.", YELLOW))


def manage_items(data):
    """Edit, move, or delete existing items."""
    # Pick a category first
    cat_key = choose_category(data)
    if not cat_key:
        print(fmt("No category chosen.", YELLOW))
        return

    cat_name = data["categories"][cat_key]
    items = data.get(cat_name, [])

    if not items:
        print(fmt(f"No items in '{cat_name}'.", YELLOW))
        return

    print(fmt(f"\nItems in {cat_name}:", BOLD, CYAN))
    for i, code in enumerate(items, 1):
        print(f"  {i}. {fmt(code, GREEN)}")

    sel = input("Choose item number to modify (Enter to cancel): ").strip()
    if not sel:
        return
    if not sel.isdigit() or not (1 <= int(sel) <= len(items)):
        print(fmt("Invalid selection.", YELLOW))
        return

    idx = int(sel) - 1
    code = items[idx]

    print(fmt(f"\nModify item: {code}", BOLD, CYAN))
    print("1. Edit code")
    print("2. Move to another category")
    print("3. Delete item")
    action = input("Choose action: ").strip()

    if action == "1":
        new_code = input("New code (Enter to keep current): ").strip()
        if new_code:
            items[idx] = new_code
            print(fmt("Item updated.", GREEN))
        else:
            print(fmt("No changes made.", YELLOW))
    elif action == "2":
        new_cat_key = choose_category(data)
        if not new_cat_key:
            print(fmt("No category chosen.", YELLOW))
            return
        new_cat_name = data["categories"][new_cat_key]
        if new_cat_name == cat_name:
            print(fmt("Item already in this category.", YELLOW))
            return
        # Move item list-wise and update code prefix to new category key
        parts = code.split("-")
        if parts:
            parts[0] = new_cat_key
        new_code = "-".join(parts)
        # Remove from old list
        items.pop(idx)
        # Add to new list
        data.setdefault(new_cat_name, []).append(new_code)
        print(fmt(f"Moved to {new_cat_name} as {new_code}.", GREEN))
    elif action == "3":
        items.pop(idx)
        print(fmt("Item deleted.", GREEN))
    else:
        print(fmt("Unknown action.", YELLOW))


def items_menu(data):
    """Unified items entry: add new items or manage existing ones."""
    print(fmt("\nItems:", BOLD, CYAN))
    print("1. Add item")
    print("2. Manage existing items")
    choice = input("Choose option (Enter to cancel): ").strip()
    if choice == "":
        return
    if choice == "1":
        add_item(data)
    elif choice == "2":
        manage_items(data)
    else:
        print(fmt("Invalid choice.", YELLOW))


def main():
    data = load_items()
    if "categories" not in data:
        data["categories"] = {}

    while True:
        print(fmt("=== personal-belongings manager ===", BOLD, CYAN))
        print("1. Items")
        print("2. Categories")
        print("3. Show items")
        print("4. Exit")
        choice = input("Choose option: ").strip()

        # Enter in main menu => exit
        if choice == "":
            break

        if choice == "1":
            items_menu(data)
            save_items(data)
        elif choice == "2":
            categories_menu(data)
            save_items(data)
        elif choice == "3":
            clear_screen()
            print(fmt("=== items (yaml) ===", BOLD, CYAN))
            text = yaml.dump(data, allow_unicode=True, sort_keys=False)
            print(colorize_yaml(text))
            wait_for_enter()
        elif choice == "4":
            break
        else:
            print(fmt("Invalid choice.", YELLOW))


if __name__ == "__main__":
    main()
