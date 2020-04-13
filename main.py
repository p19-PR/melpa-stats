import requests
import json
import pickle
import sys
import os
import collections
from datetime import datetime
from multiprocessing import Pool

def env(key, default):
    return os.environ.get(key) if os.environ.get(key) else default

POOL_SIZE = int(env('POOL_SIZE', 0)) # default no threading
MAX_PACKAGES = int(env('MAX_PACKAGES', 0)) # default all packages
SAVE_FILE = 'save.p'
OUTPUT_FILE = env('OUTPUT_FILE', 'data.csv')

Package = collections.namedtuple('Package', 'name source owner download_count date_added')
Recipe = collections.namedtuple('Recipe', 'name source owner download_count')

def format_header():
    return 'name,source,owner,download_count,date_added'

def format_package(p):
    return f"{p.name},{p.source},{p.owner},{p.download_count},{p.date_added}"

def get_date_added(recipe):
    if not os.path.exists(f"melpa/recipes/{recipe}"):
        return ""
    stream = os.popen(f"cd melpa && git log --format=%at recipes/{recipe} | tail -1")
    output = stream.read()
    ts = int(output)
    date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
    return date

def get_recipe_list():
    r = requests.get('https://melpa.org/recipes.json')
    recipe_list = json.loads(r.content)

    def get_source(name):
        return recipe_list[name]['fetcher']

    def get_owner(name):
        d = recipe_list[name]
        if 'repo' in d:
            return d['repo'].split('/')[0]
        else:
            return ''

    return recipe_list, get_source, get_owner

def download_count_getter():
    r = requests.get('https://melpa.org/download_counts.json')
    download_counts = json.loads(r.content)

    def get_download_count(name):
        return download_counts[name]

    return get_download_count

def build_package(r):
    name = r.name
    source = r.source
    owner = r.owner
    dl = r.download_count

    print(f"Fetching {name}")
    date = get_date_added(name)

    return Package(name=name, source=source, owner=owner, download_count=dl, date_added=date)

def fetch_packages():
    recipe_list, get_source, get_owner = get_recipe_list()

    get_download_count = download_count_getter()

    if MAX_PACKAGES != 0:
        recipe_list = [r for r in list(recipe_list.keys())[0:MAX_PACKAGES]]

    l = [Recipe(name=r, source=get_source(r), owner=get_owner(r),
                download_count=get_download_count(r)) for r in recipe_list]

    if POOL_SIZE == 0:
        packages = [build_package(r) for r in l]
    else:
        with Pool(POOL_SIZE) as p:
            packages = p.map(build_package, l)

    return packages

def update_packages(packages):
    u = []
    recipe_list, get_source, get_owner = get_recipe_list()
    get_download_count = download_count_getter()

    for p in packages:
        name = p.name
        source = get_source(name)
        owner = get_owner(name)
        dl = get_download_count(name)
        date = p.date_added
        if date == '':
            date = get_date_added(name)

        u.append(Package(name=name, source=source, owner=owner, download_count=dl, date_added=date))

    return u

def pickle_packages(packages):
    if len(packages) > 0:
        pickle.dump(packages, open(SAVE_FILE, 'wb'))

def get_packages():
    if os.path.exists(SAVE_FILE):
        packages = update_packages(pickle.load(open(SAVE_FILE, 'rb')))
    else:
        packages = fetch_packages()

    pickle_packages(packages)

    return packages


def main():
    packages = get_packages()
    with open(OUTPUT_FILE, 'w') as output:
        output.write(format_header() + '\n')
        for p in packages:
            output.write(format_package(p) + '\n')


if __name__ == '__main__':
    main()
