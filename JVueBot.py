import asyncio
import base64
import json
from urllib.parse import quote
import discord
from discord.ui import Select, View
from discord import app_commands
from discord.ext import commands
# from config import TOKEN
import requests
import config

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


def search_movie_by_name(movie_name):
    # Radarr API endpoint for movie search
    search_endpoint = f"{config.RADARR_URL}/api/v3/movie/lookup"

    # Parameters for the search query
    params = {
        'apikey': config.RADARR_API_KEY,
        'term': movie_name
    }

    try:
        # Make a GET request to Radarr API
        response = requests.get(search_endpoint, params=params)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            results = response.json()

            # Return the search results
            return results
        else:
            # Print an error message if the request was not successful
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def search_tv_show_by_name(tv_show_name):
    # Sonarr API endpoint for tv show search
    search_endpoint = f"{config.SONARR_URL}/api/v3/series/lookup"

    # Parameters for the search query
    params = {
        'apikey': config.SONARR_API_KEY,
        'term': tv_show_name
    }
    try:
        # Make a GET request to Sonarr API
        response = requests.get(search_endpoint, params=params)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            results = response.json()
            # Return the search results
            return results
        else:
            # Print an error message if the request was not successful
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def get_formatted_movie_title(movie):
    # This function is returning a nicely formatted movie title: Movie Title (2001)
    releaseDate = movie["year"]
    movieTitle = movie["title"]
    if releaseDate is not None:
        movieTitle = movie["title"] + releaseDate
        return movieTitle
    return movieTitle


def send_refresh_to_autoscan(folderName):
    # as named this function is sending a refresh command to autoscan for a given folderName.
    url = config.AUTOSCAN_URL
    credentials = f"{config.AUTOSCAN_USERNAME}:{config.AUTOSCAN_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    headers = {
        'Authorization': 'Basic ' + encoded_credentials
    }
    safeFolderName = quote(folderName)
    params = {
        'dir': folderName
    }
    response = requests.post(url, headers=headers, params=params)
    return response


@bot.event
async def on_ready():
    print(f'Bot is up and ready')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(e)


@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f'Hey {interaction.user.mention}! You can do it!!', ephemeral=True)


@bot.tree.command(name="say")
@app_commands.describe(thing_to_say="What should I say?")
async def say(interaction: discord.Interaction, thing_to_say: str):
    await interaction.response.send_message(f'{interaction.user.name} said: `{thing_to_say}`')


@bot.tree.command(name="streams")
async def streams(interaction: discord.Interaction):
    await interaction.response.defer()
    payload = {}
    response1 = requests.request("GET", config.JELLYBELLY_SESSIONS_URL, headers=config.JELLYBELLY_SESSIONS_HEADERS,
                                 data=payload)
    sessionCount = 0
    streamCount = 0
    transcodeCount = 0
    directPlayCount = 0
    somethingElseCount = 0
    pausedCount = 0
    for session in response1.json():
        sessionCount += 1
        # checking to see that the session has a NowPlayingItem which indicates the rest of the things we care about will be present.
        if session["PlayState"] and (session.get("NowPlayingItem") is not None):
            pausedBool = bool(session["PlayState"]["IsPaused"])
            if pausedBool:
                if session["PlayState"]["PlayMethod"] == "Transcode":
                    transcodeCount += 1
                elif session["PlayState"]["PlayMethod"] == "DirectPlay":
                    directPlayCount += 1
                else:
                    somethingElseCount += 1
                pausedCount += 1
            else:
                if session["PlayState"]["PlayMethod"] == "Transcode":
                    transcodeCount += 1
                elif session["PlayState"]["PlayMethod"] == "DirectPlay":
                    directPlayCount += 1
                else:
                    somethingElseCount += 1
            streamCount += 1
    await asyncio.sleep(2)
    await interaction.followup.send(f'There are **{str(streamCount)}** streams. \n**{str(pausedCount)}** of them are paused. \n**{str(directPlayCount)}** are direct plays. \n**{str(transcodeCount)}** require transcoding.')
    # no longer trying to respond immediately, using .followup instead.
    # await interaction.response.send_message(f'There are **{str(streamCount)}** streams. \n**{str(pausedCount)}** of them are paused. \n**{str(directPlayCount)}** are direct plays. \n**{str(transcodeCount)}** require transcoding.')


@bot.tree.command(name="detailedstreams")
async def detailedstreams(interaction: discord.Interaction):
    await interaction.response.defer()
    payload = {}
    response1 = requests.request("GET", config.JELLYBELLY_SESSIONS_URL, headers=config.JELLYBELLY_SESSIONS_HEADERS,
                                 data=payload)
    sessionCount = 0
    streamCount = 0
    transcodeCount = 0
    directPlayCount = 0
    somethingElseCount = 0
    pausedCount = 0
    totalBitrate = 0
    if response1.json() != {}:
        embed = discord.Embed(title=f"**Current Streams**", color=discord.Color.blurple())
        for session in response1.json():
            if session["PlayState"] and (session.get("NowPlayingItem") is not None):
                pausedBool = bool(session["PlayState"]["IsPaused"])
                # if the playback session is paused
                if pausedBool:
                    # if a tv episode
                    if session["NowPlayingItem"]["Type"] == "Episode":
                        # if it is being transcoded
                        if session["PlayState"]["PlayMethod"] == "Transcode":
                            npDict = session.get("NowPlayingItem")
                            # if it has an episode number
                            if npDict.get("IndexNumber") is not None:
                                # if it actually has transcode info.
                                if session.get("TranscodingInfo") is not None:
                                    embed.add_field(
                                        name=f'⏸️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E{session["NowPlayingItem"]["IndexNumber"]} - {session["NowPlayingItem"]["Name"]}',
                                        value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - {round(int(session["TranscodingInfo"]["Bitrate"]) / 1024000, 2)}mbps',
                                        inline=False
                                        )
                                    totalBitrate += int(session["TranscodingInfo"]["Bitrate"])
                                else:
                                    embed.add_field(
                                        name=f'⏸️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E{session["NowPlayingItem"]["IndexNumber"]} - {session["NowPlayingItem"]["Name"]}',
                                        value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - ???mbps',
                                        inline=False
                                    )
                            else:
                                if session.get("TranscodingInfo") is not None:
                                    embed.add_field(
                                        name=f'⏸️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E{session["NowPlayingItem"]["IndexNumber"]} - {session["NowPlayingItem"]["Name"]}',
                                        value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - {round(int(session["TranscodingInfo"]["Bitrate"]) / 1024000, 2)}mbps',
                                        inline=False
                                    )
                                    totalBitrate += int(session["TranscodingInfo"]["Bitrate"])
                                else:
                                    embed.add_field(
                                        name=f'⏸️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E{session["NowPlayingItem"]["IndexNumber"]} - {session["NowPlayingItem"]["Name"]}',
                                        value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - ???mbps',
                                        inline=False
                                    )
                            # totalBitrate += int(session["TranscodingInfo"]["Bitrate"])
                            transcodeCount += 1
                        # else if it is being directly played
                        elif session["PlayState"]["PlayMethod"] == "DirectPlay":
                            for mediastreams in session["NowPlayingItem"]["MediaStreams"]:
                                if mediastreams["Type"] == "Video":
                                    npDict = session.get("NowPlayingItem")
                                    if npDict.get("IndexNumber") is not None:
                                        embed.add_field(
                                            name=f'⏸️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E{session["NowPlayingItem"]["IndexNumber"]} - {session["NowPlayingItem"]["Name"]}',
                                            value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ DirectPlay - {round(int(mediastreams["BitRate"]) / 1024000, 2)}mbps',
                                            inline=False
                                        )
                                    else:
                                        embed.add_field(
                                            name=f'⏸️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}Exx - {session["NowPlayingItem"]["Name"]}',
                                            value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ DirectPlay - {round(int(mediastreams["BitRate"]) / 1024000, 2)}mbps',
                                            inline=False
                                        )
                                    totalBitrate += int(mediastreams["BitRate"])
                            directPlayCount += 1
                        else:
                            somethingElseCount += 1
                    # else if it is a movie being played
                    elif session["NowPlayingItem"]["Type"] == "Movie":
                        # if that movie is being transcoded
                        if session["PlayState"]["PlayMethod"] == "Transcode":
                            embed.add_field(
                                name=f'⏸️ {str(streamCount + 1)}: {session["NowPlayingItem"]["Name"]} ({session["NowPlayingItem"]["ProductionYear"]})',
                                value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - {round(int(session["TranscodingInfo"]["Bitrate"]) / 1024000, 2)}mbps',
                                inline=False
                                )
                            totalBitrate += int(session["TranscodingInfo"]["Bitrate"])
                            transcodeCount += 1
                        # if that movie is directly playing
                        elif session["PlayState"]["PlayMethod"] == "DirectPlay":
                            for mediastreams in session["NowPlayingItem"]["MediaStreams"]:
                                if mediastreams["Type"] == "Video":
                                    embed.add_field(
                                        name=f'⏸️ {str(streamCount + 1)}: {session["NowPlayingItem"]["Name"]} ({session["NowPlayingItem"]["ProductionYear"]})',
                                        value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ DirectPlay - {round(int(mediastreams["BitRate"]) / 1024000, 2)}mbps',
                                        inline=False
                                    )
                                    totalBitrate += int(mediastreams["BitRate"])
                            directPlayCount += 1
                        else:
                            somethingElseCount += 1
                    # else if it is a live TV channel being played
                    elif session["NowPlayingItem"]["Type"] == "TvChannel":
                        # if that live tv channel playback is being transcoded
                        if session["PlayState"]["PlayMethod"] == "Transcode":
                            embed.add_field(
                                name=f'⏸️ {str(streamCount + 1)}: 📡Channel {session["NowPlayingItem"]["ChannelNumber"]} - {session["NowPlayingItem"]["CurrentProgram"]["Name"]}',
                                value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - {round(int(session["TranscodingInfo"]["Bitrate"]) / 1024000, 2)}mbps',
                                inline=False
                            )
                            totalBitrate += int(session["TranscodingInfo"]["Bitrate"])
                            transcodeCount += 1
                        # if that live tv channel is being played directly
                        elif session["PlayState"]["PlayMethod"] == "DirectPlay":
                            # will have to see if this works. might have to not check for media streams.
                            for mediastreams in session["NowPlayingItem"]["MediaStreams"]:
                                if mediastreams["Type"] == "Video":
                                    embed.add_field(
                                        name=f'⏸️️ {str(streamCount + 1)}: 📡Channel {session["NowPlayingItem"]["ChannelNumber"]} - {session["NowPlayingItem"]["CurrentProgram"]["Name"]}',
                                        value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ DirectPlay - {round(int(mediastreams["BitRate"]) / 1024000, 2)}mbps',
                                        inline=False
                                    )
                                    totalBitrate += int(mediastreams["BitRate"])
                            directPlayCount += 1
                        else:
                            somethingElseCount += 1

                    pausedCount += 1
                # else if it is not a paused session.
                else:
                    # if playback session is a TV episde
                    if session["NowPlayingItem"]["Type"] == "Episode":
                        # if that episode playback is being transcoded
                        if session["PlayState"]["PlayMethod"] == "Transcode":
                            # if there is actually info about that transcode
                            if session.get("TranscodingInfo") is not None:
                                embed.add_field(
                                    name=f'▶️️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E{session["NowPlayingItem"]["IndexNumber"]} - {session["NowPlayingItem"]["Name"]}',
                                    value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - {round(int(session["TranscodingInfo"]["Bitrate"]) / 1024000, 2)}mbps',
                                    inline=False
                                )
                                totalBitrate += int(session["TranscodingInfo"]["Bitrate"])
                            else:
                                embed.add_field(
                                    name=f'▶️️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E{session["NowPlayingItem"]["IndexNumber"]} - {session["NowPlayingItem"]["Name"]}',
                                    value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - ???mbps',
                                    inline=False
                                )
                                totalBitrate += int(0)
                            transcodeCount += 1
                        # if the tv episode is being played directly
                        elif session["PlayState"]["PlayMethod"] == "DirectPlay":
                            for mediastreams in session["NowPlayingItem"]["MediaStreams"]:
                                if mediastreams["Type"] == "Video":
                                    npi = session["NowPlayingItem"]
                                    if npi.get("IndexNumber") is not None:
                                        embed.add_field(
                                            name=f'▶️️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E{session["NowPlayingItem"]["IndexNumber"]} - {session["NowPlayingItem"]["Name"]}',
                                            value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ DirectPlay - {round(int(mediastreams["BitRate"]) / 1024000, 2)}mbps',
                                            inline=False
                                        )
                                    else:
                                        embed.add_field(
                                            name=f'▶️️ {str(streamCount + 1)}: {session["NowPlayingItem"]["SeriesName"]} - S{session["NowPlayingItem"]["ParentIndexNumber"]}E?? - {session["NowPlayingItem"]["Name"]}',
                                            value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ DirectPlay - {round(int(mediastreams["BitRate"]) / 1024000, 2)}mbps',
                                            inline=False
                                        )
                                    totalBitrate += int(mediastreams["BitRate"])
                            directPlayCount += 1
                        else:
                            somethingElseCount += 1
                    # else if that playback session is for a Movie
                    elif session["NowPlayingItem"]["Type"] == "Movie":
                        # if that movie is being transcoded
                        if session["PlayState"]["PlayMethod"] == "Transcode":
                            embed.add_field(
                                name=f'▶️️ {str(streamCount + 1)}: {session["NowPlayingItem"]["Name"]} ({session["NowPlayingItem"]["ProductionYear"]})',
                                value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - {round(int(session["TranscodingInfo"]["Bitrate"]) / 1024000, 2)}mbps',
                                inline=False
                            )
                            totalBitrate += int(session["TranscodingInfo"]["Bitrate"])
                            transcodeCount += 1
                        # else if that movie is being played directly
                        elif session["PlayState"]["PlayMethod"] == "DirectPlay":
                            for mediastreams in session["NowPlayingItem"]["MediaStreams"]:
                                if mediastreams["Type"] == "Video":
                                    embed.add_field(
                                        name=f'▶️️ {str(streamCount + 1)}: {session["NowPlayingItem"]["Name"]} ({session["NowPlayingItem"]["ProductionYear"]})',
                                        value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ DirectPlay - {round(int(mediastreams["BitRate"]) / 1024000, 2)}mbps',
                                        inline=False
                                    )
                                    totalBitrate += int(mediastreams["BitRate"])
                            directPlayCount += 1
                        else:
                            somethingElseCount += 1
                    # else if that playback session is for live TV
                    elif session["NowPlayingItem"]["Type"] == "TvChannel":
                        # if that live tv channel is being transcoded.
                        if session["PlayState"]["PlayMethod"] == "Transcode":
                            embed.add_field(
                                name=f'▶️️ {str(streamCount + 1)}: 📡Channel {session["NowPlayingItem"]["ChannelNumber"]} - {session["NowPlayingItem"]["CurrentProgram"]["Name"]}',
                                value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ Transcode - {round(int(session["TranscodingInfo"]["Bitrate"]) / 1024000, 2)}mbps',
                                inline=False
                            )
                            totalBitrate += int(session["TranscodingInfo"]["Bitrate"])
                            transcodeCount += 1
                        # else if that live tv channel is being played back directly
                        elif session["PlayState"]["PlayMethod"] == "DirectPlay":
                            # will have to see if this works. might have to not check for media streams.
                            for mediastreams in session["NowPlayingItem"]["MediaStreams"]:
                                if mediastreams["Type"] == "Video":
                                    embed.add_field(
                                        name=f'▶️️ {str(streamCount + 1)}: 📡Channel {session["NowPlayingItem"]["ChannelNumber"]} - {session["NowPlayingItem"]["CurrentProgram"]["Name"]}',
                                        value=f'\n👤 {session["UserName"]}\n📺 {session["Client"]}-{session["DeviceName"]}\n⚙️ DirectPlay - {round(int(mediastreams["BitRate"]) / 1024000, 2)}mbps',
                                        inline=False
                                    )
                                    totalBitrate += int(mediastreams["BitRate"])
                            directPlayCount += 1
                        else:
                            somethingElseCount += 1
                streamCount += 1
            sessionCount += 1
        embed.set_footer(text=f"Stream Count: {str(streamCount)} - Bitrate: {round(totalBitrate / 1024000, 2)}mbps")
        await asyncio.sleep(5)
        await interaction.followup.send(embed=embed)
    else:
        # await interaction.response.send_message(f"Currently no streams")
        # await interaction.response.defer()
        await asyncio.sleep(5)
        await interaction.followup.send(f"Currently no streams")


@bot.tree.command(name="runpolicyupdate")
async def runpolicyupdate(interaction: discord.Interaction):
    response = requests.get(config.JELLYBELLY_USERS_URL, headers=config.JELLYBELLY_POLICY_HEADERS)
    users_data = response.json()
    usernames_to_exclude = config.JELLYBELLY_POLICY_EXCLUSIONS
    for user in users_data:
        if user["Name"] in usernames_to_exclude:
            continue
        user_id = user["Id"]
        user_endpoint = f"{config.JELLYBELLY_USERS_URL}/{user_id}/Policy"
        # these policy settings are subjective. Others may want to set different values or control more things.
        # payload = json.dumps({
        #     "EnableSharedDeviceControl": False,
        #     "EnableLiveTvManagement": False,
        #     "EnableLiveTvAccess": True,
        #     "LoginAttemptsBeforeLockout": 10,
        #     "AuthenticationProviderId": "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider",
        #     "PasswordResetProviderId": "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider"
        # })
        payload = json.dumps(config.JELLYBELLY_POLICY_VALUES)

        response = requests.request("POST", user_endpoint, headers=config.JELLYBELLY_POLICY_HEADERS, data=payload)
    await interaction.response.send_message(f'Ran policy update')


@bot.tree.command(name="refreshmovie")
@app_commands.describe(movie_name="Enter the movie name.")
async def refreshmovie(interaction: discord.Interaction, movie_name: str):
    await interaction.response.defer()
    lookupResults = search_movie_by_name(movie_name)
    embed = discord.Embed(title=f"**Refreshed Movie(s)**", color=discord.Color.blurple())
    for result in lookupResults:
        if result.get("folderName") != '':
            folderName = result["folderName"]
            refreshResult = send_refresh_to_autoscan(folderName)
            embed.add_field(
                name=f'{result["title"]} ({result["year"]})',
                value=f'\n`{folderName}`\nResult: {str(refreshResult)}',
                inline=False
            )
    # await interaction.response.send_message(embed=embed)
    await asyncio.sleep(2)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="refreshtvshow")
@app_commands.describe(tv_show_name="Enter the tv show name.")
async def refreshtvshow(interaction: discord.Interaction, tv_show_name: str):
    await interaction.response.defer()
    lookupResults = search_tv_show_by_name(tv_show_name)
    embed = discord.Embed(title=f"**Refreshed Show(s)**", color=discord.Color.blurple())
    if lookupResults:
        first_result = lookupResults[0]
    else:
        first_result = []
    if first_result:
        if first_result.get("path") is not None:
            path = first_result["path"]
            refreshResult = send_refresh_to_autoscan(path)
            embed.add_field(
                name=f'{first_result["title"]}',
                value=f'\n`{path}`\nResult: {str(refreshResult)}',
                inline=False
            )
    else:
        embed.add_field(
            name=f'No Show Found',
            value=f'Make sure spelling is correct.',
            inline=False
        )
    await asyncio.sleep(2)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="passwordreset")
@app_commands.describe(username_to_reset="Enter the jellyfin username.")
async def passwordreset(interaction: discord.Interaction, username_to_reset: str):
    await interaction.response.defer()
    # findUsername (returns server name or false)
    # if findUsername Then do stuff
        # reset
    embed = discord.Embed(title=f'Password reset!', color=discord.Color.blurple())
    await asyncio.sleep(2)
    await interaction.followup.send(embed=embed)


bot.run(config.TOKEN)
