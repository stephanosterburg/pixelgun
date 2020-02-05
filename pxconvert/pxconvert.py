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
import yagmail
import colorama  # https://pypi.org/project/colorama/
import platform
import subprocess

from glob import glob
from tqdm import tqdm
from shutil import copyfile
from queue import PriorityQueue
from click import command, option
from colorama import Fore

__author__ = "Stephan Osterburg"
__copyright__ = "Copyright 2020, Pixelgun Studio"
__credits__ = ["Stephan Osterburg", "Mauricio Baiocchi"]
__license__ = "MIT"
__version__ = "0.1.1"
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

    raw_images = glob(directory + '/' + player + '/_acquisition/*/*')
    # raw_images = glob('/Volumes/Bigfoot/Pixelgun_Dev/stephan/StephanTesting/testTeam/jefferson_amile/_acquisition/01_12_2020_jefferson_amile_brow_furrow_tk1/*')

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


def convert_to_tiff(directory, player):
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

    raw_images = glob(directory + '/' + player + '/_acquisition/*/*')
    # raw_images = glob('/Volumes/Bigfoot/Pixelgun_Dev/stephan/StephanTesting/testTeam/jefferson_amile/_acquisition/01_12_2020_jefferson_amile_brow_furrow_tk1/*')

    # Create log
    log_file = '/tmp/' + player + '.log'
    logging.basicConfig(filename=log_file, filemode='a', level=logging.INFO)

    # Build a list with all image conversion commands to be executed
    for raw_image in tqdm(raw_images):
        name, suffix = os.path.splitext(raw_image)

        if suffix and re.match(suffix, '.CR2', re.IGNORECASE):
            # Insert TIFF name into directory and set tif file name
            k = name.rfind('/')
            new_name = name[:k] + '/TIFF/' + name[k + 1:]
            tif_image = new_name + '.tif'

            # Create TIFF Directory
            tiff_dir = name[:k] + '/TIFF'
            if not os.path.isdir(tiff_dir):
                os.mkdir(tiff_dir)

            cmd = app + ' ' + scpt + ' ' + raw_image + ' ' + tif_image
            # wait for command to complete
            subprocess.call(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Create log file for all failed conversion
            if imghdr.what(tif_image) != 'tiff':
                logging.info("{} did NOT convert".format(raw_image.split('/')[-1]))

    print(Fore.GREEN + 'DONE')


def check_log(player):
    """Send log file if not empty and remove it

    :param player: Name of the player
    :return: None
    """
    receiver = 'sunny@pixelgunstudio.com'
    subject = f'FAILED conversion for {player}'
    filename = f'/tmp/{player}.log'

    yag = yagmail.SMTP(user='info@pixelgunstudio.com')
    yag.send(
        to=receiver,
        subject=subject,
        attachments=filename,
    )

    os.remove(f'/tmp/{player}.log')


def clear_screen():
    _ = subprocess.run('clear' if os.name == 'posix' else 'cls')


@command()
@option('--game', '-g', default='2K_1018_NBA2K21', help='Game name', type=str, required=True)
@option('--team', '-t', help='Team name', type=str, required=True)
@option('--player', '-p', help='Player name', type=str, required=True)
@option('--card', '-c', help='Color Card', type=str)
def main(game, team, player, card):
    """
    Converting the images from CR2 to TIFF16 using Adobe Photoshop CC 2019.

    \b
    game:      Game name, i.e. 2K_1018_NBA2K21 [Default]
    team:      Team name, i.e. 'det' for the 'Detroit Pistons'
    player:    Player name, i.e. 'king_louis'
    card:      To use color card, pass in the date of the shoot, i.e. 01_03_2020
    """

    # Call function to clear screen
    clear_screen()

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
    q.put(2, convert_to_tiff(path, player))
    # Remove XMP function
    q.put(3, copy_xmp(path, player, color_card, False))

    while not q.empty():
        q.get()

    # Check for failed image conversions and send log if needed
    # TODO: send email when done including the log file if needed
    if os.stat(f'/tmp/{player}.log').st_size > 0:
        # check_log(player)
        print(Fore.RED + "There are some failed images for {}".format(player))
        print(Fore.RED + "Check log file: {}".format(f'/tmp/{player}.log'))
    else:
        os.remove(f'/tmp/{player}.log')

    # Stop using colorama to restore 'stdout' and 'stderr' to their original values.
    colorama.deinit()


if __name__ == '__main__':
    main()
