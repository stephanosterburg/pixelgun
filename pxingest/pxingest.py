#!/usr/bin/env python3

"""
Ingest (move) given data from the T2 trailer into the pipeline/client project
and fixes the naming (simplify) in the process
"""

import os
import re
import sys
import glob
import time
import shlex
import errno
import shutil
import colorama  # https://pypi.org/project/colorama/
import platform
import subprocess
import multiprocessing as mp

from pathlib import Path
from multiprocessing import Pool
from tqdm import tqdm
from queue import PriorityQueue
from click import argument, command
from colorama import Fore, Style
from dateutil.parser import *  # python-dateutil

__author__ = "Stephan Osterburg"
__copyright__ = "Copyright 2020, Pixelgun Studio"
__credits__ = ["Stephan Osterburg", "Mauricio Baiocchi"]
__license__ = "MIT"
__version__ = "0.1.1"
__maintainer__ = ""
__email__ = "info@pixelgunstudio.com"
__status__ = "Production"

# Import other pixelgun modules
try:
    if platform.system() == 'Darwin':
        if os.path.isdir('/Volumes/Bigfoot/Pixelgun_Resources/python/pxmodules'):
            sys.path.insert(0, '/Volumes/Bigfoot/Pixelgun_Resources/python/pxmodules')
    elif platform.system() == 'Linux':
        if os.path.isdir('/mnt/bigfoot/Pixelgun_Resources/python/pxmodules'):
            sys.path.insert(0, '/mnt/bigfoot/Pixelgun_Resources/python/pxmodules')
except NameError:
    pass

# from px_image_proofs import *

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


def is_date(directory, fuzzy=False):
    """
    Return True or False if the string can be interpreted as a date.

    Args:
        directory: str, string to check for date
        fuzzy: bool, ignore unknown tokens in string if True

    Returns: True or False
    """
    try:
        parse(directory, fuzzy=fuzzy)
        return True
    except ValueError:
        return False


def clean_cameras(directory):
    """
    Rename given file names
    Args:
        directory: base directory with all pose directories

    Returns: None
    """

    for _, _, filenames in os.walk(directory):
        for filename in filenames:
            name, suffix = os.path.splitext(filename)
            name = "_".join(name.split("_", 2)[:2])  # grep base name
            dst = name + suffix

            try:
                # rename filename
                os.rename(directory + '/' + filename, directory + '/' + dst)
            except ValueError:
                print(Fore.RED + "Couldn't rename {}".format(filename))


def get_user_input(prompt, cast=str, cond=(lambda x: True), onerror=None):
    """
    Get input from the user (see https://stackoverflow.com/a/53522191)

    Args:
        prompt: text to be displayed
        cast: default value is str
        cond: condition, check if user input is either one of the following letters 'n', 'y'
        onerror: error message

    Returns:
        data: the users answer
    """
    if onerror is None:
        onerror = {}

    while True:
        try:
            data = cast(input(prompt))
            if not cond(data):
                raise ValidationError

            if data is 'n':
                print('Exiting...')
                sys.exit(0)

            return data
        except tuple(onerror.keys()) as e:
            print(onerror[type(e)])


def ingest_player(player, team_dir, player_dict, path, date_stamp):
    """Main ingest call

    Args:
        player: player name
        team_dir: team name
        player_dict: dictionary of all player and the taken poses
        path: where the project is located
        date_stamp:

    Returns: None

    """
    subdirs = ['Agisoft', 'Mudbox', 'Wrap', '_deliverables', '_settings',
               'Maya', 'Photoshop', '_acquisition', '_scratch', '_staging']

    player_dir = '%s/%s' % (team_dir, player)

    if not os.path.isdir(player_dir):
        # shutil.copytree(GlobalDirs.template, player_dir)
        try:
            shutil.copytree(GlobalDirs.template, player_dir)
        except OSError as exc:  # python >2.5
            if exc.errno == errno.ENOTDIR:
                shutil.copy(GlobalDirs.template, player_dir)
            else:
                raise

        # Create default sub-directories
        for d in subdirs:
            subdir = player_dir + '/' + d
            if not os.path.exists(subdir):
                Path(subdir).mkdir(parents=True, exist_ok=True)

    for take in player_dict[player]:
        source = '%s/%s' % (path, take)
        target_take = '%s_%s' % (date_stamp, '_'.join(take.split('_')[1:]))
        print(Fore.YELLOW + '\t%s' % target_take)

        # put the next two steps into a PriorityQueue to make sure that moving the data
        # has finished first before we clean up the naming
        q.put(1, shutil.move(source, '%s/_acquisition/%s' % (player_dir, target_take)))
        q.put(2, clean_cameras('%s/_acquisition/%s' % (player_dir, target_take)))

        while not q.empty():
            q.get()


def ingest_data(job, team, path, color_card):
    """
    Main process to get all data into the correct place and clean it at the same time

    Args:
        job: project name
        team: team name
        path: where the project is located
        color_card: color card to be used for image conversion

    Returns: None
    """

    # Check if the project name a date, i.e.: 12_10_2019?
    date_stamp = os.path.basename(path)
    date_str = date_stamp.replace('_', '-')
    if not is_date(date_str):
        print(Fore.RED + 'Folder does not appear to have a date in it')
        sys.exit(1)

    # build a dictionary out of the player data
    player_dict = {}
    dir_list = os.listdir(path)

    for directory in dir_list:
        dir_path = '%s/%s' % (path, directory)
        if os.path.isdir(dir_path):

            # extract player name: 4_carbonel_ray_neutral_tk3 -> carbonel_ray
            temp = directory.split('_')
            if len(temp) >= 5:
                player = '_'.join(temp[1: 3])

                if player not in player_dict:
                    player_dict[player] = []

                player_dict[player].append(directory)

    # Create new project based on template
    team_dir = '%s/%s/Sections/%s' % (GlobalDirs.projects, job, team)
    if not os.path.isdir(team_dir):
        shutil.copytree(GlobalDirs.template, team_dir)

    # Find a color card for the player
    if 'color_card' in player_dict:
        if len(player_dict['color_card']) > 1:
            color_card_take = pick_project('Choose Color Card Take: ', player_dict['color_card'])
            color_card = '%s/%s' % (path, color_card_take)
        else:
            take = player_dict['color_card'][0]
            color_card = '%s/%s' % (path, take)

        if color_card is None:
            print(Fore.YELLOW + 'Color Card not found')
            user_input = get_user_input('Continue Anyways? [y/n] ', cond=lambda x: x in 'yn',
                                        onerror={ValidationError: "Must be either y or n", ValueError: "Not a letter"})

            if user_input == 'n':
                sys.exit(1)
        else:
            print('Color Card: {}'.format(color_card))

            # move it to the right place
            color_card_path = '%s/%s/Source_Pixelgun/Color Charts/%s' % (GlobalDirs.projects, job, date_stamp)
            if not os.path.isdir(color_card_path):
                # os.mkdir(color_card_path)
                Path(color_card_path).mkdir(parents=True, exist_ok=True)

            # Find and copy color card
            color_card_images = 0
            filenames = os.listdir(color_card)
            for filename in filenames:
                if 'AR008_POLO' in filename:
                    name, suffix = filename.split('.')
                    filename = color_card + '/' + filename

                    # JPEG
                    if re.match(suffix, 'JPG', re.IGNORECASE):
                        shutil.copy(filename, '%s/px_color_card_%s.jpg' % (color_card_path, date_stamp))
                        color_card_images += 1
                    # CR2
                    elif re.match(suffix, 'CR2', re.IGNORECASE):
                        shutil.copy(filename, '%s/px_color_card_%s.cr2' % (color_card_path, date_stamp))
                        color_card_images += 1
                    else:
                        print(Fore.YELLOW + 'Color Card %s not found!' % color_card)

            if color_card_images < 2:
                print(Fore.GREEN + 'Found %s of 2 Color Card images' % color_card_images)
                user_input = get_user_input('Continue Anyways? [y/n] ', cond=lambda x: x in 'yn',
                                            onerror={ValidationError: "Must be either y or n",
                                                     ValueError: "Not a letter"})

                if user_input == 'n':
                    sys.exit(1)

    # Move (pxingest) data from _incoming to _acquisition
    prompt = 'Do you want to ingest all players of the team at once? [y/n] '
    user_input = get_user_input(prompt, cond=lambda x: x in 'yn',
                                onerror={ValidationError: "Must be either y or n", ValueError: "Not a letter"})
    if user_input == 'y':
        for player in player_dict:
            if player != 'color_card':
                ingest_player(player, team_dir, player_dict, path, date_stamp)
    else:
        for player in player_dict:
            if player != 'color_card':
                prompt = 'Ingest [' + Fore.YELLOW + player + Style.RESET_ALL + ']? [y/n] '
                user_input = get_user_input(prompt, cond=lambda x: x in 'yn',
                                            onerror={ValidationError: "Must be either y or n",
                                                     ValueError: "Not a letter"})

            if user_input == 'y':
                ingest_player(player, team_dir, player_dict, path, date_stamp)


def list_projects():
    """Return a list of all projects"""
    projects = os.listdir(GlobalDirs.projects)
    jobs = [project for project in projects if not project.startswith(('_', '.DS_Store', 'Thumbs.db'))]

    return jobs


def pick_project(msg, options):
    """
    Pick a project from a list of all current projects

    Args:
        msg: Message to be printed
        options: list of all projects

    Returns:
        options: users project selection
    """
    print(msg)

    nums = list(range(0, len(options)))
    jobs = [str(k) + ":\t" + v for k, v in zip(nums, options)]
    # print(*jobs, sep='\n')
    print('\n'.join(map(str, jobs)))

    prompt = "Enter a value between 0 - " + str(len(options)-1) + ": "
    user_input = get_user_input(prompt, cast=int, cond=lambda x: 0 <= x <= len(options)-1,
                                onerror={ValidationError: "Must be between 0 and " + str(len(options)),
                                         ValueError: "Not a number"})

    return options[user_input]


def clear_screen():
    _ = subprocess.run('clear' if os.name == 'posix' else 'cls')


@command()
@argument('directory')
def main(directory):
    """
    Getting incoming data from T2, gather all information's, like project, team and player name
    then fix naming and moving the data to a

    Args:
        directory: Directory Name, i.e.: 12_10_2019 or /Volumes/Bigfoot/_incoming/12_10_2019
    """

    # Call function to clear screen
    clear_screen()

    # Check if given directory is valid
    path = ''
    if len(directory) == 10:
        path = os.path.realpath(GlobalDirs.incoming + directory)
    elif len(directory) > 10 and GlobalDirs.incoming in directory:
        path = os.path.realpath(directory)

    if not os.path.isdir(path):
        print(Fore.RED + 'Error: Path is invalid!')
        sys.exit(1)

    # List all current projects and choose one
    project = pick_project('Choose a destination projects: ', list_projects())

    # Enter the team name
    team = get_user_input('Enter Team name: (Enter to use default) ')
    # The following lambda call in the get_user_input doesn't work here
    # cond=lambda x: 'default' if x == '' else x
    if team is '':
        team = 'default'

    # Define Color Card
    color_card = '%s/%s/Source_Pixelgun/Color_Correction/%s/%s{0}'.format(
        (GlobalDirs.projects, project, directory, directory + '_cc.xmp'))
    if not os.path.isfile(color_card):
        color_card = '{}/{}/Source_Pixelgun/Color_Correction/01_03_2020/01_03_2020_cc.xmp'.format(GlobalDirs.projects,
                                                                                                  project)

    print('\n')
    print(Fore.BLUE + "Project:\t{}".format(project))
    print(Fore.BLUE + "Team:\t\t{}".format(team))
    print(Fore.BLUE + "CCard:\t\t{}".format(directory + '_cc.xmp'))
    print('\n')

    # Finally, working on the data
    ingest_data(project, team, path, color_card)

    # Stop using colorama to restore 'stdout' and 'stderr' to their original values.
    colorama.deinit()


if __name__ == '__main__':
    main()
