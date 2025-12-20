import os
import sys
import logging
import subprocess


def verify_cmd(path: str) -> bool:
    """Verify if the file provided at path is valid and exists, otherwise log error and exit."""
    if not os.path.exists(path):
        logging.error(f"File does not exist: {path}")
        sys.exit(1)
    if not os.path.isfile(path):
        logging.error(f"Path is not a file: {path}")
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
    print(f"✅ Merged segments into {output_file}")


def decrypt(input_file, init_path, output_file, key):
    """Decrypt a media file using mp4ff-decrypt.

    Args:
        input_file: Path to the input encrypted file.
        init_path: Path to the initialization file.
        output_file: Path to the output decrypted file.
        key: The decryption key in KID:KEY format.

    Returns:
        True if decryption succeeded, False otherwise.
    """
    key = key.split(":")[1]
    result = subprocess.run(
        ['mp4ff-decrypt', '-init', init_path, '-key', key, input_file, output_file],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"✅ Decrypted {input_file} to {output_file}")
        return True
    else:
        print(f"❌ Decryption failed: {result.stderr}")
        return False