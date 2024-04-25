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
    """ Extracts the game ID from the Checkpoint folder name. """
    try:
        game_id_hex = checkpoint_folder_name.split(' ')[0][2:]  # Typical format: "0x<game_id> <game_name>"
        formatted_game_id = f"{int(game_id_hex, 16):016x}"
        print(f"Extracted game ID {formatted_game_id} from folder name {checkpoint_folder_name}")
        return formatted_game_id
    except Exception as e:
        print(f"Error extracting game ID from {checkpoint_folder_name}: {e}")
    return None

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

def read_game_id_from_extradata0(extra_data0_path, expected_game_id):
    """ Reads the game ID from an ExtraData0 file and compares it with the expected ID. """
    try:
        with open(extra_data0_path, 'rb') as file:
            game_id_bytes = file.read(8)  # Read the first 8 bytes
            if game_id_bytes:
                game_id = struct.unpack('<Q', game_id_bytes)[0]
                formatted_game_id = f"{game_id:016x}"
                if formatted_game_id == expected_game_id:
                    print(f"Match found: Game ID {formatted_game_id} in {extra_data0_path}")
                # else:
                #     print(f"No match: Read {formatted_game_id}, expected {expected_game_id}")  # Debugging why no match
                return formatted_game_id
    except Exception as e:
        print(f"Error reading {extra_data0_path}: {e}")
    return None

def populate_system_folders(imkvdb_path, system_save_directory):
    entries = {}
    print(f"Scanning for system folders in: {system_save_directory}")
    try:
        folders = os.listdir(system_save_directory)
    except FileNotFoundError:
        print(f"Directory not found: {system_save_directory}")
        return

    for folder in folders:
        if len(folder) == 16:  # Assuming system save folders have 16 character names (hex)
            try:
                folder_id = int(folder, 16)
                # Use '<Q' for 64-bit unsigned long long
                key = (b'\x00' * 24) + struct.pack('<Q', folder_id) + (b'\x00' * 32)
                value = struct.pack('<Q', folder_id) + (b'\x00' * 56)
                entries[key] = value
                print(f"Adding system folder {folder} to imkvdb.arc: Key: {key.hex()}, Value: {value.hex()}")
            except ValueError:
                # Ignore folders with non-hexadecimal names
                continue
        else:
            print(f"Skipped folder {folder} due to incorrect name length")

    # Write entries to imkvdb.arc
    if entries:
        with open(imkvdb_path, 'wb') as file:
            file.write(b'IMKV' + b'\x00' * 4 + struct.pack('<I', len(entries)))
            for k, v in entries.items():
                file.write(b'IMEN' + struct.pack('<I', len(k)) + struct.pack('<I', len(v)) + k + v)
        print(f"imkvdb.arc created with {len(entries)} entries.")
    else:
        print("No valid system folders found to add to imkvdb.arc.")

def initialize_imkvdb(imkvdb_path, system_save_directory):
    """ Initialize a new IMKVDB file if it does not exist and populate it with system save folders. """
    if not os.path.exists(imkvdb_path):
        print(f"imkvdb.arc does not exist. Creating new file at {imkvdb_path}.")
        populate_system_folders(imkvdb_path, system_save_directory)
    else:
        print(f"imkvdb.arc already exists at {imkvdb_path}.")

def initialize_imkvdb(imkvdb_path, system_save_directory):
    """ Initialize a new IMKVDB file if it does not exist and populate it with system save folders. """
    if not os.path.exists(imkvdb_path):
        populate_system_folders(imkvdb_path, system_save_directory)
    else:
        # If the file already exists, simply check for consistency or update logic here if needed
        pass

def parse_imkvdb(file_path):
    """ Parse the existing IMKVDB file into a dictionary of keys and values. """
    entries = {}
    try:
        with open(file_path, 'rb') as file:
            header = file.read(12)  # Read the header which includes the magic 'IMKV', reserved and number of entries
            if header[:4] != b'IMKV':
                return entries  # Not a valid IMKVDB file
            num_entries = struct.unpack('<I', header[8:12])[0]
            for _ in range(num_entries):
                if file.read(4) != b'IMEN':
                    break  # Invalid entry header
                key_size = struct.unpack('<I', file.read(4))[0]
                value_size = struct.unpack('<I', file.read(4))[0]
                key = file.read(key_size)
                value = file.read(value_size)
                entries[key] = value
    except FileNotFoundError:
        pass  # File not found, return empty dict
    return entries

def update_imkvdb(file_path, game_id_hex, folder_id):
    entries = parse_imkvdb(file_path)

    # Normalize the game ID hex string to lower case
    game_id_hex = game_id_hex.lower()
    folder_id_bytes = struct.pack('<Q', folder_id)  # Folder ID in little-endian format

    if int(game_id_hex, 16) == 0:  # Assuming system entry logic needs no '1' in the key
        key = (b'\x00' * 24) + folder_id_bytes + (b'\x00' * 32)
        value = folder_id_bytes + (b'\x00' * 60) + b'\x01' + (b'\x00' * 3)
    else:  # Game entry
        game_id_bytes = bytes.fromhex(game_id_hex)
        game_id_little_endian = struct.pack('<Q', int(game_id_hex, 16))
        # Ensure the game ID is in little endian for the key
        key = game_id_little_endian + b'\x01' + (b'\x00' * 23) + b'\x01' + (b'\x00' * 31)
        value = folder_id_bytes + (b'\x00' * 16) + b'\x01' + (b'\x00' * 39)

    # Only update if key does not exist
    if key not in entries:
        entries[key] = value
        with open(file_path, 'wb') as file:
            file.write(b'IMKV' + b'\x00' * 4 + struct.pack('<I', len(entries)))  # Write header
            for k, v in entries.items():
                file.write(b'IMEN' + struct.pack('<I', len(k)) + struct.pack('<I', len(v)) + k + v)
        print(f"Updated imkvdb.arc with new entry for Game ID {game_id_hex} at folder index {folder_id}")
    else:
        print(f"Entry for Game ID {game_id_hex} already exists in imkvdb.arc, no update needed.")

def ensure_imkvdb_entry(game_id_hex, folder_id, imkvdb_path):
    """ Ensure the game ID to folder mapping exists in the IMKVDB file. """
    initialize_imkvdb(imkvdb_path)  # Ensure file exists and is initialized
    update_imkvdb(imkvdb_path, game_id_hex, folder_id)

def main(checkpoint_base_directory, ryujinx_base_directory):
    save_data_directory = os.path.join(ryujinx_base_directory, "bis/user/save")
    imkvdb_path = os.path.join(ryujinx_base_directory, "bis/system/save/8000000000000000/0/imkvdb.arc")

    for folder in os.listdir(checkpoint_base_directory):
        folder_path = os.path.join(checkpoint_base_directory, folder)
        if os.path.isdir(folder_path):
            game_id_hex = extract_game_id(folder)
            if game_id_hex:
                output_folder = None

                # Check existing Ryujinx folders for this game ID
                for save_folder in os.listdir(save_data_directory):
                    extra_data0_path = os.path.join(save_data_directory, save_folder, 'ExtraData0')
                    if os.path.exists(extra_data0_path):
                        existing_game_id = read_game_id_from_extradata0(extra_data0_path, game_id_hex)
                        if existing_game_id == game_id_hex:
                            output_folder = os.path.join(save_data_directory, save_folder)
                            break

                if not output_folder:
                    next_folder_id = get_next_ryujinx_folder(save_data_directory)
                    output_folder = os.path.join(save_data_directory, next_folder_id)
                    create_extradata0_file(game_id_hex, output_folder)

                final_destination = os.path.join(output_folder, '0')
                if not os.path.exists(final_destination):
                    os.makedirs(final_destination)

                latest_save_folder = get_latest_save_folder(folder_path)
                if latest_save_folder:
                    copy_save_files(latest_save_folder, final_destination)

                # Convert folder ID from hexadecimal string to integer
                folder_id = int(os.path.basename(output_folder), 16)
                update_imkvdb(imkvdb_path, game_id_hex, folder_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import save games to Ryujinx")
    parser.add_argument('-c', '--checkpoint', required=True, help='Path to the Checkpoint base directory')
    parser.add_argument('-r', '--ryujinx', required=True, help='Path to the Ryujinx base directory')
    args = parser.parse_args()

    system_save_directory = os.path.join(args.ryujinx, "bis/system/save")
    imkvdb_path = os.path.join(args.ryujinx, "bis/system/save/8000000000000000/0/imkvdb.arc")

    initialize_imkvdb(imkvdb_path, system_save_directory)
    main(args.checkpoint, args.ryujinx)
