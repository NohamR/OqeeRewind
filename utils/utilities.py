"""Utility functions for OqeeRewind, including verification, merging, and decryption."""

import os
import sys
import subprocess
import shutil
from utils.logging_config import logger


def verify_mp4ff():
    """Verify if mp4ff-decrypt is installed and available in PATH."""
    if shutil.which("mp4ff-decrypt") is None:
        logger.error("mp4ff-decrypt is not installed or not in PATH.")
        logger.info("Please install it using:")
        logger.info("go install github.com/Eyevinn/mp4ff/cmd/mp4ff-decrypt@latest")
        sys.exit(1)
    return True


def verify_cmd(path: str) -> bool:
    """Verify if the file provided at path is valid and exists, otherwise log error and exit."""
    if not os.path.exists(path):
        logger.error("File does not exist: %s", path)
        sys.exit(1)
    if not os.path.isfile(path):
        logger.error("Path is not a file: %s", path)
        sys.exit(1)
    return True


def merge_segments(input_folder: str, track_id: str, output_file: str):
    """Merge downloaded segments into a single file using ffmpeg."""
    segment_folder = os.path.join(input_folder, f"segments_{track_id}")

    segment_files = sorted(
        [f for f in os.listdir(segment_folder) if f.endswith(".m4s")],
        key=lambda x: int(x.split(".")[0]),
    )
    with open(output_file, "wb") as outfile:
        for fname in segment_files:
            with open(f"{segment_folder}/{fname}", "rb") as infile:
                outfile.write(infile.read())
    logger.info("Merged segments into %s", output_file)


def decrypt(segment_dir, init_path, output_file, key):
    """Decrypt segments in chunks of ~1GB to avoid loading entire file in memory.

    Args:
        segment_dir: Path to the directory containing .m4s segment files.
        init_path: Path to the initialization file.
        output_file: Path to the output decrypted file.
        key: The decryption key in KID:KEY format.

    Returns:
        True if decryption succeeded, False otherwise.
    """
    key = key.split(":")[1]

    segment_files = sorted(
        [f for f in os.listdir(segment_dir) if f.endswith(".m4s")],
        key=lambda x: int(x.split(".")[0]),
    )

    if not segment_files:
        logger.error("No segment files found in %s", segment_dir)
        return False

    logger.info(
        "Decrypting %d segments from %s to %s",
        len(segment_files),
        segment_dir,
        output_file,
    )

    chunk_num = 0
    temp_files = []
    TARGET_SIZE = 1 * 1024 * 1024 * 1024 # 1GB

    i = 0
    while i < len(segment_files):
        chunk_files = []
        chunk_size = 0

        while i < len(segment_files) and chunk_size < TARGET_SIZE:
            fname = segment_files[i]
            fpath = os.path.join(segment_dir, fname)
            fsize = os.path.getsize(fpath)
            chunk_files.append(fname)
            chunk_size += fsize
            i += 1

        logger.debug(
            "Processing chunk %d: %d segments, %.2f MB",
            chunk_num,
            len(chunk_files),
            chunk_size / (1024 * 1024),
        )

        chunk_merged = os.path.join(segment_dir, f"chunk_{chunk_num}_merged")
        chunk_dec = os.path.join(segment_dir, f"chunk_{chunk_num}_dec")
        temp_files.extend([chunk_merged, chunk_dec])

        with open(chunk_merged, "wb") as outfile:
            for fname in chunk_files:
                with open(os.path.join(segment_dir, fname), "rb") as infile:
                    outfile.write(infile.read())

        logger.debug("Decrypting chunk %d", chunk_num)
        result = subprocess.run(
            [
                "mp4ff-decrypt",
                "-init",
                init_path,
                "-key",
                key,
                chunk_merged,
                chunk_dec,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error("Decryption failed for chunk %d: %s", chunk_num, result.stderr)
            for tf in temp_files:
                if os.path.exists(tf):
                    os.remove(tf)
            return False

        chunk_num += 1

    logger.debug("Concatenating %d decrypted chunks into %s", chunk_num, output_file)
    with open(output_file, "wb") as outfile:
        for c in range(chunk_num):
            chunk_dec = os.path.join(segment_dir, f"chunk_{c}_dec")
            with open(chunk_dec, "rb") as infile:
                outfile.write(infile.read())

    for tf in temp_files:
        if os.path.exists(tf):
            os.remove(tf)

    logger.info("Successfully decrypted to %s", output_file)
    return True
