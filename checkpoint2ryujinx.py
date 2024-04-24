#!/usr/bin/env python3

import os
import struct
import shutil
import argparse


def get_next_ryujinx_folder(base_directory):
    """
    Determines the next available folder name in the Ryujinx directory based on existing folders.
    Folder names are expected to be hexadecimal numbers.
    """
    existing_folders = [folder for folder in os.listdir(base_directory) if os.path.isdir(os.path.join(base_directory, folder))]
    if not existing_folders:
        return "0000000000000001"  # Start with this if no folders exist
    max_folder = max(int(folder, 16) for folder in existing_folders)
    next_folder = format(max_folder + 1, '016x')
    return next_folder

def extract_game_id(checkpoint_folder_name):
    """
    Extracts the game ID from the Checkpoint folder name.
    Expected format: '0x<game id> <game name>'
    """
    game_id_hex = checkpoint_folder_name.split(' ')[0][2:]
    return game_id_hex

def create_extradata0_file(game_id_hex, output_folder, user_id_hex="00000000000000010000000000000000", flags=b'\x00\x00\x00\x00', journal_size=b'\x10\x00\x00\x00', commit_id=b'\x00\x00\x00\x00\x00\x00\x00\x00'):
    """
    Creates or updates the ExtraData0 file using the standard User ID from Ryujinx settings.
    """
    game_id_bytes = bytes.fromhex(game_id_hex)
    user_id_bytes = bytes.fromhex(user_id_hex)
    game_id_little_endian = struct.pack('<Q', int.from_bytes(game_id_bytes, 'big'))
    template = bytearray(512)
    template[0:8] = game_id_little_endian
    template[8:24] = user_id_bytes
    template[64:72] = game_id_little_endian
    template[80:84] = flags
    template[96:104] = journal_size
    template[104:112] = commit_id
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    with open(os.path.join(output_folder, "ExtraData0"), 'wb') as f:
        f.write(template)

def get_latest_save_folder(checkpoint_game_folder):
    backup_folders = [os.path.join(checkpoint_game_folder, folder) for folder in os.listdir(checkpoint_game_folder) if os.path.isdir(os.path.join(checkpoint_game_folder, folder))]
    return max(backup_folders, key=os.path.getmtime, default=None)

def copy_save_files(source_folder, destination_folder):
    """
    Copies all files and directories from the source folder to the destination folder.
    """
    for item in os.listdir(source_folder):
        src_path = os.path.join(source_folder, item)
        dst_path = os.path.join(destination_folder, item)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dst_path)

def read_game_id_from_extradata0(extra_data0_path):
    if not os.path.exists(extra_data0_path):
        return None
    with open(extra_data0_path, 'rb') as file:
        game_id_bytes = file.read(8)
        if game_id_bytes:
            game_id = struct.unpack('<Q', game_id_bytes)[0]
            return f"{game_id:016x}"
    return None

def main(checkpoint_base_directory, ryujinx_base_directory):
    for folder in os.listdir(checkpoint_base_directory):
        folder_path = os.path.join(checkpoint_base_directory, folder)
        if os.path.isdir(folder_path):
            game_id_hex = extract_game_id(folder)
            if game_id_hex:
                output_folder = None
                for save_folder in os.listdir(ryujinx_base_directory):
                    extra_data0_path = os.path.join(ryujinx_base_directory, save_folder, 'ExtraData0')
                    if os.path.exists(extra_data0_path):
                        if read_game_id_from_extradata0(extra_data0_path) == game_id_hex:
                            output_folder = os.path.join(ryujinx_base_directory, save_folder)
                            break
                if not output_folder:
                    output_folder = os.path.join(ryujinx_base_directory, get_next_ryujinx_folder(ryujinx_base_directory))
                    create_extradata0_file(game_id_hex, output_folder)

                final_destination = os.path.join(output_folder, '0')
                if not os.path.exists(final_destination):
                    os.makedirs(final_destination)
                latest_save_folder = get_latest_save_folder(folder_path)
                if latest_save_folder:
                    copy_save_files(latest_save_folder, final_destination)
                    print(f"Processed {folder} into Ryujinx folder {final_destination}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import save games to Ryujinx")
    parser.add_argument('-c', '--checkpoint', required=True, help='Path to the Checkpoint base directory')
    parser.add_argument('-r', '--ryujinx', required=True, help='Path to the Ryujinx base directory')
    args = parser.parse_args()
    main(args.checkpoint, args.ryujinx)
