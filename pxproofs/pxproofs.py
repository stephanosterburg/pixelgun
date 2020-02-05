#!/usr/bin/env python3

"""
Create a PDF file (proof) of three predefined images of the head (left, front, right view)
alongside create a CSV file with all pose names by client and px to deliver to the client
"""

import os
import sys
import shlex
import shutil
import colorama  # https://pypi.org/project/colorama/
import platform
import subprocess
import pandas as pd
import numpy as np

from glob import glob
from click import option, command
from colorama import Fore
from queue import PriorityQueue
from fpdf import FPDF

__author__ = "Stephan Osterburg"
__copyright__ = "Copyright 2020, Pixelgun Studio"
__credits__ = ["Stephan Osterburg", "Mauricio Baiocchi"]
__license__ = "MIT"
__version__ = "0.1.1"
__maintainer__ = ""
__email__ = "info@pixelgunstudio.com"
__status__ = "Production"

# Initialise Queue
qi = PriorityQueue()
qo = PriorityQueue()

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


def clear_screen():
    """Clear shell"""
    _ = subprocess.run('clear' if os.name == 'posix' else 'cls')


def define_proof_name(pose, game, team):
    """
    Define base output file name for PDF and CSV
    Args:
        pose:
        game:
        team:

    Returns: base file name

    """
    output_dir = os.path.realpath(GlobalDirs.projects + "/" + game + "/Source_Pixelgun/Proof Sheets/" + team)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    proof_name = '_'.join(pose.split('/')[-1].split('_')[0:5])

    return output_dir + '/' + proof_name + '_selects'


def get_placeholder(player_pose, df):
    """Get placeholder string for the images
    Write out PROOF.csv

    Args:
        df: template dataframe
        player_pose: name of players pose

    Returns: Base name of pose, i.e. 'smile'
    """

    # Create "CHUNKS' column by getting all values from 'PX AQUISITION' where there are
    # NaN in 'CLIENT SHAPE NAMES' and combine them
    df['CHUNKS'] = np.where(df['CLIENT SHAPE NAMES'].isnull(), df['PX AQUISITION'], df['CLIENT SHAPE NAMES'])

    try:
        px_pose = '_'.join(player_pose.split('/')[-1].split('_')[5:-1])
        if px_pose not in df['PX AQUISITION'].values:
            _ = pd.DataFrame([[px_pose, px_pose, px_pose]],
                             columns=('PX AQUISITION', 'CLIENT SHAPE NAMES', 'CHUNKS'))
            df = pd.concat([df, _], ignore_index=True)

        # Get pose name
        pose_name = df.loc[df['PX AQUISITION'] == px_pose, 'CHUNKS'].iloc[0]
    except ValueError:
        print(Fore.RED + "Failed to read XLS file")
        return

    return pose_name


def create_proof(directory, team, player):
    """Create a proof of a given player using Nuke

    Args:
        directory: directory name of the team
        team: Name of the team
        player: either the name of a player or "all"

    Returns: None
    """
    print(Fore.YELLOW + "Creating JPEG's...")

    # Location of Nuke
    app = '/Applications/Nuke12.0v3/Nuke12.0v3.app/Contents/MacOS/Nuke12.0 -x -F 1 '

    proof_output = directory + '/' + player

    # Backward compatibility
    if os.path.isdir(proof_output + '/_acquisition/tiff'):
        poses = glob(proof_output + '/_acquisition/tiff/*')
    else:
        poses = glob(proof_output + '/_acquisition/*')

    # Open default CSV file (XLS)
    game = ''.join(directory.rsplit(GlobalDirs.projects)).split('/')[1]
    csv_file = GlobalDirs.projects + '/' + game + '/Source_Pixelgun/Settings/chunk_mappings.csv'
    in_df = pd.read_csv(csv_file)

    # Create delivery CSV file
    out_csv = define_proof_name(poses[0], game, team) + '.csv'
    out_df = pd.DataFrame(columns=['take name', 'take', 'px take name', 'order'])

    for pose in poses:
        # Define replacement text for shot string
        shot_string = 'Px: ' + pose.split('/')[-1]

        # Copy Nuke template file to tmp directory with player and pose name
        nuke_template = '/Users/px/Projects/pxproofs/proof_comp_template.nk'
        render_filename = '/tmp/' + pose.split('/')[-1] + '.nk'
        if os.path.exists(render_filename):
            os.remove(render_filename)
        shutil.copy(nuke_template, render_filename)

        # Get placeholder string and put it into a CSV file
        pose_name = get_placeholder(pose, in_df)
        placeholder = pose_name + ' ' + pose.split('/')[-1].split('_')[-1]

        # Search and replace placeholder text in nuke template file
        placeholder_text = ('PATH_TO_PLAYERS_HEAD', 'PATH_TO_PLAYERS_PROOF', '##_##_####_########_########_####',
                            'SHOTINFORMATIONSTRING', 'PROOF_OUTPUT')
        replace_text = (pose, proof_output, placeholder, shot_string, pose.split('/')[-1])

        find_replace = dict(zip(placeholder_text, replace_text))
        with open(nuke_template, 'r') as tmp_file:
            with open(render_filename, 'w') as new_file:
                for line in tmp_file:
                    for key in find_replace:
                        if key in line:
                            line = line.replace(key, find_replace[key])
                    new_file.write(line)

        # Create command and submit it
        cmd = app + render_filename
        subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # -----------------------------------
        # CSV PART - should be somewhere else

        # Put more stuff into the CSV file
        tk_name = pose.split('/')[-1]
        tk = tk_name.split('_')[-1]
        out_df = out_df.append({'take name': pose_name, 'take': tk, 'px take name': tk_name}, ignore_index=True)

    # Write csv file
    with open(out_csv, 'w') as f:
        out_df.to_csv(f, index=False)


def create_pdf(game, team, player):
    """Create pdf for the proof

    Args:
        game: name of the game
        team: name of team
        player: Name of player

    Returns: None
    """
    print(Fore.YELLOW + 'Creating PDF...')

    # Define page title
    if len(player.split()) == 1:
        player_name = ' '.join(map(str, player.split('_')[::-1])).title()
    title = GlobalDirs.teams[team] + ' --- ' + player_name

    proof_input = os.path.realpath(GlobalDirs.projects + "/" + game + "/Sections/" + team + '/' + player)

    # Backward compatibility
    if os.path.isdir(proof_input + '/_acquisition/tiff'):
        poses = glob(proof_input + '/_acquisition/tiff/*' + player + '*')
    else:
        poses = glob(proof_input + '/_acquisition/*' + player + '*')

    # Move neutral into first place
    item = [x for x in poses if 'neutral' in x][0]
    idx = poses.index(item)
    poses.insert(0, poses.pop(idx))

    # Just in case - remove unwanted parts
    _ = [x for x in poses if 'Thumbs.db' in x]
    if len(_) > 0:
        poses.remove(_[0])

    # Create PDF
    pdf = FPDF('L', 'pt', (1080, 1920))
    pdf.set_margins(0, 0, 0)
    pdf.add_page()
    pdf.set_title(title)
    pdf.set_font('Arial', '', 64)
    pdf.cell(1200, 800, title, 0, 0, 'C')
    pdf.ln()
    for pose in poses:
        render_filename = '/tmp/' + pose.split('/')[-1] + '.jpg'
        pdf.image(render_filename)

    # Define output directory and name of PDF
    proof = define_proof_name(poses[0], game, team) + '.pdf'
    pdf.output(proof, 'F')


def cleanup(game, team, player):
    """Move jpeg images to _thumbs and removing all nuke files

    Args:
        game: Name of the game
        team: Name of the team
        player: Name of player

    Returns: None
    """

    # Get _thumbs directory and if it doesn't exists create
    thumb_dir = GlobalDirs.projects + "/" + game + "/Sections/" + team + '/' + player + '/_acquisition/_thumbs'
    if not os.path.exists(thumb_dir):
        os.mkdir(thumb_dir)

    # Copy neutral to proof directory and move the rest of the jpegs to _thumbs
    output_dir = os.path.realpath(GlobalDirs.projects + "/" + game + "/Source_Pixelgun/Proof Sheets/" + team)
    jpegs = glob('/tmp/*' + player + '*.jpg')
    for jpeg in jpegs:
        if "neutral" in jpeg:
            shutil.copyfile(jpeg, jpeg.replace('/tmp', output_dir))
        else:
            shutil.move(jpeg, jpeg.replace('/tmp', thumb_dir))

    # Remove all files
    temps = glob('/tmp/*' + player + '*')
    for temp in temps:
        os.remove(temp)


def each_player(path, game, team, player):
    """Iterate thur all or just the one player"""
    if len(player.split()) == 1:
        player_name = ' '.join(map(str, player.split('_')[::-1])).title()

    print(Fore.BLUE + "Player:\t\t{}".format(player_name))

    # put the next three steps into a PriorityQueue to make sure that moving the data
    # has finished first before we clean up the naming
    qi.put(1, create_proof(path, team, player))
    qi.put(2, create_pdf(game, team, player))
    qi.put(3, cleanup(game, team, player))

    while not qi.empty():
        qi.get()


@command()
@option('--game', '-g', default='2K_1018_NBA2K21', help='Game name', type=str, required=True)
@option('--team', '-t', help='Team name', type=str, required=True)
@option('--player', '-p', help='Player name or all', type=str, required=True)
def main(game, team, player):
    """
    Create a proof cheat of a given player using Nuke

    \b
    game:      Game name, i.e. 2K_1018_NBA2K21 [Default]
    team:      Team name, i.e. 'det' for the 'Detroit Pistons'
    player:    A players name, i.e. 'king_louis' or you can pass in 'all' to run thru all players
    """

    # Call function to clear screen
    clear_screen()

    # Check if given directory is valid, i.e.: /Pixelgun_Projects/2K_1018_NBA2K21/Sections/orl/birch_khem
    path = os.path.realpath(GlobalDirs.projects + "/" + game + "/Sections/" + team)
    if not os.path.isdir(path):
        print(Fore.RED + 'Error: Path is invalid!')
        sys.exit(1)

    print('\n')
    print(Fore.BLUE + "Project:\t{}".format(game))
    print(Fore.BLUE + "Team:\t\t{}".format(GlobalDirs.teams[team]))

    if player.lower() == 'all':
        players = glob(path + '/*')
        for counter, value in enumerate(players):
            player = value.split('/')[-1]
            qo.put(counter, each_player(path, game, team, player) )

        while not qo.empty():
            qo.get()
    else:
        each_player(path, game, team, player)

    print(Fore.GREEN + 'DONE')
    print('\n')

    # Stop using colorama to restore 'stdout' and 'stderr' to their original values.
    colorama.deinit()


if __name__ == '__main__':
    main()
