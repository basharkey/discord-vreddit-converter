#!/usr/bin/env python3

from requests_html import HTMLSession
from dotenv import load_dotenv
import requests
import re
import os
import subprocess
import discord

def parse_video_url(vreddit_url):
    # get reddit video id from reddit post
    sess = HTMLSession()
    resp = sess.get(vreddit_url)
    resp = str(resp.html.find('source'))
    try:
        vreddit_id = re.search(r'https://v.redd.it/(.*?)/HLSPlaylist.m3u8', resp).group(1)
        return vreddit_id
    except:
        return False

def retrieve_video(vreddit_id):
    video_file = 'video.mp4'
    audio_file = 'audio.mp4'
    out_file = 'out.mp4'

    # get video and audio files
    r = requests.get('https://v.redd.it/' + vreddit_id + '/DASH_360.mp4')
    with open (video_file, 'wb') as f:
        f.write(r.content)

    r = requests.get('https://v.redd.it/' + vreddit_id + '/DASH_audio.mp4')
    # some reddit videos dont contain audio, if audio doesnt exist post video only
    if 'Access Denied' in str(r.content):
        return video_file

    with open (audio_file, 'wb') as f:
        f.write(r.content)

    # combine video and audio files
    subprocess.run(['ffmpeg', '-y', '-i', video_file, '-i', audio_file, out_file])
    return out_file

def compress_video(out_file):
        # get video duration
        duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration', '-of', 'default=noprint_wrappers=1:nokey=1', out_file]).decode())

        # get audio bitrate
        audio_bitrate = subprocess.check_output(['ffprobe', '-v', 'error', '-of', 'flat=s=_', '-select_streams', 'a:0', '-show_entries', 'stream=bit_rate', out_file]).decode()
        audio_bitrate = float(int(re.search(r'"(.*?)"', audio_bitrate).group(1)) / 1000)
        
        # determine target bitrate to achieve video size of 8 MB
        target_video_bitrate = (8 * 8192) / (1.048576 * duration) - audio_bitrate
        
        # rerender video to meet size requirements
        comp_file = 'comp.mp4'
        subprocess.run(['ffmpeg', '-y', '-i', out_file, '-c:v', 'libx264', '-b:v', str(target_video_bitrate) + 'k', '-pass', '1', '-an', '-f', 'mp4', '-'])
        subprocess.run(['ffmpeg', '-i', out_file, '-c:v', 'libx264', '-b:v', str(target_video_bitrate) + 'k', '-pass', '2', '-c:a', 'aac', '-b:a', str(audio_bitrate) + 'k', comp_file])
        os.rename(comp_file, out_file)

bot = discord.Client()

@bot.event
async def on_message(message):
    if 'https://www.reddit.com/r/' in message.content or 'https://old.reddit.com/r/' in message.content:
        print("reddit post")
        vreddit_id = parse_video_url(message.content)
        if vreddit_id:
            out_file = retrieve_video(vreddit_id)
            video_size = os.path.getsize(out_file)/(1024*1024)
            if video_size > 8: # Discords regular user upload limit
                compress_video(out_file)
            await message.channel.send(file=discord.File(out_file))
        else:
            print("not vreddit")
            return

load_dotenv()
token = os.getenv('token')
bot.run(token)
