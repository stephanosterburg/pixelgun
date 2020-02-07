#!/usr/bin/env python3

"""
Converting Canon Camera RAW (CR2) images to TIFF 16 bit

Using Adobe Photoshop CC 2019 via applescript and javascript
The python code is a wrapper to copy/remove the XMP file along side the CR2 images
and calls osascript to execute an applescript to activate PS and run a javascript
"""

import os
import re
import sys
import imghdr
import shlex
import logging
import signal
import colorama  # https://pypi.org/project/colorama/
import platform
import subprocess

from glob import glob
from tqdm import tqdm
from pathlib import Path
from shutil import copyfile
from queue import PriorityQueue
from click import command, option
from colorama import Fore

__author__ = "Stephan Osterburg"
__copyright__ = "Copyright 2020, Pixelgun Studio"
__credits__ = ["Stephan Osterburg", "Mauricio Baiocchi"]
__license__ = "MIT"
__version__ = "0.1.4"
__maintainer__ = ""
__email__ = "info@pixelgunstudio.com"
__status__ = "Production"

# Initialise Queue
q = PriorityQueue()

# Initialise Colorama
colorama.init(autoreset=True)


class ValidationError(ValueError):
    pass


class GlobalDirs:
    """Global default directories"""

    def __init__(self):
        pass

    if platform.system() == 'Darwin':
        incoming = '/Volumes/Bigfoot/_incoming/'
        template = '/Volumes/Bigfoot/Pixelgun_Projects/_XX_XXXX_JobTemplate/Sections/_XX_generic_section'
        projects = '/Volumes/Bigfoot/Pixelgun_Projects'
    elif platform.system() == 'Linux':
        incoming = '/mnt/bigfoot/_incoming/'
        template = '/mnt/bigfoot/Pixelgun_Projects/_XX_XXXX_JobTemplate/Sections/_XX_generic_section'
        projects = '/mnt/bigfoot/Pixelgun_Projects'

    # All the teams in the game available
    teams = {'atl': 'Atlanta Hawks',
             'bkn': 'Brooklyn Nets',
             'bos': 'Boston Celtics',
             'cel': 'Cleveland Cavaliers',
             'cha': 'Charlotte Hornets',
             'chi': 'Chicago Bulls',
             'dal': 'Dallas Mavericks',
             'den': 'Denver Nuggets',
             'det': 'Detroit Pistons',
             'gsw': 'Golden State Warriors',
             'hou': 'Houston Rockets',
             'ind': 'Indiana Pacers',
             'lac': 'Los Angeles Clippers',
             'lal': 'Los Angeles Lakers',
             'mem': 'Memphis Grizzlies',
             'mia': 'Miami Heat',
             'mil': 'Milwaukee Bucks',
             'min': 'Minnesota Timberwolves',
             'nop': 'New Orleans Pelicans',
             'nyk': 'New York Knicks',
             'okc': 'Oklahoma City Thunder',
             'orl': 'Orlando Magic',
             'phi': 'Philadelphia 76ers',
             'phx': 'Phoenix Suns',
             'por': 'Portland Trail Blazers',
             'sac': 'Sacramento Kings',
             'sas': 'San Antonio Spurs',
             'tor': 'Toronto Raptors',
             'uta': 'Utah Jazz',
             'was': 'Washington Wizards'}

    # IP addresses of all machines in the farm
    machines = {'px10': '10.0.53.110',
                'px11': '10.0.53.111',
                'px12': '10.0.53.112',
                'px13': '10.0.53.113',
                'px14': '10.0.53.114'}


def copy_xmp(directory, player, src_xmp, task):
    """Copy XMP template along  side every Camera RAW image so that
    the conversion process in Adobe PS does the right thing

    :param directory: path to the team
    :param player: name of a player
    :param src_xmp: XMP file to be copied
    :return: None
    """

    if task:
        print(Fore.YELLOW + 'Copying XMP...')
    else:
        print(Fore.YELLOW + 'Cleaning XMP...')

    # raw_images = glob('/Volumes/Bigfoot/Pixelgun_Dev/stephan/StephanTesting/testTeam/jefferson_amile/_acquisition/01_12_2020_jefferson_amile_brow_furrow_tk1/*')
    # directory = '/Volumes/Bigfoot/Pixelgun_Dev/stephan/StephanTesting/testTeam'
    raw_images = glob(directory + '/' + player + '/_acquisition/*/*')

    for raw_image in raw_images:
        name, suffix = os.path.splitext(raw_image)
        if suffix and re.match(suffix, '.CR2', re.IGNORECASE):
            # Copy XMP template to be side by side with the CR2 images
            k = name.rfind('/')
            new_name = name[:k] + '/' + name[k + 1:]
            dst_xmp = new_name + '.xmp'

            if task:
                copyfile(src_xmp, dst_xmp)
            else:
                os.remove(dst_xmp)

    print(Fore.GREEN + 'DONE')


def convert_to_tiff(directory, player, *args, **kwargs):
    """Convert CR2 to TIFF 16bit
    Create a TIFF sub-directory and run Adobe Photoshop to convert the images

    :param directory: directory name of the team
    :param  player: either the name of a player
    :return: None
    """
    print(Fore.YELLOW + 'Converting CR2 to TIFF16...')

    # Execute Adobe PS via osascript to convert CR2 to TIFF16 with javascript
    app = '/usr/bin/osascript'
    scpt = '/Users/px/Projects/pxconvert/convert_img.scpt'

    # raw_images = glob('/Volumes/Bigfoot/Pixelgun_Dev/stephan/StephanTesting/testTeam/jefferson_amile/_acquisition/01_12_2020_jefferson_amile_brow_furrow_tk1/*')
    # directory = '/Volumes/Bigfoot/Pixelgun_Dev/stephan/StephanTesting/testTeam'

    # Get Camera RAW images
    pose = kwargs.get('pose', None)
    if pose is None:
        raw_images = glob(directory + '/' + player + '/_acquisition/*/*')
    else:
        poses = glob(directory + '/' + player + '/_acquisition/*')
        poses = [s for s in poses if pose in s]
        if len(poses) > 1:
            pose = poses[0].split('/')[-1][:-4]
        else:
            pose = poses[0].split('/')[-1]

        raw_images = glob(directory + '/' + player + '/_acquisition/' + pose + '*/*')

    # Get all poses
    poses = glob(directory + '/' + player + '/_acquisition/*')
    # Drop tiff from list if already exists
    item = [x for x in poses if 'tiff' in x]
    if len(item) != 0:
        idx = poses.index(item[0])
        poses.pop(idx)
    # Create tiff directory
    for pose in poses:
        dir_list = pose.split('/')
        tiff_dir = Path('/'.join(dir_list[:-1]) + '/tiff/' + dir_list[-1])
        tiff_dir.mkdir(parents=True, exist_ok=True)

    # Create log
    log_file = '/tmp/' + player + '.log'
    logging.basicConfig(filename=log_file, filemode='a', level=logging.INFO)

    # Build a list with all image conversion commands to be executed
    for raw_image in tqdm(raw_images):
        name, suffix = os.path.splitext(raw_image)

        if suffix and re.match(suffix, '.CR2', re.IGNORECASE):
            # Insert TIFF name into directory and set tif file name
            dir_list = raw_image.split('/')
            tiff_dir = '/'.join(dir_list[:-2]) + '/tiff'
            if not os.path.isdir(tiff_dir):
                os.mkdir(tiff_dir)

            tif_image = tiff_dir + '/' + '/'.join(dir_list[-2:])
            tif_image = tif_image.split('.')[0] + '.tif'

            cmd = app + ' ' + scpt + ' ' + raw_image + ' ' + tif_image
            # Using the call function to wait for command to complete
            subprocess.call(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Create log file for all failed conversion
            if imghdr.what(tif_image) != 'tiff':
                logging.info("{} did NOT convert".format(raw_image.split('/')[-1]))

    print(Fore.GREEN + 'DONE')


def clear_screen():
    _ = subprocess.run('clear' if os.name == 'posix' else 'cls')


@command()
@option('--game', '-g', default='2K_1018_NBA2K21', help='Game name', type=str, required=True)
@option('--team', '-t', help='Team name', type=str, required=True)
@option('--player', '-p', help='Player name', type=str, required=True)
@option('--directory', '-d', default=None, help='Directory of a pose', type=str)
@option('--card', '-c', help='Color Card', type=str)
def main(game, team, player, directory, card):
    """
    Converting the images from CR2 to TIFF16 using Adobe Photoshop CC 2019.

    \b
    game:      Game name, i.e. 2K_1018_NBA2K21 [Default]
    team:      Team name, i.e. 'det' for the 'Detroit Pistons'
    player:    Player name, i.e. 'king_louis'
    directory: Directory name of a pose, either as full name or pose name,
               i.e.: 01_12_2020_jefferson_amile_yell_angry_tk2 OR yell_angry
    card:      To use color card, pass in the date of the shoot, i.e. 01_03_2020
    """

    # Call function to clear screen
    clear_screen()

    # If Photoshop runs already kill it
    process = subprocess.Popen('pgrep Photoshop', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pid, err = process.communicate()
    os.kill(int(pid.decode("utf-8")), signal.SIGKILL)

    # Check if given directory is valid, i.e.: /Pixelgun_Projects/2K_1018_NBA2K21/Sections/orl/birch_khem
    path = os.path.realpath(GlobalDirs.projects + "/" + game + "/Sections/" + team)
    if not os.path.isdir(path):
        print(Fore.RED + 'Error: Path is invalid!')
        sys.exit(1)

    if len(player.split()) == 1:
        player_name = ' '.join(map(str, player.split('_')[::-1])).title()

    # Define Color Card
    if card:
        color_card = f'{GlobalDirs.projects}/{game}/Source_Pixelgun/Color_Correction/{card}/{card}_cc.xmp'
    else:
        _ = glob(f'{GlobalDirs.projects}/{game}/Source_Pixelgun/Color_Correction/*')
        latest_card = max(_, key=os.path.getctime).split('/')[-1]
        color_card = f'{GlobalDirs.projects}/{game}/Source_Pixelgun/Color_Correction/{latest_card}/{latest_card}_cc.xmp'

    if team in GlobalDirs.teams:
        team_name = GlobalDirs.teams[team]
    else:
        team_name = team

    print('\n')
    print(Fore.BLUE + "Project:\t{}".format(game))
    print(Fore.BLUE + "Team:\t\t{}".format(team_name))
    print(Fore.BLUE + "Player:\t\t{}".format(player_name))
    print('\n')

    # Copy XMP function
    q.put(1, copy_xmp(path, player, color_card, True))
    # Convert Camera RAW to TIFF
    q.put(2, convert_to_tiff(path, player, pose=directory))
    # Remove XMP function
    q.put(3, copy_xmp(path, player, color_card, False))

    while not q.empty():
        q.get()

    # Check for failed image conversions and send log if needed
    if os.stat(f'/tmp/{player}.log').st_size > 0:
        print(Fore.RED + "There are some failed images for {}".format(player))
        print(Fore.RED + "Check log file: {}".format(f'/tmp/{player}.log'))
    else:
        os.remove(f'/tmp/{player}.log')

    # Stop using colorama to restore 'stdout' and 'stderr' to their original values.
    colorama.deinit()


if __name__ == '__main__':
    main()
