import logging
import os
import re
import requests
import sys
import tkinter as tk
from bs4 import BeautifulSoup

LOG_FILE = os.path.splitext(os.path.abspath(__file__))[0] + '.log'
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format='%(asctime)s %(message)s ')

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

ALL_MEDIA_EXTENSIONS = {".avi", ".mp4", ".mkv", ".mpg", ".mpeg", ".mov", ".rm", ".vob", ".wmv", ".flv", ".3gp", ".3g2"}


def format_url(name, season, episode):
    return 'http://www.addic7ed.com/serie/{0}/{1}/{2}/1'.format(name, season, episode)


def download_sub(link, root, session, srt_path, referrer, version):
    try:
        root.destroy()
        r = session.get('http://www.addic7ed.com'+link,
                        headers={'User-Agent': headers['User-Agent'], 'Referer': referrer})
        with open(srt_path, 'wb') as f:
            f.write(r.content)
        logging.info('Downloaded {!r} for {!r}'.format(version, srt_path))
    except Exception as e:
        logging.error(str(e), exc_info=True)
        return


def show_subtitles(url, srt_path):
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

            all_subtitles.sort(key=lambda k: -k[1])

            root = tk.Tk()
            root.title(os.path.split(srt_path)[1])
            for col, label in enumerate(['Sr No', 'Version', 'Downloads', 'Language', 'Link']):
                tk.Label(root, text=label).grid(column=col, row=0, sticky=tk.W, padx=10, pady=10)

            for row, sub in enumerate(all_subtitles, 1):
                version, downloads, language, link = sub
                v = version.split('Version ')[1].split(',')[0].lower().replace(' ', '.')
                all_versions = {v, v.replace('sva', 'avs'), v.replace('avs', 'sva'),
                                v.replace('web-tbs', 'web.x264-tbs'), v.replace('repack.deflate', 'deflate'),
                                v.replace('hdtv.killers', 'hdtv.x264-killers'),
                                v.replace('hdtv.avs_sva', 'avs'), v.replace('hdtv.avs_sva', 'sva')}
                if any(v in srt_path.lower() for v in all_versions):
                    print('Auto-download:', srt_path)
                    download_sub(link=link, root=root, session=session,
                                 srt_path=srt_path, referrer=url, version=version)
                    return

                for col, label in enumerate([row, version, downloads, language]):
                    tk.Label(root, text=label).grid(column=col, row=row, sticky=tk.W, padx=5, pady=5)
                tk.Button(root, text='Download', command=lambda c=link: download_sub(link=c, root=root,
                                                                                     session=session,
                                                                                     srt_path=srt_path,
                                                                                     referrer=url,
                                                                                     version=version))\
                    .grid(column=4, row=row, sticky=tk.W, padx=10, pady=5)

            root.mainloop()
    except Exception as e:
        logging.error(str(e), exc_info=True)
        return


def analyze_path(full_path):
    file_path, extension = os.path.splitext(full_path)
    if extension not in ALL_MEDIA_EXTENSIONS or os.path.exists(file_path+'.srt'):
        return

    path, file = os.path.split(file_path)
    try:
        name, season, episode = re.search(r'(.*)[sS](\d\d)[eE](\d\d)', file).groups()
    except AttributeError:
        logging.info('Invalid RegEx for file: {}'.format(full_path))
        return

    name = name.rstrip('.').replace('.', '%20').lower()
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
