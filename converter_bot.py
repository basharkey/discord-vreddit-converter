#!/usr/bin/env python3
from requests_html import HTMLSession
from dotenv import load_dotenv
import sys
import requests
import re
import os
import subprocess
import discord

def parse_video_url(vreddit_url):
    if 'https://old.reddit.com/r/' in vreddit_url:
        vreddit_url = vreddit_url.replace('https://old.', 'https://www.')

    # get reddit video id from reddit post
    sess = HTMLSession()
    vreddit_url = re.search(r'(https?://[^\s]+)', vreddit_url).group(1)
    print(f"Reddit URL: {vreddit_url}")
    resp = sess.get(vreddit_url)

    try:
        flair = resp.html.search('"flair":[{"text":"{}"')[0]
        if flair.lower() == 'nsfw':
            is_nsfw = True
        else:
            is_nsfw = False
    except:
        is_nsfw = False

    try:
        vreddit_id = resp.html.search('"hlsUrl":"https://v.redd.it/{}/HLSPlaylist.m3u8')[0]
        print(f"vReddit ID: {vreddit_id}")
        return vreddit_id, is_nsfw
    except:
        return False, False


def compress_video(files, max_size):
        video_file = files[0]

        # get video duration sec
        duration = float(subprocess.check_output(['ffprobe', '-v', 'quiet', '-select_streams', 'v:0', '-show_entries', 'stream=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_file]).decode())

        # get video bitrate kb
        video_bitrate = float(subprocess.check_output(['ffprobe', '-v', 'quiet', '-select_streams', 'v:0', '-show_entries', 'stream=bit_rate', '-of', 'default=noprint_wrappers=1:nokey=1', video_file]).decode()) / 1024

        # determine target bitrate to achieve target size
        target_bitrate = (max_size * 1024 * 1024 * 8 / duration / 1024)
        comp_file = 'comp.mp4'
    
        try:
            audio_file = files[1]

            if comp_audio:
                # get audio bitrate kb
                audio_bitrate = float(subprocess.check_output(['ffprobe', '-v', 'quiet', '-select_streams', 'a:0', '-show_entries', 'stream=bit_rate', '-of', 'default=noprint_wrappers=1:nokey=1', audio_file]).decode()) / 1024
    
                comp_ratio = target_bitrate / (video_bitrate + audio_bitrate)
                target_audio_bitrate = audio_bitrate * comp_ratio
            else:
                audio_size = total_file_size([audio_file])
                target_video_bitrate = ((max_size - audio_size) * 1024 * 1024 * 8 / duration / 1024)

                subprocess.run(['ffmpeg', '-y', '-i', video_file, '-b:v', str(target_video_bitrate) + 'k', '-pass', '1', '-f', 'mp4', '/dev/null'])
                subprocess.run(['ffmpeg', '-y', '-i', video_file, '-i', audio_file, '-b:v', str(target_video_bitrate) + 'k', '-pass', '2', comp_file])

                return comp_file
        except:
            comp_ratio = target_bitrate / video_bitrate
    
        target_video_bitrate = video_bitrate * comp_ratio

        try:
            subprocess.run(['ffmpeg', '-y', '-i', video_file, '-i', audio_file, '-b:v', str(target_video_bitrate) + 'k', '-b:a', str(target_audio_bitrate) + 'k', '-pass', '1', '-f', 'mp4', '/dev/null'])
            subprocess.run(['ffmpeg', '-y', '-i', video_file, '-i', audio_file, '-b:v', str(target_video_bitrate) + 'k', '-b:a', str(target_audio_bitrate) + 'k', '-pass', '2', comp_file])
        except:
            subprocess.run(['ffmpeg', '-y', '-i', video_file, '-b:v', str(target_video_bitrate) + 'k', '-pass', '1', '-f', 'mp4', '/dev/null'])
            subprocess.run(['ffmpeg', '-y', '-i', video_file, '-b:v', str(target_video_bitrate) + 'k', '-pass', '2', comp_file])
    
        return comp_file


def total_file_size(files):
    total_size = 0
    for file in files:
        total_size += os.path.getsize(file) / (1024 * 1024)
    return total_size


def retrieve_video(vreddit_id, max_size):
    video_file = 'video.mp4'
    audio_file = 'audio.mp4'

    # get video and audio files
    supported_resolutions = ['1080', '720', '480', '360', '240']
    for resolution in supported_resolutions:
        print(f"Downloading @ {resolution}")
        r = requests.get('https://v.redd.it/' + vreddit_id + '/DASH_' + resolution + '.mp4')

        if 'Access Denied' in str(r.content):
            print(f"Video not available @ {resolution}")
            continue
        else:
            with open (video_file, 'wb') as f:
                f.write(r.content)
            break

    r = requests.get('https://v.redd.it/' + vreddit_id + '/DASH_audio.mp4')
    # some reddit videos dont contain audio, if audio doesnt exist post video only
    if 'Access Denied' in str(r.content):
        if total_file_size([video_file]) > max_size:
            out_file = compress_video([video_file], max_size)
        else:
            out_file = video_file
        return out_file 
    else:
        with open (audio_file, 'wb') as f:
            f.write(r.content)

        if total_file_size([video_file, audio_file]) > max_size:
            out_file = compress_video([video_file, audio_file], max_size)
        else:
            out_file = 'out.mp4'
            subprocess.run(['ffmpeg', '-y', '-i', video_file, '-i', audio_file, '-c', 'copy', out_file])
            
        return out_file 


load_dotenv()
token = os.getenv('token')
comp_audio = os.getenv('compress_audio')
if comp_audio == 'true':
    comp_audio = True
else:
    comp_audio = False
bot = discord.Client()

@bot.event
async def on_message(message):
    max_size = 8 # MB
    if 'https://www.reddit.com/r/' in message.content or 'https://old.reddit.com/r/' in message.content or 'https://v.redd.it/' in message.content:
        print("Reddit post detected")
        vreddit_id, is_nsfw = parse_video_url(message.content)
        print(f"NSFW: {is_nsfw}")

        if vreddit_id:
            msg = await message.channel.send(content='Converting...')
            out_file = retrieve_video(vreddit_id, max_size)
            await msg.delete() 
            if is_nsfw:
                os.rename(out_file, 'SPOILER_out.mp4')
                out_file = 'SPOILER_out.mp4'
                await message.channel.send(content='[NSFW]', file=discord.File(out_file))
            else:
                await message.channel.send(file=discord.File(out_file))
        else:
            print("Unable to find vReddit ID")
            return

bot.run(token)
