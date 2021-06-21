REQUIRED_DISK_SPACE = 100 * (2**20) # Bail if free space is less than 100MiB


import os
import sys
import json
import errno
import shutil
import requests
import traceback
from urllib import request
from urllib.parse import urlparse

from tqdm import tqdm
import parsel
import esprima
from termcolor import colored


def note(*args, **kwargs):
    print(colored("imgur-dl.py:", attrs=["bold"])
          + " "
          + args[0].format(*args[1:], **kwargs), file=sys.stderr)
    sys.stderr.flush()


def sanitize_path(path):
    result = path.strip()
    # Replace newlines with spaces
    result = result.translate(str.maketrans('\n', ' '))
    # Delete NTFS-unsupported characters
    result = result.translate(str.maketrans('', '', r'<>:"/\\|?*'))
    # Delete \x00-\x20
    result = result.translate(str.maketrans('', '', ''.join(chr(i) for i in range(32))))
    # Collapse multiple spaces into one
    result = ' '.join(result.split())
    return result


def main():
    for url in sys.argv[1:]:
        try:
            pr = urlparse(url)
            album_id = pr.path.rstrip('/').split('/')[-1]

            _, _, free = shutil.disk_usage('.')

            if free < REQUIRED_DISK_SPACE:
                raise RuntimeError('Disk space running low, refusing to continue')

            note("Album ID: {}", album_id)

            source_uri = f"https://imgur.com/a/{album_id}/embed?pub=true"

            headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 "\
                                     "Build/KOT49H) AppleWebKit/537.36 (KHTML, like "\
                                     "Gecko) Chrome/34.0.1847.114 Mobile Safari/537.36"}
            response = requests.get(source_uri, headers=headers)

            assert response.status_code == 200

            images = {}

            selector = parsel.Selector(text=response.content.decode('utf-8'))
            title = selector.css('#title-text::text').get()
            if title is None:
                note("Gallery has no title")
                newdir = "{}".format(album_id)
                os.mkdir(newdir)
            else:
                images['title'] = title
                title = sanitize_path(title)
                note("Title: {}", title)
                while True:
                    try:
                        newdir = "{} - {}".format(title, album_id)
                        os.mkdir(newdir)
                        break
                    except OSError as e:
                        if e.errno == errno.ENAMETOOLONG:
                            if len(title) == 0:
                                newdir = "{}".format(album_id)
                                os.mkdir(newdir)
                                break
                            title = title[:-4] + '...'
                            continue
                        else:
                            raise

            scripts = selector.css('script:not([src])::text').getall()

            # with open(os.path.join(newdir, 'script.js'), 'w') as script_js:
                # script_js.write(script)

            def parse_delegate(node, range):
                if node.type == 'VariableDeclarator' and node.id.name == 'images':
                    global images
                    start, end = node.init.range
                    data = json.loads(script[start:end])
                    if 'count' in data and 'images' in data:
                        images.update(data)
            try:
                for script in scripts:
                    esprima.parseScript(script, options={'range': True}, delegate=parse_delegate)
            except esprima.error_handler.Error as e:
                if 'images' in images:
                    note("Non-fatal parser exception: {}", str(e))
                else:
                    raise

            with open(os.path.join(newdir, 'images.json'), 'w') as images_json:
                json.dump(images, images_json, indent=4)

            assert images['count'] == len(images['images'])
            total = len(images['images'])

            tqdm_bar_format = '{desc:<2.5}{percentage:3.0f}%|{bar:40}{r_bar}'

            for i, image in enumerate(tqdm(images['images'], unit='img',
                                           bar_format=tqdm_bar_format,
                                           position=0, miniters=1)):
                hash = image['hash']
                ext = image['ext']
                index = "{{:0{}d}}".format(len(str(images['count']))).format(i+1)

                with tqdm(total=image['size'], unit='b', unit_scale=True,
                          bar_format=tqdm_bar_format, position=1, leave=False,
                          miniters=1) as progress:
                    downloaded = 0
                    def updatehook(nblocks, bsize, fsize):
                        global downloaded
                        progress.update(nblocks*bsize - downloaded)
                        downloaded = nblocks*bsize

                    dlurl = 'https://i.imgur.com/{}{}'.format(hash, ext)
                    dlfile = '{} - {}{}'.format(index, hash, ext)
                    request.urlretrieve(dlurl, os.path.join(newdir, dlfile), updatehook)
                    request.urlcleanup()
        except Exception as e:
            traceback.print_exc()
            note("Failed to download: {}", url)
            request.urlcleanup()

if __name__ == "__main__":
    main()
