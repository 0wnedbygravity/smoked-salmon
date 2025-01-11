import os
import subprocess

import click

from salmon import config


def get_audio_files(path):
    """
    Iterate over a path and return all the files that match the allowed
    audio file extensions.
    """
    files = []
    for root, folders, files_ in os.walk(path):
        files += [
            create_relative_path(root, path, f)
            for f in files_
            if os.path.splitext(f.lower())[1] in {".flac", ".mp3", ".m4a"}
        ]
    return sorted(files)


def create_relative_path(root, path, filename):
    """
    Create a relative path to a filename. For example, given:
        root     = '/home/xxx/Tidal/Album/Disc 1'
        path     = '/home/xxx/Tidal/Album'
        filename = '01. Track.flac'
    'Disc 1/01. Track.flac' would be returned.
    """
    return os.path.join(
        root.split(path, 1)[1][1:], filename
    )  # [1:] to get rid of the slash.

def get_folder_name(path):
    """
    Extract the folder name from a given file path. For example, given:
        path     = '/home/xxx/Tidal/Album'
    'Album' would be returned.
    """
    # Get the directory portion of the path
    directory_path = os.path.dirname(path)
    # Get the base folder name from the directory path
    folder_name = os.path.basename(directory_path)
    return folder_name


def compress(filepath):
    """Re-compress a .flac file with the configured level."""
    with open(os.devnull, "w") as devnull:
        subprocess.call(
            [
                "flac",
                f"-{config.FLAC_COMPRESSION_LEVEL}",
                filepath,
                "-o",
                f"{filepath}.new",
                "--delete-input-file",
            ],
            stdout=devnull,
            stderr=devnull,
        )
    os.rename(f"{filepath}.new", filepath)


def alac_to_flac(filepath):
    """Convert alac to flac"""
    with open(os.devnull, "w") as devnull:
        subprocess.call(
            [
                "ffmpeg",
                # "-y",
                "-i",
                filepath,
                "-acodec",
                "flac",
                f"{filepath}.flac",
                # "--delete-input-file",
            ],
            stdout=devnull,
            stderr=devnull,
        )
    os.rename(f"{filepath}.flac", filepath)

def promt_path_processed(path, tracker_name):

    if check_path_processed(path, tracker_name):
        return
    
    if not click.confirm(
        click.style(
            f'\nDo you want to mark the folder as Processed for {tracker_name}?',
                fg="magenta",
                bold=True,
            ),
            default=True
        ):
        return

    mark_path_processed(path, tracker_name)

    return

def get_processed_filename(path, tracker_name):
    """
    Returns filename to mark path as processed.
    """
    return os.path.join(path, f".PROCESSED-{tracker_name.upper()}")

def check_path_processed(path, tracker_name):
    """
    Checks whenever a path contains a ".PROCESSED-TRACKER" file.
    """
    # Construct the tracker file path
    tracker_file_path = get_processed_filename(path, tracker_name)

    if os.path.exists(tracker_file_path):
        return True
    
    return False

def mark_path_processed(path, tracker_name):
    """
    Create a ".PROCESSED-TRACKER" file in the specified directory path.
    """  
    # Construct the tracker file path
    tracker_file_path = get_processed_filename(path, tracker_name)

    if check_path_processed(path, tracker_name):
        click.secho(f"\nTracker file already exists!", color="red")
        click.secho(f"  {tracker_name}")

    # Create the tracker file
    open(tracker_file_path, "a").close()
    
    click.secho(f"\nThe folder {os.path.basename(path)} has been marked as processed for {tracker_name}", color="green")
