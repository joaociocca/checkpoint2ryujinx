# Import your Switch savegames to Ryujinx

I had too many games to import manually, so I decided to play a bit with my meager Python skills and ChatGPT.

No, it's not just "hey, gimme the code", it's been some 14 hours of questions, answers and debugging - probably would have been easier for a Python programmer, but I'm not that.

## How to uses

```shell
python checkpoint2ryujinx.py -c <checkpoint_path> -r <ryujinx_path>
```

Checkpoint path is where you copied your Switch's Checkpoint backup to.

Ryujinx path is the Ryujinx configuration path.

- Linux: $HOME/.config/Ryujinx
- Windows: %appdata%/Ryujinx (I think?)

## Features

The script will scan through Ryujinx's `/bis/system/save` and `/bis/user/save` folders to see if there's already that game's folder there, and if there's already the record for that game in the `/bis/system/save/8000000000000000/0/imkvdb.arc` file.

If the ARC file's missing (I manually removed mine a lot for testing while creating this script), the script will create a new ARC file, then it'll first populate it with SYSTEM stuff, and finally with USER stuff.

If the ARC file is present, the script will only check USER stuff. It'll go through the Checkpoint backup folders, grab the gameid and check if there's an entry for it on the ARC file. If there is, the script will copy the files from the Checkpoint backup to the corresponding folder. If there isn't, the script will add a new entry to the ARC file, create the correct folder, and copy the files there.

## todo
- test more games
- check file's timestamp and only update if newer
- add option to fetch stuff directly from Nintendo Switch via Checkpoint's FTP
