import asyncio
import os

import click

from salmon import config
from salmon.common import commandgroup
from salmon.common.figles import check_path_processed, promt_path_processed
from salmon.constants import SOURCES, TAG_ENCODINGS

import salmon.trackers

from salmon.tagger import (
    validate_encoding,
)

from salmon.uploader import upload

from salmon.uploader.preassumptions import print_preassumptions

loop = asyncio.get_event_loop()


@commandgroup.command()
@click.argument(
    "path", type=click.Path(exists=True, file_okay=False, resolve_path=True)
)
@click.option("--group-id", "-g", default=None, help="Group ID to upload torrent to")
@click.option(
    "--lossy/--not-lossy",
    "-l/-L",
    default=None,
    help="Whether or not the files are lossy mastered",
)
@click.option(
    "--spectrals",
    "-sp",
    type=click.INT,
    multiple=True,
    help="Track numbers of spectrals to include in torrent description",
)
@click.option(
    "--overwrite",
    "-ow",
    is_flag=True,
    help="Whether or not to use the original metadata.",
)
@click.option(
    "--encoding",
    "-e",
    type=click.STRING,
    callback=validate_encoding,
    help="You must specify one of the following encodings if files aren't lossless: "
    + ", ".join(list(TAG_ENCODINGS.keys())),
)
@click.option(
    "--compress",
    "-c",
    is_flag=True,
    help="Recompress flacs to the configured compression level before uploading.",
)
@click.option(
    "--tracker",
    "-t",
    callback=salmon.trackers.validate_tracker,
    help=f'Uploading Choices: ({"/".join(salmon.trackers.tracker_list)})',
)
@click.option("--request", "-r", default=None, help='Pass a request URL or ID')
@click.option(
    "--spectrals-after",
    "-a",
    is_flag=True,
    help='Assess / upload / report spectrals after torrent upload',
)
@click.option(
    "--auto-rename",
    "-n",
    is_flag=True,
    help=f'Rename files and folders automatically',
)
@click.option(
    "--skip-up",
    is_flag=True,
    help=f'Skip check for 24 bit upconversion',
)
@click.option(
    "--scene",
    is_flag=True,
    help=f'Is this a scene release (default: False)'
)
@click.option(
    "--rutorrent",
    is_flag=True,
    help=f'Adds torrent to Rutorrent tracker after torrent upload (default: False)'
)
@click.option("--source-url", "-su", 
    default=None, 
    help=f'For WEB uploads provide the source of the album to be added in release description'
)
@click.option(
    "-yyy",
    is_flag=True,
    help=f'Automatically pick the default answer for prompt'
)
def batchup(
    path,
    group_id,
    lossy,
    spectrals,
    overwrite,
    encoding,
    compress,
    tracker,
    request,
    spectrals_after,
    auto_rename,
    skip_up,
    scene,
    rutorrent,
    source_url,
    yyy
):
    """Command scan folder and find uploadable subfolders based on their content."""

    if yyy:
        config.YES_ALL = True

    gazelle_site = salmon.trackers.get_class(tracker)()
    
    for folder in find_uploadable_folder(path, tracker):
        
        folder = os.path.abspath(folder)

        try: 
            upload_folder(
                folder,
                group_id,
                lossy,
                spectrals,
                overwrite,
                encoding,
                compress,
                gazelle_site,
                request,
                spectrals_after,
                auto_rename,
                skip_up,
                scene,
                rutorrent,
                source_url,
            )
        except click.Abort:
            promt_path_processed(folder, tracker)
        
        click.confirm(
            click.style(
                '\nDo you want to find the next item to upload?',
                fg="magenta",
                bold=True,
            ), abort=True,
            default=True
        )

        
    click.secho("\nNo more folders left!", fg="green")
    

def upload_folder(
    path,
    group_id,
    lossy,
    spectrals,
    overwrite,
    encoding,
    compress,
    gazelle_site,
    request,
    spectrals_after,
    auto_rename,
    skip_up,
    scene,
    rutorrent,
    source_url,
):
    """Upload a folder. Starts by showing the content and let the user chose the source"""
    source = choose_source(SOURCES.values(), path)
    print_preassumptions(
        gazelle_site,
        path,
        group_id,
        source,
        lossy,
        spectrals,
        encoding,
        spectrals_after,
    )
    if source_url:
        source_url = source_url.strip()
    upload(
        gazelle_site,
        path,
        group_id,
        source,
        lossy,
        spectrals,
        encoding,
        source_url=source_url,
        scene=scene,
        rutorrent=rutorrent,
        overwrite_meta=overwrite,
        recompress=compress,
        request_id=request,
        spectrals_after=spectrals_after,
        auto_rename=auto_rename,
        skip_up=skip_up,
    )

def find_uploadable_folder(path, tracker_name):
    """
    A generator function similar to os.walk, but it does not scan subdirectories.
    """

    with os.scandir(path) as it:
        files = []
        dirs = []

        if check_path_processed(path, tracker_name):
            return

        for entry in it:
            if entry.is_dir():
                  dirs.append(entry.path)
            elif entry.is_file():
                files.append(entry.name)

        dirs.sort()

        for dir in dirs:
            yield from find_uploadable_folder(dir, tracker_name)

        if not has_audio_files(files):
            return

        yield path
        
def has_audio_files(files):
    """
    Checks if list of files contains an audio file
    """
    for file in files:
        if os.path.splitext(file.lower())[1] in {".flac", ".mp3", ".m4a"}:
            return True
    
    return False

def list_folder_content(path):
    """
    Prints the files and subfolders found within a path.
    """
    with os.scandir(path) as it:
        files = []
        dirs = []

        for entry in it:
            if entry.is_dir():
                dirs.append(entry.name)    
            elif entry.is_file():
                files.append(entry.name)
        files.sort()
        dirs.sort()

        if len(files) > 0:
            click.secho("\nThe following files where found in the folder:", fg="yellow")
            for file in files:
                click.secho(f"  {file}")

        if len(dirs) > 0:
            click.secho("\nThe following sub-folders where found in the folder:", fg="yellow")
            for dir in dirs:
                click.secho(f"  {dir}")

def choose_source(choices, path):
    """Allows the user to choose a tracker from choices."""
    while True:
        click.secho("Currently selected folder:", fg="yellow")
        click.secho(f"  {path}")

        list_folder_content(path)

        # Loop until we have chosen a tracker or aborted.
        source_input = click.prompt(
            click.style(
                f'\nYour choices are {" , ".join(choices)} ' 'or [a]bort.',
                fg="magenta",
                bold=True,
            ),
        )
        source_input = source_input.strip().upper()
        if source_input in choices:
            click.secho(f"\nUsing source: {source_input}", fg="green")
            return source_input
        # this part allows input of the first letter of the tracker.
        elif source_input in [choice[0] for choice in choices]:
            for choice in choices:
                if source_input == choice[0]:
                    click.secho(f"\nUsing source: {choice}", fg="green")
                    return choice
        elif source_input.lower().startswith("a"):
            click.secho("\nAborting", fg="green")
            raise click.Abort