import argparse
import pathlib
import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm
from dvc.repo import Repo


def get_url(repo, path):
    index, entry = repo.get_data_index_entry(path)
    remote_fs, remote_path = index.storage_map.get_remote(entry)
    return remote_fs.unstrip_protocol(remote_path)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=str, default='chocassye')
    args = parser.parse_args()

    conn = psycopg2.connect(
        host="localhost",
        database=args.db,
        user="postgres",
        password="password",
    )
    print(f"Connected to database: {args.db}")

    root = pathlib.Path(__file__).parent
    data_dir = root / "data"

    images = [
        *data_dir.rglob("scans/*/*/*.jpg"),
        *data_dir.rglob("scans/*/*/*.png"),
    ]
    print(f"Found {len(images)} images.")

    repo = Repo(str(pathlib.Path(__file__).parent))
    results = [
        {'path': image_path, 'url': get_url(repo, str(image_path))}
        for image_path in tqdm(images)
    ]

    tuples = []
    for result in results:
        path = result['path']
        url = result['url']
        book_name = path.parent.parent.name
        edition = path.parent.name
        page_name = path.stem
        splits = page_name.split("+")
        if len(splits) == 2:
            section = None
            page = splits[1]
        elif len(splits) == 3:
            section = splits[1]
            page = splits[2]
        else:
            print("Cannot parse page name:", path)
            continue
        tuples.append((book_name, edition, section, page, url))

    with conn.cursor() as cur:
        # first, delete all previous contents
        cur.execute("TRUNCATE TABLE images;")
        execute_values(
            cur,
            "INSERT INTO public.images (book_name, edition, section, page, url) VALUES %s;",
            tuples,
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
