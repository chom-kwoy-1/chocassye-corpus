import os
import unicodedata
import argparse

def normalize_filenames_in_dir(root_dir: str) -> None:
    """
    Recursively normalizes all filenames in the given directory to Unicode
    Normalisation Form C (NFC) and renames the files in place.

    Args:
        root_dir: The path to the starting directory.
    """

    # Check if the path exists and is a directory
    if not os.path.isdir(root_dir):
        print(f"Error: Directory not found or is not a directory: '{root_dir}'")
        return

    print(f"Starting NFC normalization in: '{root_dir}'")

    # Counter for successful renames
    renamed_count = 0

    # os.walk yields a 3-tuple: (current_dir_path, dir_names, file_names)
    for current_dir, _, filenames in os.walk(root_dir, topdown=False):
        # We process files first, then directories (bottom-up traversal)
        # to ensure directory names are normalized before we process their contents.

        # 1. Normalize File Names
        for filename in filenames:
            normalized_filename = unicodedata.normalize('NFC', filename)

            # Skip if no change is needed
            if normalized_filename == filename:
                continue

            old_path = os.path.join(current_dir, filename)
            new_path = os.path.join(current_dir, normalized_filename)

            try:
                # Renaming automatically removes the original path/name
                os.rename(old_path, new_path)
                print(f"Renamed: '{filename}' -> '{normalized_filename}'")
                renamed_count += 1
            except FileNotFoundError:
                # Should not happen often, but handles race conditions
                print(f"Warning: File not found during rename (race condition?): '{old_path}'")
            except PermissionError:
                print(f"Error: Permission denied for renaming: '{old_path}'")
            except Exception as e:
                print(f"An unexpected error occurred while renaming '{old_path}': {e}")

        # 2. Normalize Directory Names
        # Note: Directory names must be normalized carefully. We need to rename
        # the directory itself and then ensure os.walk doesn't continue down
        # the old, non-existent path. os.walk handles this by processing `dirnames`
        # in place if `topdown=True`, but since we use `topdown=False` (bottom-up),
        # we handle the renaming after processing the files, and it's less complex.
        # For `topdown=False`, we iterate through the list of directory names
        # (which are the child directories of `current_dir`)

        # Make a copy of the list of directory names for safe iteration and modification
        for dirname in list(os.listdir(current_dir)):
            # Ensure we are only normalizing directories that haven't been renamed yet
            dir_path = os.path.join(current_dir, dirname)
            if not os.path.isdir(dir_path):
                continue

            normalized_dirname = unicodedata.normalize('NFC', dirname)

            if normalized_dirname == dirname:
                continue

            old_path = os.path.join(current_dir, dirname)
            new_path = os.path.join(current_dir, normalized_dirname)

            try:
                os.rename(old_path, new_path)
                print(f"Renamed Directory: '{dirname}' -> '{normalized_dirname}'")
                renamed_count += 1
            except FileNotFoundError:
                print(f"Warning: Directory not found during rename: '{old_path}'")
            except PermissionError:
                print(f"Error: Permission denied for renaming directory: '{old_path}'")
            except Exception as e:
                print(f"An unexpected error occurred while renaming directory '{old_path}': {e}")


    print("-" * 30)
    print(f"Normalization complete. Total files/directories renamed: {renamed_count}")
    print(f"Finished NFC normalization in: '{root_dir}'")


if __name__ == "__main__":
    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Recursively NFC-normalizes all filenames and directory names in a given path."
    )
    parser.add_argument(
        "directory",
        type=str,
        help="The starting directory path to process."
    )

    args = parser.parse_args()

    # Run the normalization function
    normalize_filenames_in_dir(args.directory)
