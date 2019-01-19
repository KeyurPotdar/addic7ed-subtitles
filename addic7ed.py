import logging
import os
import re
import sys
import tkinter as tk

import requests
from bs4 import BeautifulSoup

LOG_FILE = os.path.splitext(os.path.abspath(__file__))[0] + '.log'
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format='%(asctime)s %(message)s ')

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

ALL_MEDIA_EXTENSIONS = {".avi", ".mp4", ".mkv", ".mpg", ".mpeg", ".mov", ".rm", ".vob", ".wmv", ".flv", ".3gp", ".3g2"}


def format_url(name, season, episode):
    """
    Returns the URL formed by using `name`, `season` and `episode`.

    Example:
    >>> url = format_url('the.office', 2, 3)
    >>> url
    'http://www.addic7ed.com/serie/the%20office/2/3/1'
    """
    return 'http://www.addic7ed.com/serie/{0}/{1}/{2}/1'.format(name.replace('.', '%20'), season, episode)


def download_sub(link, root, session, srt_path, referer, version):
    """
    Downloads the subtitle file and saves at the location given by `srt_path`

    :param link: subtitle url
    :param root: root window of Tk
    :param session: requests.Session object
    :param srt_path: location of subtitle
    :param referer: Referer required for header
    :param version: subtitle version
    """
    try:
        root.destroy()
        r = session.get('http://www.addic7ed.com'+link,
                        headers={'User-Agent': headers['User-Agent'], 'Referer': referer})
        with open(srt_path, 'wb') as f:
            f.write(r.content)
        logging.info('Downloaded {!r} for {!r}'.format(version, srt_path))
    except Exception as e:
        logging.error(str(e), exc_info=True)
        return


def get_version_set(v):
    """
    Returns a set containing all versions which map to the version
    """
    version_mapper = [
        ('sva', 'avs'),
        ('avs', 'sva'),
        ('web-tbs', 'web.x264-tbs'),
        ('repack.deflate', 'deflate'),
        ('hdtv.killers', 'hdtv.x264-killers'),
        ('hdtv.avs_sva', 'avs'),
        ('hdtv.avs_sva', 'sva'),
        ('repack.amzn.web-dl-ntb', 'repack.amzn.web-dl.ddp5.1.h.264-ntb'),
        ('amzn.web-dl-ntb', 'amzn.web-dl.ddp5.1.h.264-ntb'),
    ]
    all_versions = {v}

    for old, new in version_mapper:
        all_versions.add(v.replace(old, new))

    return all_versions


def show_subtitles(url, srt_path, auto_download=True):
    """
    Scrapes www.addic7ed.com and displays all available subtitles.
    If `auto_download` is `True`, downloads the version matching subtitle automatically.
    If a version matching subtitle is not found, displays all available subtitles.
    """
    try:
        with requests.Session() as session:
            r = session.get(url, headers=headers)
            soup = BeautifulSoup(r.text, 'lxml')
            all_subtitles = []
            for sub in soup.find_all('td', colspan='3', class_='NewsTitle'):
                table = sub.find_parent('table')
                version = sub.text.strip()
                downloads = table.find_all('tr')[3].td.text
                downloads = int(re.search(r'(\d+)\s+Downloads', downloads).groups()[0])
                language = table.find('td', class_='language').text.strip()
                link = table.find_all('tr')[2].select('.buttonDownload')[-1]['href']
                if language == 'English':
                    all_subtitles.append((version, downloads, language, link))

            # Sort the subtitles w.r.t. number of downloads
            all_subtitles.sort(key=lambda k: -k[1])

            root = tk.Tk()
            root.title(os.path.split(srt_path)[1])
            for col, label in enumerate(['Sr No', 'Version', 'Downloads', 'Language', 'Link']):
                tk.Label(root, text=label).grid(column=col, row=0, sticky=tk.W, padx=10, pady=10)

            for row, sub in enumerate(all_subtitles, 1):
                version, downloads, language, link = sub

                if auto_download:
                    # Automatically download the version matching subtitle
                    v = version.split('Version ')[1].split(',')[0].lower().replace(' ', '.')
                    if any(ver in srt_path.lower() for ver in get_version_set(v)):
                        print('Auto-download:', srt_path)
                        download_sub(link=link, root=root, session=session,
                                     srt_path=srt_path, referer=url, version=version)
                        return

                for col, label in enumerate([row, version, downloads, language]):
                    tk.Label(root, text=label).grid(column=col, row=row, sticky=tk.W, padx=5, pady=5)
                tk.Button(root, text='Download', command=lambda c=link: download_sub(link=c, root=root, session=session,
                                                                                     srt_path=srt_path, referer=url,
                                                                                     version=version))\
                    .grid(column=4, row=row, sticky=tk.W, padx=10, pady=5)

            root.mainloop()
    except Exception as e:
        logging.error(str(e), exc_info=True)
        return


def analyze_path(full_path):
    """
    Downloads the subtitle if the file is a media file and the SRT file for this file does not exist
    """
    file_path, extension = os.path.splitext(full_path)

    # If file is not a media file, or an SRT file for the media file already exists, skip the file
    if extension not in ALL_MEDIA_EXTENSIONS or os.path.exists(file_path+'.srt'):
        return

    path, file = os.path.split(file_path)
    try:
        # Get name, season, episode from the file name
        # Can only match files with the format: (tv_show_name)s(season_number)e(episide_number)
        name, season, episode = re.search(r'(.*)[sS](\d\d)[eE](\d\d)', file).groups()
    except AttributeError:
        logging.info('Invalid RegEx for file: {}'.format(full_path))
        return

    name = name.rstrip('.').lower()

    # Special cases (personalization)
    name = name.replace('shameless us', 'shameless (us)')

    url = format_url(name, season, episode)
    show_subtitles(url, file_path+'.srt')


def main():
    for path in sys.argv:
        if os.path.isdir(path):
            for dir_path, _, file_names in os.walk(path):
                for filename in file_names:
                    file_path = os.path.join(dir_path, filename)
                    analyze_path(file_path)
        else:
            analyze_path(path)


if __name__ == '__main__':
    main()
