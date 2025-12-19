import pathlib
import shutil
import psycopg2
import argparse
import re
import subprocess
import rich
from natsort import natsorted


def confirm_page(conn, book_name, image_file, page_name):
    if '+' in page_name:
        section = page_name.split('+')[0]
        page_name = page_name.split('+')[1]
    else:
        section = None

    cur = conn.cursor()
    if section is None:
        cur.execute("""
                    SELECT section, page, html
                    FROM sentences
                    WHERE filename = %s
                      AND section IS NULL
                      AND page LIKE %s
                    ORDER BY number_in_book
                    """, (book_name, f"%{page_name}%"))
    else:
        cur.execute("""
                    SELECT section, page, html
                    FROM sentences
                    WHERE filename = %s
                      AND section = %s
                      AND page LIKE %s
                    ORDER BY number_in_book
                    """, (book_name, section, f"%{page_name}%"))

    texts = cur.fetchall()
    cur.close()

    print(f"Contents of page {page_name} of book {book_name}:")
    for section, page, text in texts[:5]:
        print(f"Sec {section} page {page}: {text}")


    proc = subprocess.Popen(["gwenview", image_file],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)

    while True:
        if proc.poll() is not None:
            proc = subprocess.Popen(["gwenview", image_file],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)

        response = input(f'Is {image_file} -> {page_name} correct? (y/n) ')
        if response.lower() not in ['y', 'n']:
            print(f"Unrecognized response: {response}")
            continue
        break

    proc.kill()

    return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image_dir", type=str)
    parser.add_argument("--db", type=str, default="chocassye")
    parser.add_argument('--ignore-pages', '-i', type=str, nargs='*', default=[])
    args = parser.parse_args()

    print(args)

    image_dir = pathlib.Path(args.image_dir).resolve()
    book_name = image_dir.parent.name
    print(f"Book name: {book_name}")

    new_dir_name = image_dir / "renamed"

    conn = psycopg2.connect(
        host="localhost",
        database=args.db,
        user="postgres",
        password="password",
    )
    print("Connected to PostgreSQL successfully!")

    cur = conn.cursor()
    cur.execute("""
        SELECT section, page FROM sentences 
            WHERE filename = %s
            ORDER BY number_in_book
    """, (book_name,))

    page_names = []
    for section, page_name in cur:
        if page_name is None:
            continue
        page_name = page_name.strip()
        if page_name == "":
            continue
        cur_pages = page_name.split("-")
        splits = re.split(r"(\d+)", cur_pages[0])
        prefix = splits[0]
        cur_pages[0] = "".join(splits[1:])
        if section is not None:
            prefix = f"{section}+{prefix}"
        for page in cur_pages:
            if page in args.ignore_pages:
                continue
            page = re.sub(r"^0+", "", page)  # remove leading zeros
            page = prefix + page
            if len(page_names) > 0 and page in page_names:
                continue
            page_names.append(page)

    cur.close()

    if len(page_names) == 0:
        print("No pages found!")
        exit(1)

    print(f"Page names = {page_names}")

    # List all .jpg files in the directory in sorted order
    image_files = natsorted([
        *image_dir.glob('*.jpg'),
        *image_dir.glob('*.png'),
    ])

    # compare the number of page names and images
    if len(page_names) != len(image_files):
        print(f'The number of page names and images do not match: '
              f'{len(page_names)} page names and {len(image_files)} images.')

        for i, image_path in enumerate(image_files):
            if i >= len(page_names):
                print(f'{image_path} -> No page name')
            else:
                print(f'{image_path} -> {page_names[i]}')

        # Bisect to find the first mismatch, through user feedback
        print('Bisecting to find the first mismatch')
        left = 0
        right = len(page_names)
        i = len(page_names) // 2
        while left < right:
            response = confirm_page(conn, book_name, image_files[i], page_names[i])

            if response == 'y':
                left = i + 1
            elif response == 'n':
                right = i
            else:
                print('Invalid response')
                continue
            i = (left + right) // 2

        print(f'First mismatch at {i}: {image_files[i]} -> {page_names[i]}')
        print("Please fix the mismatch and run the command again.")
        return

    else:
        rich.print("[bold green]Number of pages match.[/bold green]")
        # Check first and last pages
        confirm_page(conn, book_name, image_files[0], page_names[0])
        confirm_page(conn, book_name, image_files[-1], page_names[-1])

    conn.close()

    for i, image_path in enumerate(image_files):
        if i >= len(page_names):
            print(f'{image_path} -> No page name')
        else:
            print(f'{image_path} -> {page_names[i]}')

    pathlib.Path(new_dir_name).mkdir(exist_ok=True, parents=True)

    for i, image_path in enumerate(image_files):
        # Copy the image to the new directory with the new name
        new_image_path = pathlib.Path(new_dir_name) / f'{i+1}+{page_names[i]}.jpg'
        shutil.copy(image_path, new_image_path)

    print("Renaming complete.")
    response = input("Is everything OK? (y/n) ")
    if response.lower() == 'y':
        backup_dir = image_dir / ".backup"
        backup_dir.mkdir(exist_ok=True, parents=True)
        for i, image_path in enumerate(image_files):
            shutil.move(image_path, backup_dir / image_path.name)
        for i, image_path in enumerate(image_files):
            name = f'{i+1}+{page_names[i]}.jpg'
            new_image_path = pathlib.Path(new_dir_name) / name
            shutil.move(new_image_path, image_dir / name)
        new_dir_name.rmdir()


if __name__ == '__main__':
    main()
